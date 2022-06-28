'''
Author: Exarlos
Date: 2022-06-16 01:38:56
LastEditors: Exarlos
LastEditTime: 2022-06-21 00:25:27
Description: 世界上没有低级的法术,只有低级的法师!
'''

from coroweb import add_routes, add_static
import orm
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import logging
from aiohttp import web
import asyncio
import os
import json
import time

from config import configs

# 简单设置一个logger
logging.basicConfig(level=logging.INFO)
# 初始化jinja2模板


def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # await asyncio.sleep(0.3)
        # r = await handler(request)
        # if r is not None:
        #     return r
        return (await handler(request))
    return logger

# 暂时没用,是用来处理post的


async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data


async def response_factory(app, handler):
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(
                    r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(
                    template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(text=r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(text=t, body=str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

# 这里config是第六天的内容


async def init_db(app):
    # If on Linux, use another user instead of 'root'
    await orm.create_pool(
        loop,
        host=configs.db.host,
        port=configs.db.port,
        user=configs.db.user,
        password=configs.db.password,
        db=configs.db.db
    )


# # * 这里是一个简单的路由管理器
# routes = web.RouteTableDef()

# # * 这里需要设置返回的html就可以了,然后注册一个路由,用一个装饰器


# @ routes.get('/hello')
# async def hello(request):
#     return web.Response(body=b'<h1>Hello, world!<h1>', content_type='text/html')


# @ routes.get('/')
# async def index(request):
#     logging.info('index')
#     # 需要些content_type 要不然会下载一个文件
#     return web.Response(body=b'<h1>Awesome<h1>', content_type='text/html')

# 注册启动函数,并添加路由表
app = web.Application(middlewares=[
    logger_factory,
    response_factory
])
init_jinja2(app, filters=dict(datetime=datetime_filter))
add_routes(app, 'handlers')
add_static(app)

loop = asyncio.get_event_loop()
app.on_startup.append(init_db)  # app启动之后,数据库连接池初始化

# app.add_routes(routes)

# 程序运行
web.run_app(app, host='127.0.0.1', port=8080)
