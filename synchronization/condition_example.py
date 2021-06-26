import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)


async def download_huge_file(condition):
    # just a huge file
    download_url = 'https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip'
    async with condition:
        async with aiohttp.ClientSession() as session:
            logging.info("Download started")
            async with session.get(download_url) as response:
                content = await response.read()
                logging.info("Download complete")
                condition.notify_all()
                return content


async def coroutine_one(condition):
    async with condition:
        logging.info("[coroutine one] Condition aquired, waiting for event")
        await condition.wait()
        logging.info("[coroutine one] Event triggered")


async def coroutine_two(condition):
    async with condition:
        logging.info("[coroutine two] Condition aquired, waiting for event")
        await condition.wait()
        logging.info("[coroutine two] Event triggered")


async def main():
    cond = asyncio.Condition()
    await asyncio.gather(
        coroutine_one(cond),
        coroutine_two(cond),
        download_huge_file(cond)
    )


loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(main()))
