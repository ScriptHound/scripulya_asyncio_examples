import asyncio
import logging
import secrets
import struct
import sys
from io import BytesIO
from itertools import cycle

import webob

from constants import (
    OPCODE_CLOSE_CONN, OPCODE_TEXT, PAYLOAD_LEN)

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.INFO)


def make_closing_frame():
    """Closing frame can have no body or instead, have
    the reason why the closed frame is formed"""
    result = BytesIO()
    header_one = 0b11110000 | OPCODE_CLOSE_CONN
    header_two = 0b10000000
    result.write(struct.pack("!BB", header_one, header_two))
    result = result.getvalue()
    return result


def make_opening_handshake(host, port):
    environ = {
        "HTTP_HOST": f"{host}:{port}",
        "PATH_INFO": "/",
        "REQUEST_METHOD": "GET",
        "SERVER_NAME": host,
        "SERVER_PORT": port,
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.url_scheme": "http",
        "wsgi.version": (1, 0),
    }
    message = webob.Request(environ=environ)
    message.headers["Upgrade"] = "websocket"
    message.headers["Connection"] = "Upgrade"
    # this header is hardcoded
    message.headers["Sec-WebSocket-Key"] = "AQIDBAUGBwgJCgsMDQ4PEC=="
    message.headers["Sec-WebSocket-Version"] = 13
    message = str(message) + "\r\n\r\n"
    return message


def mask(mask, data):
    """Mask should be 4 bytes length"""
    return bytes(a ^ b for a, b in zip(cycle(mask), data))


def unpack_massage(message):
    header_two = message[1]
    payload_length = header_two & PAYLOAD_LEN
    
    payload_starting_byte = 4
    if payload_length == 126:
        payload_length = struct.unpack(">H", message[2:4])[0]
    elif payload_length == 127:
        payload_length = struct.unpack(">Q", message[2:11])[0]
        payload_starting_byte = 11
    
    logger.info(f"Payload length is: {payload_length}")
    payload = message[payload_starting_byte:]
    return payload


def wrap_message(message, opcode=OPCODE_TEXT):
    """Form a frame for the message and mask it"""
    result = BytesIO()
    header_one = 0b10000000 | opcode
    header_two = 0b10000000

    message = bytes(message, encoding="utf-8")

    length = len(message)
    if length < 126:
        result.write(struct.pack("!BB", header_one, header_two | length))
    elif length < 65536:
        result.write(struct.pack("!BBH", header_one, header_two | 126, length))
    else:
        result.write(struct.pack("!BBQ", header_one, header_two | 127, length))

    mask_bytes = secrets.token_bytes(4)
    log_info = bin(int.from_bytes(mask_bytes, byteorder=sys.byteorder))
    logger.info(
        f"MASK BYTES ARE {log_info}"
    )
    result.write(mask_bytes)

    masked_data = mask(mask_bytes, message)
    result.write(masked_data)
    return result.getvalue()


async def tcp_echo_client(host="127.0.0.1", port=9001):
    reader, writer = await asyncio.open_connection(host, port)

    handshake = make_opening_handshake(host, port)
    logger.info(f"Send: {handshake!r}")
    writer.write(handshake.encode())
    await writer.drain()
    logger.info("Sent a handshake")

    logger.info("Waiting for an upgrade response")
    data = await reader.read(1024)
    logger.info(f"Received: {data}")

    resp = wrap_message("HELLO WEBSOCKETS")
    resp = bytes(resp)
    logger.info(resp)
    writer.write(resp)
    await writer.drain()

    resp = await reader.read(1024)
    resp = unpack_massage(resp)
    logger.info(f"Response from server is: {resp}")
    logger.info("Close the connection")
    closing_frame = make_closing_frame()
    writer.write(closing_frame)
    await writer.drain()

    writer.close()
    await writer.wait_closed()


# attention, default port and host are 127.0.0.1:9001
asyncio.run(tcp_echo_client(host='localhost', port=9001))
