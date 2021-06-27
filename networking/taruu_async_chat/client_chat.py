from tkinter import *
import tkinter as tk
import asyncio
import time
import json
import base64


def decode_dict(bytes_in: bytes):
    json_data = base64.b64decode(bytes_in)
    data_dict = json.loads(json_data)
    return data_dict


def encode_dict(data: dict):
    json_data = json.dumps(data).encode()
    return base64.b64encode(json_data) + b"\r\n"


class Application(tk.Frame):
    def __init__(self, root=None, callback=None):
        super().__init__(root)
        self.callback = callback
        self.root = root
        # self.root.geometry('500x500')
        self.root.title("Chat demo")

        self.chat_text_box = Text(width=50, height=30)
        self.chat_text_box.config(state=DISABLED)
        # self.chat_text_box.place(w=0, x=0)
        self.chat_text_box.grid(row=0, column=0, padx=5, pady=5, ipady=5,
                                columnspan=4, rowspan=6)
        self.chat_text_box.config(state=NORMAL)
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

    def set_username(self, username):
        self.users_list_box.insert(0, f"{username} (You)")
        if self.username_entry.get() != username:
            self.username_entry.insert(0, username)



    def save_username(self):
        print("save username")

    def send_message(self):
        print("send message")

    def insert_message(self, message):
        self.chat_text_box.config(state=NORMAL)
        self.chat_text_box.delete("1.0", "2.0")
        self.chat_text_box.insert(END, f"{message}\n")
        self.chat_text_box.see(END)
        self.chat_text_box.config(state=DISABLED)


class asyncClient:
    def __init__(self, app):
        self.app = app
        self.work_client = True
        self.reader = None
        self.writer = None

    async def _tk_application_loop(self):
        while self.work_client:
            try:
                self.app.update()
                await asyncio.sleep(0)
            except:
                self.work_client = False

    async def test_insert_text(self):
        while self.work_client:
            self.app.insert_message(f"{time.time()}")
            await asyncio.sleep(1)


    async def command_reader(self, data_command):
        if "set_username" in data_command:
            self.app.set_username(data_command["set_username"])
        pass
        #commands = {"set_username" : }

    async def send_data(self, data: dict):
        self.writer.write()

    async def receive_data(self):
        while self.work_client:
            data_obj = decode_dict(await self.reader.readline())
            await self.command_reader(data_obj)
            print(data_obj)

    async def connect_to_server(self, address, port):
        asyncio.create_task(self._tk_application_loop())
        asyncio.create_task(self.test_insert_text())
        self.reader, self.writer = await asyncio.open_connection(address, port)
        asyncio.create_task(self.receive_data())
        while self.work_client:
            await asyncio.sleep(1)


root = tk.Tk()
app_tk = Application(root=root)

async_client = asyncClient(app_tk)
asyncio.run(async_client.connect_to_server("127.0.0.1", 8888))
