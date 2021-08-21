import socket
import time
import logging
from select import select
from collections import deque
import asyncio

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

generators_queue = deque()
list_connections_to_read = []
list_connections_to_write = []


def server_init():
    """Иницилизация сервера сокетов"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    server_socket.bind(('localhost', 5000))
    server_socket.listen()
    logger.info("server start on localhost 5000")

    asyncio.create_task(accept_connection(server_socket))
    asyncio.create_task(handle_connection())


async def accept_connection(server_socket):
    """Вечный генератор для соеденений"""
    while True:
        await asyncio.sleep(0)
        try:
            client_socket, address = server_socket.accept()
            logger.info(f"Accept connected form \t{address}")
            list_connections_to_read.append(client_socket)
        except:
            continue


async def handle_connection():
    """Ловим сокеты которые готовы выдать к нам данные"""
    while True:
        await asyncio.sleep(0)
        # активируем 0 timeout что бы не было блокировки процессов
        ready_to_read, *_ = select(list_connections_to_read, [], [], 0)
        for sock_ready in ready_to_read:
            address = sock_ready.__repr__().replace('<', '').split('=')[-1][:-1]
            logger.info(f"Ready to read from \t{address}")

            asyncio.create_task(receive_message(sock_ready))
            list_connections_to_read.remove(sock_ready)


async def receive_message(client_socket):
    """Чтение сообщения"""
    request = client_socket.recv(1024)
    if request:
        message = "You data: ".encode() + request
        # делаем корутину на отправку сообщения
        await send_message(client_socket, message)
    else:
        await close_client(client_socket)
    return


async def send_message(client_socket, message):
    """Отправку сообщения в сокет"""
    address = client_socket.__repr__().replace('<', '').split('=')[-1][:-1]
    logger.info(f"Send reply to client\t{address}")
    client_socket.send(message)
    # сокет в очередь
    list_connections_to_read.append(client_socket)
    return


async def close_client(client_socket):
    """Закрываем сокет"""
    logger.info("Client exit")
    client_socket.close()
    return


async def main():
    server_init()
    while True:
        await asyncio.sleep(0)


if __name__ == '__main__':
    asyncio.run(main())
