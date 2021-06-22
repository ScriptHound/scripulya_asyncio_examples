import asyncio
import aiohttp

# доступ максимально для двух корутин
simultaneous_coroutines = 2
semaphore = asyncio.Semaphore(simultaneous_coroutines)


async def request_data():
    async with semaphore:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://readmanga.live/') as resp:
                print("Receiving data from internet")
                return await resp.text()


async def manipulate_data():
    print("Data requested")
    asyncio.sleep(1)
    await request_data()
    print("Manipulated data")


if __name__ == '__main__':
    # создаём 10 корутин
    coroutines = [manipulate_data() for _ in range(10)]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*coroutines))
