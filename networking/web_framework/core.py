import asyncio
import re
import logging

import webob
from http_parser.pyparser import HttpParser
FORMAT = 'LOGGING %(asctime)-15s | %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
VIEWS_MAPPING = {}


def add_route(route):
    def decorator(func):
        VIEWS_MAPPING.update({route: func})

        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def middleware(reader, writer):
    request_data = await reader.read(1024)

    path, _ = request_data.split(b'\r\n', 1)
    method = re.search(br'^(.*?)\s', path).group(1).decode()
    path = re.search(br'(/.*)\sHTTP/', path).group(1)
    try:
        body = request_data.split(b'\n\n')[1]
    except IndexError:
        body = None
    logging.info(f'Request to: {path}')

    callback = VIEWS_MAPPING[path.decode()]
    body = await callback({'body': body, 'method': method})

    response = webob.Response(body=body.encode())
    response = 'HTTP/1.1 ' + str(response)
    response = response.encode()
    writer.write(response)
    await writer.drain()
    writer.close()


async def main(host, port):
    server = await asyncio.start_server(
        middleware, host, port
    )

    addr = server.sockets[0].getsockname()
    logging.info(f"Serving on {addr[0]}:{addr[1]}")

    async with server:
        await server.serve_forever()


def run_app(host, port):
    asyncio.run(main(host, port))
