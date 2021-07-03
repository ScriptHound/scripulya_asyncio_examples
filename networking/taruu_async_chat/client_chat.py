from tkinter import *
import tkinter as tk
import asyncio
import time
import json
import base64


def decode_dict(bytes_in: bytes):
    """Расшифруем словарь"""
    json_data = base64.b64decode(bytes_in)
    data_dict = json.loads(json_data)
    return data_dict


def encode_dict(data: dict):
    """Зашифруем словарь"""
    json_data = json.dumps(data).encode()
    return base64.b64encode(json_data) + b"\r\n"


class Application(tk.Frame):
    """Класс приложения"""

    def __init__(self, root=None, send_data=None):
        super().__init__(root)
        self.send_data = send_data
        self.root = root
        self.now_username = None
        self.root.title("Chat demo")

        # Ставим элементы
        self.chat_text_box = Text(width=50, height=30)
        self.chat_text_box.config(state=DISABLED)
        # self.chat_text_box.place(w=0, x=0)
        self.chat_text_box.grid(row=0, column=0, padx=5, pady=5, ipady=5,
                                columnspan=4, rowspan=6)
        self.chat_text_box.config(state=NORMAL)
        # Костыль по заполнению тектса
        for _ in range(30):
            self.chat_text_box.insert(END, "\n")
        self.chat_text_box.config(state=DISABLED)
        self.username_entry = Entry()
        self.username_entry.grid(row=6, column=5, padx=5, pady=5, ipady=5,
                                 ipadx=5, sticky=N + S + W + E)
        self.users_list_box = Listbox(width=20, height=15)
        self.users_list_box.grid(row=0, column=5, rowspan=6, padx=5, pady=5,
                                 ipady=5, ipadx=5,
                                 sticky=N + S + W + E)
        self.username_save = Button(text="Save username",
                                    command=self.save_username)
        self.username_save.grid(row=7, column=5, padx=5, pady=5, ipady=5,
                                ipadx=5, sticky=N + S + W + E)
        self.message_send = Button(text="Send Message",
                                   command=self.send_message)
        self.message_send.grid(row=7, column=3, padx=5, pady=5, ipady=5,
                               ipadx=5, sticky=W + E)

        self.message = ""
        self.message_entry = Entry()
        self.message_entry.grid(row=6, column=0, padx=5, pady=5, columnspan=4,
                                sticky=N + S + W + E)
        self.message_entry.bind("<Return>", self.send_message_enter)

    def _insert_message(self, message):
        """Вставить новое сообщение в окно"""
        self.chat_text_box.config(state=NORMAL)
        self.chat_text_box.delete("1.0", "2.0")
        self.chat_text_box.insert(END, f"{message}\n")
        self.chat_text_box.see(END)
        self.chat_text_box.config(state=DISABLED)

    def _set_username(self, username):
        """Устоновить ник для юзера """
        self.now_username = username
        self.username_entry.delete(0, END)
        self.username_entry.insert(END, username)
        self.users_list_box.delete(0)
        self.users_list_box.insert(0, f"{username} (You)")

    def _add_user(self, username):
        """Добавить пользователя"""
        if username == self.now_username:
            username = f"{username} (You)"
        self.users_list_box.insert(END, f"{username}")

    def _remove_user(self, username):
        list_users = {}
        [list_users.update(
            {user: i}) for i, user in list(self.users_list_box.get(1, END))]
        id_user_to_remove = list_users.get(username)
        self.users_list_box.delete(id_user_to_remove)

    def send_message_enter(self, event):
        """Нажатие на Enter"""
        self.send_message()

    def send_message(self):
        """Отправить сообщение"""
        message = self.message_entry.get()
        if message:
            asyncio.create_task(
                self.send_data(
                    {"command": "message",
                     "data": {"content": message}}
                ))
        self.message_entry.delete(0, len(message))

    def save_username(self):
        """Изменить ник"""
        username = self.username_entry.get()
        if username:
            self.now_username = username
            self._set_username(username)
            asyncio.create_task(
                self.send_data(
                    {"command": "set_username",
                     "data": username}
                ))

    def list_users(self, list_users):
        """Обновления списка пользователей"""
        old_list_users = list(self.users_list_box.get(0, END))
        print(old_list_users)
        [self.users_list_box.delete(0) for _ in old_list_users]
        [self._add_user(user) for user in list_users]

    def write_message(self, data_obj):
        """Записываем полученные сообщения"""
        message = f"{data_obj['username']} :{data_obj['content']}"
        self._insert_message(message)


class AsyncClient:
    """Основной класс для обработки сообщений"""

    def __init__(self, app):
        """Иницилизация приложения"""
        self.app = app
        self.app.send_data = self.send_data
        self.work_client = True
        self.reader = None
        self.writer = None
        # self.commands = {
        #     "message": self.app.write_message,
        #     "get_username": self.app.set_username,
        #     "list_users": self.app.list_users
        # }

    async def _tk_application_loop(self):
        """Финт ушами который позволяет нам запускать прогу в асинхроне"""
        while self.work_client:
            try:
                self.app.update()
                await asyncio.sleep(0)
            except:
                self.work_client = False

    async def command_reader(self, data_obj):
        """Читаем и выполняем команду"""
        command = data_obj["command"]
        data = data_obj["result"]
        if command == "message":
            self.app.write_message(data)
        elif command == "get_username":
            self.app._set_username(data)
        elif command == "list_users":
            self.app.list_users(data)
        return True

    async def send_data(self, data: dict):
        """Шлем сообщения"""
        self.writer.write(encode_dict(data))

    async def receive_data(self):
        """Ждем сообщения"""
        while self.work_client:
            data_obj = decode_dict(await self.reader.readline())
            await self.command_reader(data_obj)

    async def connect_to_server(self, address, port):
        """Подключаемся к серверу"""
        asyncio.create_task(self._tk_application_loop())
        self.reader, self.writer = await asyncio.open_connection(address, port)
        asyncio.create_task(self.receive_data())
        while self.work_client:
            await asyncio.sleep(1)


# Делаем класс
root = tk.Tk()
app_tk = Application(root=root)

async_client = AsyncClient(app_tk)
#Подключаемся к серверу
asyncio.run(async_client.connect_to_server("127.0.0.1", 8888))
