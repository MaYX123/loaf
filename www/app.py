#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Nina'

'''
async web application.
'''

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

import logging
logging.basicConfig(level=logging.INFO)


def index(request):
    return web.Response(body='<h1>Awesome测试</h1>'.encode('GBK'), headers={'content-type':'text/html'})


async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
