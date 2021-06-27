import asyncio
import logging
import logging.handlers
import sys
import json
import base64

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def decode_dict(bytes_in: bytes):
    json_data = base64.b64decode(bytes_in)
    data_dict = json.loads(json_data)
    return data_dict


def encode_dict(data: dict):
    json_data = json.dumps(data).encode()
    return base64.b64encode(json_data) + b"\r\n"



class ServerChat:
    def __init__(self):
        self.commands = {}
        self.users_count = 1
        self.list_user = {}

    def add_to_commands(func, self=None):
        print(func)

    async def send_all_exclude_user(self, data_dict, username_not_send):
        logger.info(f'send data to all user: {data_dict}')
        for username, writer in self.list_user.items():
            if username != username_not_send:
                writer.write(encode_dict(data_dict))
                await writer.drain()

    async def user_exit(self, username):
        user_write = self.list_user.pop(username)
        user_write.write(encode_dict({"disconnect_you": True}))
        user_write.close()
        await self.send_all_exclude_user({"user_left_chat": username}, None)
        return True

    async def user_disconnected(self, username, reader):
        if reader.at_eof():
            logger.info(f'{username} disconnected.')
            user_write = self.list_user.pop(username)
            user_write.close()
            await self.send_all_exclude_user({"user_left_chat": username}, None)
            return True
        else:
            return False

    async def wait_message(self, writer, reader, username):
        data_obj = decode_dict(await reader.readline())
        if await self.command_reader(data_obj, username, writer, reader):
            asyncio.create_task(self.wait_message(writer, reader, username))

    async def command_reader(self, data_obj, username, writer, reader):
        commands = {
            "send_message": self.send_message
        }
        if await self.user_disconnected(username, reader):
            return False
        if "disconnect_me" in data_obj:
            await self.user_exit(username)
            return False

        pass

    async def send_message(self, data_obj):
        print(data_obj)

    async def first_connection(self, reader, writer):
        username = f"User {self.users_count}"
        self.users_count += 1
        logger.info(f'Send username')
        writer.write(encode_dict({"set_username": username}))

        self.list_user.update({username: writer})
        await self.send_all_exclude_user({"user_connect_to_chat": username},
                                         None)
        asyncio.create_task(self.wait_message(writer, reader, username))

    async def handle_connection(self, reader, writer):
        logger.info(f'Handle incoming connection')
        await self.first_connection(reader, writer)


async def main():
    chat_server = ServerChat()
    server = await asyncio.start_server(
        chat_server.handle_connection, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
