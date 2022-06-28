'''
Author: Exarlos
Date: 2022-06-18 17:05:51
LastEditors: Exarlos
LastEditTime: 2022-06-18 21:45:51
Description: 世界上没有低级的法术,只有低级的法师!
'''


import functools
import logging


from aiohttp import web_app
import inspect
from aiohttp import web
from urllib import parse
from apis import APIError
import os
import asyncio


def get(path):
    """_summary_
    Define decorator @get('/path')

    Args:
        path (_type_): _description_
    """
    # def decorator(func):
    #     @web_app.get(path)
    #     async def wrapper(request):
    #         return await func(request)
    #     return wrapper
    # return decorator
    def decorator(func):
        # 使得 wrapper.__name__ 等于 func.__name__
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator


def post(path):
    """
    Define decorator @post('/path')

    :param path:
    :return:
    """

    def decorator(func):
        # 使得 wrapper.__name__ = func.__name__
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper

    return decorator

# 下面这部分可以自行查阅 inspect 模块来理解
# https://docs.python.org/zh-cn/3.8/index.html

# * 获取函数命名关键字参数，且非默认参数

# 检查 是否有命名关键字参数,且该参数没有默认值


def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        # * 或者 *args 后面的参数，且没有默认值
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            # 在 args 里加上仅包含关键字（keyword）的参数,就是只接受字典传参， 且不包括默认值， 然后返回 args
            args.append(name)
    return tuple(args)
    # 所以这个函数的作用和名称一样， 得到需要的关键字参数, 下面同理

# 获取命名关键字参数


def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

# 这里就是个判断布尔, 如果有 命名request 关键字参数, 就返回 True


def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for _, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 检查是否有随机参数,有了就返回 True


def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for _, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 是否有 request 参数,且参数不是随机参数,不是命名关键字参数,部署关键字参数就报错


def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (
                fn.__name__, str(sig)))
    return found

# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数
# 调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求
# 这一段我没看明白


class RequestHandler(object):
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        # 这些函数以及后续的处理都是在判断route和handler两者信息是否匹配,参数是否都匹配
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest(reason='Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(reason='JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(reason='Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning(
                        'Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest(reason='Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

# * 路由里增加static的路径


def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

# add_route函数的作用是把一个URL地址与一个函数绑定


def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (
        method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

# add_routes函数的作用是把所有的URL地址与对应的函数绑定


def add_routes(app, module_name):
    # For package.module, n = 7
    # For module, n = -1
    n = module_name.rfind('.')
    if n == -1:
        # Import module
        mod = __import__(module_name, globals(), locals())
    else:
        # For package.module, name = module
        name = module_name[n + 1:]
        # Import package.module, the same as 'from package import module', fromlist = [module]
        mod = getattr(__import__(
            module_name[:n], globals(), locals(), [name]), name)
    # Directory of attributes of module
    for attr in dir(mod):
        if attr.startswith('__'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)
