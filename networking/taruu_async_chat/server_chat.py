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
    """Расшифруем словарь"""
    json_data = base64.b64decode(bytes_in)
    data_dict = json.loads(json_data)
    return data_dict


def encode_dict(data: dict):
    """Зашифруем словарь"""
    json_data = json.dumps(data).encode()
    return base64.b64encode(json_data) + b"\r\n"


class ServerChat:
    def __init__(self):
        self.users_count = 1
        self.list_user = {}

    async def _send_data_to_user(self, username, data_dict):
        logger.info(f"Send data to user {username}: {data_dict}")
        writer = self.list_user.get(username)
        writer.write(encode_dict(data_dict))
        await writer.drain()

    async def _send_data_users(self, data_dict):
        """Отправить данные всем пользователям"""
        logger.info(f'send data to all user: {data_dict}')
        ready_data = encode_dict(data_dict)
        for writer in self.list_user.values():
            writer.write(ready_data)
            await writer.drain()

    async def user_exit(self, username):
        """Если пользовател вышел из чата"""
        user_write = self.list_user.pop(username)
        user_write.close()
        data_obj = {"command": "message",
                    "result": {"username": "SERVER",
                               "content": f"User {username} left chat"}}
        asyncio.create_task(self._send_data_users(data_obj))
        asyncio.create_task(self.list_users())
        return True

    async def user_disconnected(self, username, reader):
        """Отключить пользователя экстренно"""
        if reader.at_eof():
            logger.info(f'{username} disconnected.')
            user_write = self.list_user.pop(username)
            user_write.close()

            data_obj = {"command": "message",
                        "result": {"username": "SERVER",
                                   "content": f"User {username} left chat"}}
            asyncio.create_task(self._send_data_users(data_obj))
            asyncio.create_task(self.list_users())
            return True
        else:
            return False

    async def send_message(self, data_obj, username):
        """Отправить сообщение"""
        data_obj = {
            "command": "message",
            "result": {
                "username": username,
                "content": data_obj["content"]
            }
        }
        await self._send_data_users(data_obj)

    async def set_username(self, new_username, username):
        """Пользователь поменял ник"""
        if new_username in self.list_user:
            data_obj = {
                "command": "message",
                "result": {
                    "username": "SERVER",
                    "content":
                        f"Sorry but '{new_username}' already taken"
                }
            }
            asyncio.create_task(self._send_data_to_user(username, data_obj))
            return False
        old_username = username
        writer = self.list_user.pop(username)
        self.list_user.update({new_username: writer})
        data_obj = {
            "command": "message",
            "result": {
                "username": "SERVER",
                "content":
                    f"user {old_username} change to f{new_username}"
            }
        }
        asyncio.create_task(self._send_data_users(data_obj))
        asyncio.create_task(self.list_users())
        return True

    async def list_users(self):
        """список всех пользователей"""
        data_obj = {"command": "list_users",
                    "result": list(self.list_user.keys())}
        await self._send_data_users(data_obj)

    async def _wait_message(self, writer, reader, username):
        """Ждем сообщения от юзеря"""
        in_bytes = await reader.readline()
        if await self.user_disconnected(username, reader):
            await self.list_users()
            return
        logging.info(f'Received bytes {in_bytes}')
        data_obj = decode_dict(in_bytes)
        await self._command_reader(data_obj, username, writer, reader)

    async def _command_reader(self, data_obj, username, writer, reader):
        """Выполняем команды"""
        if "disconnect" == data_obj["command"]:
            await self.user_exit(username)
            await self.list_users()
            return False
        elif "message" == data_obj["command"]:
            await self.send_message(data_obj["data"], username)
            asyncio.create_task(
                self._wait_message(writer, reader, username))
        elif "set_username" == data_obj["command"]:
            if await self.set_username(data_obj["data"], username):
                asyncio.create_task(
                    self._wait_message(writer, reader, data_obj["data"]))
        return True

    async def handle_connection(self, reader, writer):
        """Первое подключение клиенту к серверу"""
        logger.info(f'Handle incoming connection')
        username = f"User {self.users_count}"
        self.users_count += 1
        logger.info(f'Send username')
        # Даем обидное имя юзерю
        writer.write(encode_dict(
            {"command": "get_username",
             "result": username}
        ))
        await writer.drain()
        # добавяем юзеря в список
        self.list_user.update({username: writer})
        await self.send_message({"content": f"user {username} join to chat"},
                                "SERVER")
        await self.list_users()
        asyncio.create_task(self._wait_message(writer, reader, username))


async def main():
    chat_server = ServerChat()
    server = await asyncio.start_server(
        chat_server.handle_connection, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
