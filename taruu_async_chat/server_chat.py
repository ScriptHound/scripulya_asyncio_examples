import asyncio

list_user = []


class ServerChat:
    def __init__(self):
        self.list_user = {}

    async def send_all_exclude_user(self, message, username_not_send):
        for username, writer in self.list_user.items():
            if username != username_not_send:
                writer.write(message.encode())
                await writer.drain()

    async def wait_message(self, writer, reader, username):
        while True:
            data_bytes = await reader.readline()
            message = data_bytes.decode()
            if message.replace("\r\n", "") == "^]":
                user_write = self.list_user.pop(username)
                user_write.write("Bye Bye {username}\r\n".encode())
                user_write.close()
                await self.send_all_exclude_user(f"User {username} left chat\r\n", None)
                break
            else:
                await self.send_all_exclude_user(username + ": " + message, username)

    async def get_username(self, reader, writer):
        writer.write(b"Enter you username:")
        await writer.drain()
        data_bytes = await reader.readline()
        username = data_bytes.decode().replace("\r\n", "")
        if username in self.list_user:
            writer.write(b"Sorry this username is busy!\r\n")
            await writer.drain()
            writer.close()
            return

        print(f"{username} connection to chat")
        writer.write(b"To exit type '^]' \r\n")
        await writer.drain()
        self.list_user.update({username: writer})
        await self.send_all_exclude_user(f"User {username} connected to chat\n", username)
        asyncio.create_task(self.wait_message(writer, reader, username))

    async def handle_connection(self, reader, writer):
        await self.get_username(reader, writer)


async def main():
    chat_server = ServerChat()
    server = await asyncio.start_server(
        chat_server.handle_connection, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
