import asyncio


async def handle_start(reader, writer):
    data = await reader.read()
    message = data.decode()

    print(f'Received message\n{message}')
    writer.close()


async def main():
    server = await asyncio.start_server(
        handle_start, '127.0.0.1', 8000
    )

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
