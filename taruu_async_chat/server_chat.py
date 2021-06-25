import asyncio

list_user = []


class ServerChat:
    def __init__(self):
        self.list_user = []

    async def handle_connection(self, reader, writer):
        if not (reader, writer) in self.list_user:
            self.list_user.append((reader, writer))
            print(self.list_user)
        while True:
            data = await reader.read(100)
            message = data.decode()
            addr = writer.get_extra_info('peername')

            print(f"Received {message!r} from {addr!r}")

            print(f"Send: {message!r}")
            for reader_l, writer_l in self.list_user:
                writer_l.write(b"relp:" + data)
                await writer_l.drain()

            print("unlock the connection")

        # writer.close()


async def main():
    chat_server = ServerChat()
    server = await asyncio.start_server(
        chat_server.handle_connection, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
