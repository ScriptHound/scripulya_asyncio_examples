import asyncio
import aiohttp
from time import perf_counter

cache = {}
stuff_lock = asyncio.Lock()
SLOW_URL = 'https://readmanga.live/sitemap.xml'


async def make_cached_get_request(url, cache: dict):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            stuff = await resp.text()
            cache[url] = stuff
            return stuff


# попробуйте снять stuff_lock с этой функции
# и увидете, что урл не попадёт в кеш
async def get_stuff(url):
    async with stuff_lock:
        global cache
        if url in cache:
            print(url)
            return cache[url]
        return await make_cached_get_request(url, cache)
        

async def parse_stuff():
    return await get_stuff(SLOW_URL)


async def use_stuff():
    return await get_stuff(SLOW_URL)


async def main():
    time_start = perf_counter()
    await asyncio.gather(
        parse_stuff(),
        use_stuff(),
    )
    exec_time = perf_counter() - time_start
    print(f"Execution time: {exec_time} seconds")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
