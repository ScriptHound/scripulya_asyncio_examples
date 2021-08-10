import socket
import selectors
import logging

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)
selector = selectors.DefaultSelector()


def server_init():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', 5000))
    server_socket.listen()
    selector.register(fileobj=server_socket, events=selectors.EVENT_READ,
                      data=accept_connection)


def accept_connection(server_socket):
    logger.info("Accepting connection")
    client_socket, addr = server_socket.accept()
    logger.info(f"Connected form {addr}")
    selector.register(fileobj=client_socket, events=selectors.EVENT_READ,
                      data=send_message)


def send_message(client_socket):
    request = client_socket.recv(1024)
    if request:
        logger.info("Rely client message")
        response = "You data: ".encode() + request
        client_socket.send(response)
    else:
        logger.info("Client exit")
        selector.unregister(client_socket)
        client_socket.close()


def connection_handler():
    events = selector.select()
    for key, _ in events:
        method = key.data
        method(key.fileobj)


if __name__ == '__main__':
    server_init()
    while True:
        connection_handler()
