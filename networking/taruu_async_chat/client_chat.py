from tkinter import *
import tkinter as tk
import asyncio
import time

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
        self.chat_text_box.grid(row=0, column=0, padx=5, pady=5, ipady=5, columnspan=4, rowspan=6)
        self.chat_text_box.config(state=NORMAL)
        for _ in range(30):
            self.chat_text_box.insert(END, "\n")
        self.chat_text_box.config(state=DISABLED)

        self.username_entry = Entry()
        self.username_entry.grid(row=6, column=5, padx=5, pady=5, ipady=5, ipadx=5, sticky=N + S + W + E)

        self.users_list_box = Listbox(width=20, height=15)
        self.users_list_box.grid(row=0, column=5, rowspan=6, padx=5, pady=5, ipady=5, ipadx=5,
                                 sticky=N + S + W + E)

        self.username_save = Button(text="Save username", command=self.save_username)
        self.username_save.grid(row=7, column=5, padx=5, pady=5, ipady=5, ipadx=5, sticky=N + S + W + E)

        self.message_send = Button(text="Send Message", command=self.send_message)
        self.message_send.grid(row=7, column=3, padx=5, pady=5, ipady=5, ipadx=5, sticky=W + E)

        self.message = ""
        self.message_entry = Entry()
        self.message_entry.grid(row=6, column=0, padx=5, pady=5, columnspan=4, sticky=N + S + W + E)

    def set_username(self, username):
        print(self.username_entry.get())
        if self.username_entry.get() != username:
            print(username)
            self.username_entry.insert(0, username)

    def save_username(self):
        print("save username")

    def send_message(self):
        print("send message")

    def insert_message(self, message):
        self.chat_text_box.config(state=NORMAL)
        self.chat_text_box.insert(END, f"{message}\n")
        self.chat_text_box.config(state=DISABLED)



class AsncClient:
    def __init__(self, app):
        self.app = app
        self.work_client = True

    async def _tk_application_loop(self):
        global _default_root
        while self.work_client:
            try:
                self.app.update()
                await asyncio.sleep(0)
            except:
                self.work_client = False

    async def test_loop(self):
        asyncio.create_task(self._tk_application_loop())
        while self.work_client:
            self.app.insert_message(str(time.time()))
            await asyncio.sleep(1)


async def loop_main(app):
    while True:
        app.set_username("test")
        app.update()
        await asyncio.sleep(0)


root = tk.Tk()
app_tk = Application(root=root)

async_client = AsncClient(app_tk)

asyncio.run(async_client.test_loop())
