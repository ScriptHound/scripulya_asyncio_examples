import asyncio
import concurrent.futures
import random


def sometask_todo():
    task_number = random.random() * 100
    for i in range(10):
        print(f'Number from task #{task_number} is {i}')


async def producer(queue, function):
    await queue.put(function)
    print("Created a task")


async def consumer(queue, pool):
    while True:
        function = await queue.get()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(pool, function)
        queue.task_done()
        print("Task complete")


async def main():
    queue = asyncio.Queue()
    producers = [
        asyncio.create_task(producer(queue, sometask_todo))
        for _ in range(5)]

    with concurrent.futures.ProcessPoolExecutor() as pool:
        consumers = [asyncio.create_task(consumer(queue, pool))
                     for _ in range(10)]
        await asyncio.gather(*producers)
        await queue.join()
        for c in consumers:
            c.cancel()


asyncio.run(main())
