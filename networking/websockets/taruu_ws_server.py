import asyncio
import struct
from base64 import b64encode
from hashlib import sha1

import logging
import logging.handlers
from networking.websockets.constants import *

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def encode_to_UTF8(data):
    """Кодируем сообщение"""
    try:
        return data.encode('UTF-8')
    except UnicodeEncodeError as e:
        logger.error("Could not encode data to UTF-8 -- %s" % e)
        return False
    except Exception as e:
        raise (e)


def try_decode_UTF8(data):
    """Декодирование сообщения"""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    except Exception as e:
        raise (e)


class WebSocketServer:
    """Не Клиент а Сервер вебсокета"""

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.keep_alive = True
        self.handshake_done = False
        self.valid_client = False
        self.message_cache = b""

    async def client_watcher(self):
        """Смотрим за вебсокетом"""
        while self.keep_alive:
            logger.debug(self.handshake_done)
            if not self.handshake_done:
                await self.handshake()
            else:
                await self.read_next_message()

    async def relpy_client(self, message):
        """Ответ клиенту"""
        message = b"You foxgirl? Okey here you message: " + message.encode()
        await self.send_text(message)

    async def send_pong(self, message):
        """Ответа на пинг"""
        await self.send_text(message, OPCODE_PONG)

    async def read_bytes(self, num):
        """Читаем байты"""
        bytes = await self.reader.read(num)
        logger.debug(f"Read len byes {num}")
        return bytes

    async def read_http_headers(self):
        """Чтения твоей головы бро"""
        headers = {}
        http_get = await self.reader.readline()
        http_get = http_get.decode().strip()
        assert http_get.upper().startswith('GET')
        # remaining should be headers
        while True:
            header = await self.reader.readline()
            header = header.decode().strip()
            if not header:
                break
            head, value = header.split(':', 1)
            headers[head.lower().strip()] = value.strip()
        return headers

    async def handshake(self):
        """Обмен рукопожатиями"""
        headers = await self.read_http_headers()
        try:
            assert headers['upgrade'].lower() == 'websocket'
        except AssertionError:
            self.keep_alive = False
            return
        try:
            key = headers['sec-websocket-key']
        except KeyError:
            logger.warning("Client tried to connect but was missing a key")
            self.keep_alive = False
            return

        logger.debug(f"Client client: {key}")
        logging.info(f"Client {hash(self.reader)} handshake")
        # Варим ответ для клиента
        response = self.make_handshake_response(key)
        self.writer.write(response.encode())
        await self.writer.drain()
        self.handshake_done = True

    async def send_text(self, message, opcode=OPCODE_TEXT):
        """Шлем текст клиенту"""

        # Validate message
        if isinstance(message, bytes):
            message = try_decode_UTF8(
                message)  # this is slower but ensures we have UTF-8
            if not message:
                logger.warning(
                    "Can\'t send message, message is not valid UTF-8")
                return False
        else:
            logger.warning(
                f'Can\'t send message, message has to be a string or bytes. \
            Given type is {type(message)}')
            return False

        header = bytearray()
        payload = encode_to_UTF8(message)
        payload_length = len(payload)

        # Выбор длинны
        if payload_length <= 125:
            header.append(FIN | opcode)
            header.append(payload_length)

        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))

        elif payload_length < 18446744073709551616:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))
        else:
            raise Exception(
                "Message is too big. Consider breaking it into chunks.")

        logging.info(f"Client {hash(self.reader)} send echo")
        self.writer.write(header + payload)
        await self.writer.drain()

    async def read_next_message(self):
        """Чтение следущего фрейма"""
        try:
            b1, b2 = await self.read_bytes(2)
        except asyncio.IncompleteReadError as e:
            if e.partial == 0:
                logger.info("Client closed connection.")
                self.keep_alive = False
                return
            b1, b2 = 0, 0
        except ValueError as e:
            b1, b2 = 0, 0

        fin = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN
        logging.info(f"Client {hash(self.reader)} get message")
        logging.debug(
            f"""f:{fin} op:{opcode} ma:{masked} pay:{payload_length}""")

        # Читаем опткоды
        if opcode == OPCODE_CLOSE_CONN:
            logger.info(
                f"Client {hash(self.reader)} asked to close connection.")
            self.keep_alive = False
            return
        if not masked:
            logger.warning("Client must always be masked.")
            self.keep_alive = False
            return
        if opcode == OPCODE_CONTINUATION:
            logger.warning("Continuation frames are not supported.")
            return
        elif opcode == OPCODE_BINARY:
            logger.warning("Binary frames are not supported.")
            return
        elif opcode == OPCODE_TEXT:
            opcode_handler = self.relpy_client
        elif opcode == OPCODE_PING:
            opcode_handler = self.send_pong
        elif opcode == OPCODE_PONG:
            opcode_handler = self.send_pong
        else:
            logger.warning("Unknown opcode %#x." % opcode)
            self.keep_alive = False
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", await self.reader.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", await self.reader.read(8))[0]

        # Получаем маску
        masks = await self.read_bytes(4)

        message_bytes = bytearray(
            byte ^ masks[i % 4] for i, byte in enumerate(
                await self.read_bytes(payload_length)))
        data = try_decode_UTF8(message_bytes)
        logger.debug(f"data {bool(data)}")
        if data:
            await opcode_handler(data)

    @classmethod
    def make_handshake_response(cls, key):
        """Комякает ответ"""
        return f'''HTTP/1.1 101 Switching Protocols\r
Connection: Upgrade\r
Sec-WebSocket-Accept: {cls.calculate_response_key(key)}
Upgrade: websocket\r\n\r\n'''

    @classmethod
    def calculate_response_key(cls, key):
        """Здесь происходит вычисление ключа для клинета"""
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')


async def handle_echo(reader, writer):
    """Ловим клиента и пихаем его на досмотр"""
    logging.info(f"Connected new client {hash(reader)}")
    asyncio.create_task(WebSocketServer(reader, writer).client_watcher())


async def main():
    """Работай чертила..."""
    server = await asyncio.start_server(
        handle_echo, 'localhost', 8081)

    addr = server.sockets[0].getsockname()
    logging.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
