'''
Author: Exarlos
Date: 2022-06-18 22:24:49
LastEditors: Exarlos
LastEditTime: 2022-06-19 01:06:27
Description: 世界上没有低级的法术,只有低级的法师!
'''
# 直接导入config_default.py中的通用配置信息
import config_default


class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''

    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

# 将两个配置文件合并的代码

# 这里用的是递归的方式将两个配置文件合并


def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

# 将配置文件返回为字典


def toDict(d):
    D = Dict()
    # 下面两行是用于支持这样的写法
    # a=Dict(names=('aa','bb'),values=(1,2),c=3)
    #a={'c': 3, 'aa': 1, 'bb': 2}
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D


configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)
