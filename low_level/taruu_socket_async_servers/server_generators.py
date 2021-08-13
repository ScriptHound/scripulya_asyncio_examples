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
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(False)
    server_socket.bind(('localhost', 5000))
    server_socket.listen()
    generators_queue.append(accept_connection(server_socket))
    generators_queue.append(check_ready())


def accept_connection(server_socket):
    while True:
        yield
        try:
            client_socket, addr = server_socket.accept()
            logger.info(f"Connected form {addr}")
            list_connections_to_read.append(client_socket)
            # generators_queue.append(receive_message(client_socket))
        except:
            continue


def check_ready():
    logging.info("test")
    while True:
        yield
        # активируем 0 timeout что бы не было блокировки процессов
        ready_to_read, ready_to_write, [] = select(list_connections_to_read,
                                                   list_connections_to_write,
                                                   [], 0.0001)
        for sock_ready in ready_to_read:
            generators_queue.append(
                receive_message(sock_ready))
            list_connections_to_read.remove(sock_ready)

        # for sock_ready in ready_to_write:
        #     generators_queue.append(
        #         send_message(list_connections_to_write.pop(sock_ready),
        #                      b"test"))


def receive_message(client_socket):
    yield
    request = client_socket.recv(1024)
    if request:
        message = "You data: ".encode() + request
        logger.info(f"get message {message}")
        generators_queue.append(send_message(client_socket, message))
        list_connections_to_read.append(client_socket)
    else:
        client_socket.close()


def send_message(client_socket, message):
    yield
    logger.info("Send message to client")
    client_socket.send(message)


def close_client(client_socket):
    yield
    logger.info("Client exit")
    client_socket.close()


def generator_handler():
    old_task = generators_queue.copy()
    while True:
        if old_task != generators_queue:
            logger.info(f"{generators_queue}")
            old_task = generators_queue

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
