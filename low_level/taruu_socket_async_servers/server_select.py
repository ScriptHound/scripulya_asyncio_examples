import socket
from select import select
import logging

logging.basicConfig(
    format="\033[36m %(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('localhost', 5000))
server_socket.listen()

connection_to_lookup = [server_socket]


def accept_connection(server_socket):
    logger.info("Accepting connection")
    client_socket, addr = server_socket.accept()
    logger.info(f"Connected form {addr}")
    connection_to_lookup.append(client_socket)


def send_message(client_socket):
    request = client_socket.recv(1024)
    if request:
        logger.info("Rely client message")
        response = "You data: ".encode() + request
        client_socket.send(response)
    else:
        logger.info("Client exit")
        client_socket.close()
        connection_to_lookup.remove(client_socket)


def connection_handler():
    ready_to_handle, *_ = select(connection_to_lookup, [], [])
    for sock in ready_to_handle:
        if sock is server_socket:
            accept_connection(sock)
        else:
            send_message(sock)


if __name__ == '__main__':
    while True:
        connection_handler()
