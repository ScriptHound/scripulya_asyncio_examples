import asyncio
import logging
import logging.handlers
import sys

logging.basicConfig(format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ServerChat:
    def __init__(self):
        self.list_user = {}

    async def send_all_exclude_user(self, message, username_not_send):
        logger.info(f'Message: {message}'.replace("\r", "").replace("\n", ""))
        for username, writer in self.list_user.items():
            if username != username_not_send:
                writer.write(message.encode())
                await writer.drain()

    async def user_exit(self, username, message):
        if message.replace("\r\n", "") == "^]":
            user_write = self.list_user.pop(username)
            user_write.write(f"Bye Bye {username}\r\n".encode())
            user_write.close()
            await self.send_all_exclude_user(f"User {username} left chat\r\n", None)
            return True
        else:
            return False

    async def user_disconnected(self, username, reader):
        if reader.at_eof():
            logger.info(f'{username} disconnected.')
            user_write = self.list_user.pop(username)
            user_write.close()
            await self.send_all_exclude_user(f"{username} left chat\r\n", None)
            return True
        else:
            return False

    async def wait_message(self, writer, reader, username):
        data_bytes = await reader.readline()
        message = data_bytes.decode()
        if not await self.user_exit(username, message) and not await self.user_disconnected(username, reader):
            await self.send_all_exclude_user(f"{username}: {message}", username)
            asyncio.create_task(self.wait_message(writer, reader, username))

    async def get_username(self, reader, writer):
        logger.info(f'Wait enter username')
        writer.write(b"Enter you username:")
        await writer.drain()
        data_bytes = await reader.readline()
        username = data_bytes.decode().replace("\r\n", "")
        if username in self.list_user:
            writer.write(b"Sorry this username is busy!\r\n")
            await writer.drain()
            writer.close()
            return

        writer.write(b"To exit type '^]' \r\n")
        await writer.drain()
        self.list_user.update({username: writer})
        await self.send_all_exclude_user(f"User {username} connected to chat\n", username)
        asyncio.create_task(self.wait_message(writer, reader, username))

    async def handle_connection(self, reader, writer):
        logger.info(f'Handle incoming connection')
        await self.get_username(reader, writer)


async def main():
    chat_server = ServerChat()
    server = await asyncio.start_server(
        chat_server.handle_connection, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
