import asyncio


async def callbacked(event: asyncio.Event):
    print("Initiated coro")
    await event.wait()
    print("Callbacked coro triggered")


async def another_callbacked(event: asyncio.Event):
    print("Initiated another coro")
    await event.wait()
    print("Another callbacked coro triggered")


async def background_coro():
    print("Longterm coroutine")
    await asyncio.sleep(5)
    print("-----------Longterm coroutine has finished-----------")


async def main():
    while True:
        event = asyncio.Event()
        # заставим callbacked ждать пока 
        # евент случится
        asyncio.create_task(callbacked(event))
        asyncio.create_task(another_callbacked(event))
        longterm_task = asyncio.create_task(background_coro())

        await longterm_task
        # стоит обратить внимание, что 
        # теперь для вызова таски или нескольких 
        # достаточно триггернуть евент
        event.set()
        

asyncio.run(main())
