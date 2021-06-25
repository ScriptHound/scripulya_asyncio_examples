import asyncio
import aiohttp


async def download_huge_file(condition):
    # just a huge file
    download_url = 'https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip'
    async with condition:
        async with aiohttp.ClientSession() as session:
            print("Download started")
            async with session.get(download_url) as response:
                content = await response.read()
                print("Download complete")
                condition.notify_all()
                return content


async def coroutine_one(condition):
    async with condition:
        print("[coroutine one] Condition aquired, waiting for event")
        await condition.wait()
        print("[coroutine one] Event triggered")


async def coroutine_two(condition):
    async with condition:
        print("[coroutine two] Condition aquired, waiting for event")
        await condition.wait()
        print("[coroutine two] Event triggered")


async def main():
    cond = asyncio.Condition()
    await asyncio.gather(
        coroutine_one(cond),
        coroutine_two(cond),
        download_huge_file(cond)
    )


loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(main()))
