import asyncio
import re
import logging

import webob
FORMAT = 'LOGGING %(asctime)-15s | %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
VIEWS_MAPPING = {}


# запросы тут идут от main до миддлвари, которая потом
# распределяет запросы по вьюшкам. А чтобы можно было
# понять куда какой запрос должен идти есть VIEWS_MAPPING,
# в котором прописаны пары {путь: вьюшка}


def add_route(route):
    def decorator(func):
        VIEWS_MAPPING.update({route: func})

        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def middleware(reader, writer):
    # очень важно, чтобы было конечное число в read,
    # иначе функция застрянет в бесконечном цикле
    # TODO вроде есть метод через while, но at_eof и просто
    # проверка на конец буфера не помогли
    request_data = await reader.readuntil(separator=b"\r\n\r\n")
    logging.info(request_data)

    path, _ = request_data.split(b'\r\n', 1)
    method = re.search(br'^(.*?)\s', path).group(1).decode()
    path = re.search(br'(/.*)\sHTTP/', path).group(1)
    try:
        body = request_data.split(b'\n\n')[1]
    except IndexError:
        body = None
    logging.info(f'Request to: {path}')

    # тут происходит распределение по вьюшкам и передача запроса
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
