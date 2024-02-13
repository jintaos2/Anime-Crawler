from __future__ import annotations
from typing import List, Dict, Callable, Literal, Generator, Any, Optional, Union
import os 
import inspect
import re
import logging 
import yaml 
import shutil
import traceback  
import sys 
import platform 
import psutil 
import datetime
import time
import threading 
import copy
from itertools import chain

# global variables
# ----------------


os_name                         = platform.system()     # 'Windows' or 'Linux'
status                          = 0                     #  once < 0: start, >=0: idle
config_lock                     = threading.RLock()
running                         = True                  # whether can run       
tasks: List[Task]               = []                    # tasks
info: Callable[[any], None]     = None 
debug: Callable[[any], None]    = None 

config = [{
    'max_log_lines'     : 400,                                                      # max lines of log
    'max_cache_items'   : 5000,                                                     # max items of cache
    'max_interval'      : 10,                                                       # 循环秒数
    'download_dir'      : '../../anime',                                            # download dir
    'aria2'             : 'http://127.0.0.1:6800/rpc',                              # aria2 rpc url
    'proxies_en'        : False,                                                    # enable proxies
    'proxies_url'       : 'http://localhost:7890',                                  # proxies url
    'error_en'          : False,                                                    # enable error
    'sources'           : {'dmhy': ['https://dmhy.org/topics/list/page/{}', 5]},    # sources
    'title':{
        'epsodes'       : '(?<=[^\\da-zB-DF-Z])\\d\\d(?=[^\\db])|(?<=第)\\d(?=话)',  # epsode filter
        'must'          : ['動畫', '简|CHS|GB|繁|CHT|BIG5'],                         # 标题必须包含的关键字
        'score'         : ['简|CHS|GB', '1080|2160'],                               # 标题得分
        'select'        : 0,                                                        # 每一集的选择顺序，0表示选择最新的
    }
}]


def relative_path(path: str, level: int = 1, check_exist: bool = False) -> str:
    """ 
    path: 
        relative path to caller's directory 
    level: 
        nth caller 
    check_exist: 
        whether check the existance of path 

    return:
        absolute path
    """
    if os.path.isabs(path):
        ret = path 
    else:
        a = os.path.dirname(inspect.stack()[level].filename)
        ret = os.path.abspath(os.path.join(a, path)) 
    if check_exist:
        assert os.path.exists(ret) 
    return re.sub(r'\\', '/', ret) 

def generator_info(g: Generator) -> str:
    return f'{os.path.basename(g.gi_code.co_filename):>13}:{g.gi_frame.f_lineno:<3}'

def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def data2yaml(data)->Optional[str]:
    if data is None:
        return None
    else:
        return yaml.dump(data, allow_unicode = True, sort_keys=False, Dumper=yaml.CDumper)

def yaml2data(yaml_str)->Optional[Dict]:
    if yaml_str is None or yaml_str == '':
        return None
    else:
        return yaml.load(yaml_str, Loader=yaml.CLoader)


class Event:
    pass 

class SleepEvent(Event):
    def __init__(self, t):
        self.t = t

class InfoEvent(Event):
    def __init__(self, s: str):
        self.s = s  

class ErrorEvent(Event): 
    def __init__(self, s: str):
        self.s = s  


class Task: 
    """
    执行顺序：
        正常循环：head -> body -> tail 
        清退：exit
    """
    def __init__(self):
        """ before loop. ex. set log handler """
        self.task_status: Literal['head', 'body', 'tail', 'exit', 'idle'] = 'idle' 
        self.task_log: List[str] = []                

    def __exec__(self, stage: Literal['head', 'body', 'tail', 'exit']):             # 执行任务  
        global info, debug
        if stage not in ['head', 'body', 'tail', 'exit']:
            raise AttributeError(f'unknown stage: {stage}, not executed') 
        if stage == 'head':
            self.task_log.clear()                                                   # 清空本地log
        func = getattr(self, f'loop_{stage}')                                       # 获取任务函数
        tag = self.__module__ + '.' + self.__class__.__qualname__
        tag = f'[{tag:>28}:{stage:<4}]'
        if not inspect.isgeneratorfunction(func):                                   # 只执行生成器
            raise TypeError(f'{tag} is not a generator function, not executed')  
        
        self.task_status = stage                                                    # 哪个阶段 
        try:
            _t = time.time()                                                            # 开始计时
            for i in (g:=func()):
                msg = f'({generator_info(g)}) {tag}'
                if isinstance(i, SleepEvent):
                    time.sleep(i.t)  
                    self.task_log.append(f'{msg} sleep {i.t}s')
                elif isinstance(i, str):
                    _s = f'{msg} {i}'
                    self.task_log.append(_s)  
                    info(_s, stacklevel=3)
                elif isinstance(i, InfoEvent):
                    _s = f'{msg} {i.s}'
                    self.task_log.append(_s) 
                    info(_s, stacklevel=3) 
                elif isinstance(i, ErrorEvent):
                    _s = f'{msg} {i.s}'
                    self.task_log.append(_s) 
                    debug(_s, stacklevel=3) 
                elif i is None:
                    continue
                else:
                    raise TypeError(f'unknown event type: {type(i)}')
            _s = f'{" ":<20}{tag} finished at {now()} for {time.time()-_t:.3f}s'
            self.task_log.append(_s)
        except: 
            _s = f'{" ":<20}{tag} error    at {now()} for {time.time()-_t:.3f}s'
            self.task_log.append(_s) 
            self.task_log.append(traceback.format_exc()) 
            debug(_s, stacklevel=3)
            debug(traceback.format_exc(), stacklevel=3)
        finally:
            self.task_status = 'idle'

    def sleep(self, t) -> Event:
        return SleepEvent(t)  
    
    def info(self, s: str) -> Event:
        return InfoEvent(s)
    
    def debug(self, s: str) -> Event:
        return ErrorEvent(s)

    def loop_head(self):
        """ get global config """ 
        yield 

    def loop_body(self):
        """ exec """ 
        yield 

    def loop_tail(self):
        """ end loop """ 
        yield 

    def loop_exit(self):
        """ clean up """
        yield 

    def __str__(self) -> str:
        return '\n'.join(self.task_log)



class LogStream(object):
    """ store log as lines """
    def __init__(self):
        self.logs: List[str] = []

    def write(self, s): 
        for i in s.splitlines(keepends=True):
            self.logs.append(i)

    def flush(self):
        pass

    def __len__(self):
        return len(self.logs)

    def __str__(self):
        return ''.join(self.logs)


class Log(Task):
    def __init__(self): 
        super().__init__()
        self.info_file = relative_path('./info.log')
        self.debug_file = relative_path('./debug.log')  
        self.logger = logging.getLogger('error') 
        self.history = LogStream()
        self.format = logging.Formatter("{asctime} ({filename:>8}:{lineno:<3}) {message}", r'%Y/%m/%d %H:%M:%S', style='{')

        # load log 
        try:
            with open(self.info_file, 'r', encoding='utf8') as f: 
                self.history.logs = f.readlines()
        except:
            pass 

        self.logger.setLevel(logging.DEBUG)  
        # add handler 
        fh_debug = logging.FileHandler(self.debug_file, mode='a', encoding='utf8')  ; fh_debug.setLevel(logging.DEBUG)
        fh_info = logging.FileHandler(self.info_file, mode='a', encoding='utf8')    ; fh_info.setLevel(logging.INFO)
        ch = logging.StreamHandler()                                                ; ch.setLevel(logging.INFO)
        sh = logging.StreamHandler(self.history)                                    ; sh.setLevel(logging.INFO)
        for i in [fh_debug, fh_info, ch, sh]:
            i.setFormatter( self.format)
            self.logger.addHandler(i) 
        self.logger.debug(f'------------------- init log {len(self.history)} lines -------------------')
        print(f'------------------- init log {len(self.history)} lines -------------------')

    def loop_head(self):
        # check config
        n = config[0].get('max_log_lines', 100) 
        # reduce info log
        if len(self.history.logs) > n*1.1:
            self.history.logs = self.history.logs[-n:] 
            # write log 
            with open(self.info_file, 'w+', encoding='utf8') as f:
                f.writelines(self.history.logs)  
        # reduce debug log
        with open(self.debug_file, 'r', encoding='utf8') as f:
            _cache = f.readlines()[-2000:] 
        with open(self.debug_file, 'w', encoding='utf8') as f:
            f.writelines(_cache)
        yield  


    def info(self, *args, stacklevel = 2):
        s = ' '.join(str(i) for i in args)
        self.logger.info(s, stacklevel=stacklevel) 

    def debug(self, *args, stacklevel = 2): 
        s = ' '.join(str(i) for i in args)
        self.logger.debug(s, stacklevel=stacklevel)  

    def __str__(self) -> str:
        return ''.join(self.history.logs)



def _valid_title_filter(d: dict) -> bool:
    if not isinstance(d, dict):
        return  False 
    for key in ['epsodes', 'must', 'score', 'select']:
        if key not in d:
            return False
    epsodes = d.get('epsodes') 
    must = d.get('must') 
    score = d.get('score')
    select = d.get('select') 
    try:
        re.compile(epsodes) 
    except:
        return False
    try: 
        [re.compile(i, re.I) for i in must] 
    except:
        return False
    try:
        [re.compile(i, re.I) for i in score] 
    except:
        return False 
    if not isinstance(select, int) or select < 0:
        return False
    return True


def update_config(data: Union[list, dict], web: bool = False)->List[str]: # return msg
    # format web data
    if web:
        data['sources'] = yaml2data(data['sources'])
        data['title'] = yaml2data(data['title'])
        debug(f'update config: {data}') 
        items = data.pop('data')
        data_list = [data]
        for item in items:
            item_ex = [i.strip() for i in item.split('\n') if i.strip()] 
            if not item_ex:
                continue
            if len(item_ex) < 2:
                yield f'invalid item: {item}'
                return 
            elif len(item_ex) == 2:
                data_list.append({'filters': item_ex[0], 'epsodes': item_ex[1]})
            else:
                data_list.append(yaml2data(item))
    else:
        data_list: list = data

    global config 
    c = config[0]; x = data_list[0]          
    temp = int(x.get('max_log_lines'))
    if temp > 10:
        c['max_log_lines'] = temp
    else:
        yield f'invalid max_log_lines: {temp}'
    temp = int(x.get('max_cache_items'))
    if temp > 100:
        c['max_cache_items'] = temp
    else:
        yield f'invalid max_cache_items: {temp}'
    temp = int(x.get('max_interval'))
    if temp > 10:
        c['max_interval'] = temp
    else:
        yield f'invalid max_interval: {temp}'
    temp = x.get('download_dir')
    if isinstance(temp, str) and temp:
        c['download_dir'] = temp
    else:
        yield f'invalid download_dir: {temp}'
    temp = x.get('aria2')
    if isinstance(temp, str) and temp.startswith('http'):
        c['aria2'] = temp
    else:
        yield f'invalid aria2: {temp}'
    temp = x.get('proxies_en')
    if isinstance(temp, bool):
        c['proxies_en'] = temp
    else:
        yield f'invalid proxies_en: {temp}'
    temp = x.get('proxies_url')
    if isinstance(temp, str) and temp.startswith('http'):
        c['proxies_url'] = temp
    else:
        yield f'invalid proxies_url: {temp}'
    temp = x.get('error_en')
    if isinstance(temp, bool):
        c['error_en'] = temp
    else:
        yield f'invalid error_en: {temp}'
    temp = x.get('sources')
    if isinstance(temp, dict):
        c['sources'] = temp
    else:
        yield f'invalid sources: {temp}'
    temp = x.get('title')
    if isinstance(temp, dict) and 'epsodes' in temp and 'must' in temp and 'score' in temp and 'select' in temp:
        c['title'] = temp
    else:
        yield f'invalid title: {temp}'

    # items 
    config[1:] = [] 
    for i in data_list[1:]:
        if not isinstance(i, dict) or 'filters' not in i or 'epsodes' not in i:
            yield f'invalid item: {i}'
            continue
        f = i.get('title') 
        if f is not None and not _valid_title_filter(f):
            yield 'invalid title: {f}' 
            i.pop('title')
        config.append(i)
    yield f'update config success, len = {len(config)-1}'


class _config(Task):

    def __init__(self):
        """ load yaml """ 
        super().__init__()
        global config  
        self.path = relative_path('../config.yaml')
        self.path_backup = relative_path('../config.backup.yaml') 

        # load from file
        try:
            with open(self.path, 'r', encoding='utf8') as f:
                config_raw = yaml.load(f, Loader=yaml.CLoader)  
        except:
            with open(self.path_backup, 'w', encoding='utf8') as f:
                config_raw = yaml.load(f, Loader=yaml.CLoader)  
        print(str(config_raw))
        msg = '\n'.join(update_config(config_raw))
        print(f'init config: {msg}')
        print(data2yaml(config))


    def loop_tail(self):
        global config 
        shutil.copyfile(self.path, self.path_backup) 
        yield self.debug(f'{self.path} backup to {self.path_backup}')
        with open(self.path, 'w', encoding='utf8') as f:
            f.write(data2yaml(config))
        yield self.debug(f'config len={len(config)} store to {self.path}')

    


_log = Log()
_config_task = _config()

tasks.append(_log)
tasks.append(_config_task)

info = _log.info
debug = _log.debug


########################################### web ###########################################

def get_status() -> str:
    cpu = psutil.cpu_percent() 
    m = psutil.virtual_memory() 
    m_used = m.used/(1 << 30) 
    m_total = m.total/(1<<30)
    m_app = psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2
    return f"""{os_name}:{now()}  CPU:{cpu}%  MEM:{m_app:.2f}MB/{m_used:.2f}GB/{m_total:.2f}GB  --> {status}""" 

def get_log() -> str:
    if not tasks: 
        return 'no tasks' 
    result = []
    for i in chain(tasks[1:], tasks[0:1]):
        result.append( f'<span style="color:green;">==============================================> {i.__class__.__name__:>10} : {i.task_status}</span>')
        result.append(str(i))
    return '\n'.join(result)
    

class AnimeBase(Task):
    pass

def search_cache(data: str) -> str:
    ret = []
    data = [i.strip() for i in data.split('\n') if i.strip()] + ['','','']
    if data[0]:
        epsode_re = re.compile(data[0])
    else:
        epsode_re = re.compile(r'(?<=[\WAE])\d\d(?=[\Wv])|(?<=第)\d\d(?=[话話])')
    if data[1]:
        title_re = re.compile(data[1], re.I)
    else:
        title_re = re.compile('.*')
    if data[2]:
        n = int(data[2])
    else:
        n = 10
    for task in tasks:
        if isinstance(task, AnimeBase): 
            ret.append(f'{task.__class__.__name__}:') 
            count = 0
            for i in reversed(task.cache.values()):
                if title_re.search(i.release_title):
                    ret.append(f'{epsode_re.findall(i.release_title)}, {i}')  
                    count += 1 
                if count >= n:
                    break 
    return '\n'.join(ret)

