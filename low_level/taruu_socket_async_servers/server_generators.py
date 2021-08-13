import socket
from select import select
import logging
from collections import deque

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
    generators_queue.append(accept_connection(server_socket))
    generators_queue.append(handle_connection())


def accept_connection(server_socket):
    """Вечный генератор для соеденений"""
    while True:
        yield
        try:
            client_socket, address = server_socket.accept()
            logger.info(f"Accept connected form \t{address}")
            list_connections_to_read.append(client_socket)
        except:
            continue


def handle_connection():
    """Ловим сокеты которые готовы выдать к нам данные"""
    while True:
        yield
        # активируем 0 timeout что бы не было блокировки процессов
        ready_to_read, *_ = select(list_connections_to_read, [], [], 0)
        for sock_ready in ready_to_read:
            address = sock_ready.__repr__().replace('<', '').split('=')[-1][:-1]
            logger.info(f"Ready to read from \t{address}")
            generators_queue.append(receive_message(sock_ready))
            list_connections_to_read.remove(sock_ready)


def receive_message(client_socket):
    """Чтение сообщения"""
    yield
    request = client_socket.recv(1024)
    if request:
        message = "You data: ".encode() + request
        # делаем корутину на отправку сообщения
        generators_queue.append(send_message(client_socket, message))
    else:
        client_socket.close()


def send_message(client_socket, message):
    """Отправку сообщения в сокет"""
    yield
    address = client_socket.__repr__().replace('<', '').split('=')[-1][:-1]
    logger.info(f"Send reply to client\t{address}")
    client_socket.send(message)
    # сокет в очередь
    list_connections_to_read.append(client_socket)


def close_client(client_socket):
    """Закрываем сокет"""
    yield
    logger.info("Client exit")
    client_socket.close()


def generator_handler():
    """Главный обработчик"""
    while True:
        task = generators_queue.popleft()
        try:
            next(task)
            generators_queue.append(task)
        except StopIteration:
            continue
        except Exception as e:
            logging.error(f"e {e}")


if __name__ == '__main__':
    server_init()
    generator_handler()
