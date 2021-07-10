import asyncio
import base64
import json
import logging
import struct
from base64 import b64encode
from hashlib import sha1
import pprint
import logging.handlers
import asyncio

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Я копипастер! И я этим да
FIN = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE_CONN = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


def encode_to_UTF8(data):
    try:
        return data.encode('UTF-8')
    except UnicodeEncodeError as e:
        logger.error("Could not encode data to UTF-8 -- %s" % e)
        return False
    except Exception as e:
        raise (e)


def try_decode_UTF8(data):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    except Exception as e:
        raise (e)


class HandlerData:
    def __iter__(self):
        pass


def server_get_message(self, data):
    logger.info(f"WebSocket get message: {data}")


class WebSocketClient:
    """Клиент вебсокета"""

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.keep_alive = True
        self.handshake_done = False
        self.valid_client = False
        pass

    async def client_watcher(self):
        while self.keep_alive:
            logger.debug(self.handshake_done)
            if not self.handshake_done:
                await self.handshake()
            else:
                await self.read_next_message()
        pass

    async def relpy_client(self, message):
        logger.debug(f"Send relpy {message}")
        message = b"You foxgirl? Okey here you message: " + message.encode()
        await self.send_text(message)

    async def send_pong(self, message):
        await self.send_text(message, OPCODE_PONG)

    async def read_bytes(self, num):
        bytes = await self.reader.read(num)
        logger.debug(f"bytes {num} {bytes}")
        return bytes

    async def read_http_headers(self):
        """Чтения твоей головы бро"""
        headers = {}
        # first line should be HTTP GET
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

        logger.debug(f"KEY client: {key}")
        response = self.make_handshake_response(key)
        logger.debug(response)
        self.writer.write(response.encode())
        await self.writer.drain()
        self.handshake_done = True

    async def send_text(self, message, opcode=OPCODE_TEXT):
        """
        Important: Fragmented(=continuation) messages are not supported since
        their usage cases are limited - when we don't know the payload length.
        """

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
                f'Can\'t send message, message has to be a string or bytes. Given type is {type(message)}')
            return False

        header = bytearray()
        payload = encode_to_UTF8(message)
        payload_length = len(payload)

        # Normal payload
        if payload_length <= 125:
            header.append(FIN | opcode)
            header.append(payload_length)

        # Extended payload
        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))

        # Huge extended payload
        elif payload_length < 18446744073709551616:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))

        else:
            raise Exception(
                "Message is too big. Consider breaking it into chunks.")
            return

        logger.debug(f"to send {header + payload}")
        self.writer.write(header + payload)
        await self.writer.drain()

    async def read_next_message(self):
        b1, b2 = await self.read_bytes(2)
        try:
            pass
        # except SocketError as e:  # to be replaced with ConnectionResetError for py3
        #     if e.errno == errno.ECONNRESET:
        #         logger.info("Client closed connection.")
        #         self.keep_alive = 0
        #         return
        #     b1, b2 = 0, 0
        except ValueError as e:
            b1, b2 = 0, 0

        logger.debug(f"2 first_bytes {b1, b2}")

        fin = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if opcode == OPCODE_CLOSE_CONN:
            logger.info("Client asked to close connection.")
            self.keep_alive = 0
            return
        if not masked:
            # logger.warn("Client must always be masked.")
            self.keep_alive = 0
            return
        if opcode == OPCODE_CONTINUATION:
            logger.warn("Continuation frames are not supported.")
            return
        elif opcode == OPCODE_BINARY:
            logger.warn("Binary frames are not supported.")
            return
        elif opcode == OPCODE_TEXT:
            opcode_handler = self.relpy_client
        elif opcode == OPCODE_PING:
            opcode_handler = self.send_pong
        elif opcode == OPCODE_PONG:
            opcode_handler = self.send_pong
        else:
            logger.warn("Unknown opcode %#x." % opcode)
            self.keep_alive = 0
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", await self.reader.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", self.reader.read(8))[0]

        masks = await self.read_bytes(4)
        message_bytes = bytearray()
        for message_byte in await self.read_bytes(payload_length):
            message_byte ^= masks[len(message_bytes) % 4]
            message_bytes.append(message_byte)

        logger.debug(message_bytes)
        await opcode_handler(message_bytes.decode('utf8'))

    @classmethod
    def make_handshake_response(cls, key):
        return f'''HTTP/1.1 101 Switching Protocols\r
Connection: Upgrade\r
Sec-WebSocket-Accept: {cls.calculate_response_key(key)}
Upgrade: websocket\r\n\r\n'''

    @classmethod
    def calculate_response_key(cls, key):
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')


class SimpleWebSocketServer:
    def __init__(self):
        self.list_client = []


async def handle_echo(reader, writer):
    asyncio.create_task(WebSocketClient(reader, writer).client_watcher())

    # data = await reader.read(100)
    # message = data.decode()
    # addr = writer.get_extra_info('peername')
    #
    # print(f"Received {message!r} from {addr!r}")
    #
    # print(f"Send: {message!r}")
    # writer.write(data)
    # await writer.drain()
    #
    # print("Close the connection")


async def main():
    server = await asyncio.start_server(
        handle_echo, 'localhost', 8081)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
