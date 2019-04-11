import asyncio
import os
import logging
from aiohttp import web
from aiohttp_cache import cache, setup_cache
import aioredis
import aiofiles

loop = asyncio.get_event_loop()


async def setup(r):
    wordlist = os.path.join(os.path.dirname(__file__), 'wordlist.txt')
    async with aiofiles.open(wordlist, mode='r') as f:
        async for line in f:
            n = line.strip()
            for l in range(1, len(n)):
                prefix = n[0:l]
                await r.zadd('compl', 0, prefix)
            await r.zadd('compl', 0, n + "*")


async def autocomplete(request):
    params = request.rel_url.query
    results = []
    try:
        if params is not None:
            prefix = params['search']
            count = 50
            r = await aioredis.create_redis(('poc_redis', 6379), loop=loop)
            rangelen = 50
            if await r.exists('compl') == False:
                print("Loading data into Redis DB\n")
                setup(r)
            else:
                print("Dummy data already loaded \n")

            print(prefix)
            start = await r.zrank('compl', prefix)
            print(start)
            if not start:
                results = []
            else:
                while (len(results) != count):
                    rangev = await r.zrange('compl', start, start + rangelen - 1)
                    start += rangelen
                    if not rangev or len(rangev) == 0:
                        break
                    for entry in [x.decode('utf-8') for x in rangev]:
                        minlen = min(len(entry), len(prefix))
                        if entry[0:minlen] != prefix[0:minlen]:
                            count = len(results)
                            break
                        if entry[-1] == "*" and len(results) != count:
                            results.append(entry[0:-1])
    except Exception as e:
        print(e)
    return web.json_response(results, content_type='text/plain')


async def index(request):
    chat_file = open(
        os.path.join(os.path.dirname(__file__), 'search.html'), 'rb').read()
    return web.Response(body=chat_file, content_type='text/html')


async def factory():

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')

    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    app.router.add_route('GET', '/autocomplete', autocomplete)
    setup_cache(app)
    return app

