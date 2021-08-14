import socket
from select import select
import logging
from collections import deque
import time

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

generators_queue = deque()
list_connections_to_read = []
list_connections_to_write = []


class CoroSleep:
    def __init__(self, time_to_sleep=0.0):
        self.time_to_execute = time.time() + time_to_sleep

    def __await__(self):
        while time.time() < self.time_to_execute:
            yield "not call"
        else:
            yield "done"


def server_init():
    """Иницилизация сервера сокетов"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    server_socket.bind(('localhost', 5000))
    server_socket.listen()
    logger.info("server start on localhost 5000")
    
    generators_queue.append(accept_connection(server_socket))
    generators_queue.append(handle_connection())





async def accept_connection(server_socket):
    """Вечный генератор для соеденений"""
    while True:
        await CoroSleep()
        try:
            client_socket, address = server_socket.accept()
            logger.info(f"Accept connected form \t{address}")
            list_connections_to_read.append(client_socket)
        except:
            continue


async def handle_connection():
    """Ловим сокеты которые готовы выдать к нам данные"""
    while True:
        # активируем 0 timeout что бы не было блокировки процессов
        await CoroSleep()
        ready_to_read, *_ = select(list_connections_to_read, [], [], 0)
        for sock_ready in ready_to_read:
            address = sock_ready.__repr__().replace('<', '').split('=')[-1][:-1]
            logger.info(f"Ready to read from \t{address}")
            generators_queue.append(receive_message(sock_ready))
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
    await CoroSleep()
    address = client_socket.__repr__().replace('<', '').split('=')[-1][:-1]
    logger.info(f"Send reply to client\t{address}")
    client_socket.send(message)
    # сокет в очередь
    list_connections_to_read.append(client_socket)
    return


async def close_client(client_socket):
    """Закрываем сокет"""
    await CoroSleep()
    logger.info("Client exit")
    client_socket.close()
    return


def generator_handler():
    """Главный обработчик"""
    while True:
        task = generators_queue.popleft()

        try:
            task.send(None)
            generators_queue.append(task)
        except StopIteration:
            continue
        except Exception as e:
            logging.error(f"e {e}")


if __name__ == '__main__':
    server_init()
    generator_handler()
