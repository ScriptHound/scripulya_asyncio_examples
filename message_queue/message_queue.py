import asyncio
from asyncio.queues import Queue
import concurrent.futures
import random


class TaskQueue:
    def __init__(self) -> None:
        self._queue = Queue()
        self.consumers = []

    async def _consumer(self, pool):
        # This loop is not freezing, it only makes
        # consumer do tasks forever
        while True:
            function = await self._queue.get()

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(pool, function)
            self._queue.task_done()

    async def create_task(self, task):
        await self._queue.put(task)

    async def run_tasks(self):
        # here are 10 workers created and then wait until
        # all tasks done
        with concurrent.futures.ProcessPoolExecutor() as pool:
            consumers = [asyncio.create_task(
                self._consumer(pool))
                for _ in range(10)]
            await self._queue.join()
            for c in consumers:
                c.cancel()


def sometask_todo():
    task_number = random.random() * 100
    for i in range(10):
        print(f'Number from task #{task_number} is {i}')


async def main():
    queue = TaskQueue()
    producers = [
        asyncio.create_task(queue.create_task(sometask_todo))
        for _ in range(5)]
    await asyncio.gather(*producers)
    await queue.run_tasks()


asyncio.run(main())
