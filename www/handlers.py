'''
Author: Exarlos
Date: 2022-06-19 00:11:20
LastEditors: Exarlos
LastEditTime: 2022-06-22 17:08:54
Description: 世界上没有低级的法术,只有低级的法师!
'''

import re
import time
import json
import logging
import hashlib
import base64


# import asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id


@get('/')
async def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary,
             created_at=time.time()-120),
        Blog(id='2', name='Something New',
             summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary,
             created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy='created_at desc')
    for u in users:
        u.passwd = '******'
    return dict(users=users)

# 处理注册页面URL


@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

# @get('/')
# async def index(request):
#     users = await User.findAll()
#     return {
#         '__template__': 'test.html',
#         'users': users
#     }
