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


class HandlerData:
    def __iter__(self):
        pass


class WebSocketClient:
    """Клиент вебсокета"""

    def __init__(self, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

        pass

    async def client_watcher(self):
        pass

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
        logger.debug(pprint.pformat(headers))
        logger.debug(headers['upgrade'].lower())

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
        self.writer.writelines(response)
        await self.writer.drain()
        logger.debug(await self.reader.readline())

    def read_next_message(self):
        try:
            b1, b2 = await self.read_bytes(2)
        # except SocketError as e:  # to be replaced with ConnectionResetError for py3
        #     if e.errno == errno.ECONNRESET:
        #         logger.info("Client closed connection.")
        #         self.keep_alive = 0
        #         return
        #     b1, b2 = 0, 0
        except ValueError as e:
            b1, b2 = 0, 0

        fin = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if opcode == OPCODE_CLOSE_CONN:
            logger.info("Client asked to close connection.")
            self.keep_alive = 0
            return
        if not masked:
            logger.warn("Client must always be masked.")
            self.keep_alive = 0
            return
        if opcode == OPCODE_CONTINUATION:
            logger.warn("Continuation frames are not supported.")
            return
        elif opcode == OPCODE_BINARY:
            logger.warn("Binary frames are not supported.")
            return
        elif opcode == OPCODE_TEXT:
            opcode_handler = lambda data: logger.info(
                "get text from client {data}")
        elif opcode == OPCODE_PING:
            opcode_handler = self.server._ping_received_
        elif opcode == OPCODE_PONG:
            opcode_handler = self.server._pong_received_
        else:
            logger.warn("Unknown opcode %#x." % opcode)
            self.keep_alive = 0
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", self.rfile.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", self.rfile.read(8))[0]

        masks = self.read_bytes(4)
        message_bytes = bytearray()
        for message_byte in await self.read_bytes(payload_length):
            message_byte ^= masks[len(message_bytes) % 4]
            message_bytes.append(message_byte)
        opcode_handler(self, message_bytes.decode('utf8'))

    async def read_bytes(self, num):
        return await self.reader.read(num)

    @classmethod
    def make_handshake_response(cls, key):
        return list(map(lambda line: line.encode(), [
            'HTTP/1.1 101 Switching Protocols',
            'Upgrade: websocket',
            'Connection: Upgrade',
            'Sec-WebSocket-Accept: {}'.format(
                cls.calculate_response_key(key))
        ]))

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
    await WebSocketClient(reader, writer).handshake()

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
    writer.close()


async def main():
    server = await asyncio.start_server(
        handle_echo, 'localhost', 8081)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
