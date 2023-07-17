from __future__ import annotations
from typing import List, Dict, Callable, Literal, Generator, Any
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

# global variables
# ----------------


os_name = platform.system()     # 'Windows' or 'Linux'
status = 0                      #  <0: stopped, >=0: running
config_lock = threading.RLock()
config: List[Dict] = [{
    'max_log_lines'     : 400,                                                      # max lines of log
    'max_cache_items'   : 5000,                                                     # max items of cache
    'max_interval'      : 10,                                                       # 循环秒数
    'download_dir'      : '../../anime',                                            # download dir
    'aria2'             : 'http://127.0.0.1:6800/rpc',                              # aria2 rpc url
    'proxies_en'        : False,                                                    # enable proxies
    'proxies_url'       : 'http://localhost:7890',                                  # proxies url
    'sources'           : {'dmhy': ['https://dmhy.org/topics/list/page/{}', 5]},    # sources
    'title':{
        'epsodes'       : '(?<=[^\\da-zB-DF-Z])\\d\\d(?=[^\\db])|(?<=第)\\d(?=话)',  # epsode filter
        'must'          : ['動畫', '简|CHS|GB|繁|CHT|BIG5'],                         # 标题必须包含的关键字
        'score'         : ['简|CHS|GB', '1080|2160'],                               # 标题得分
        'select'        : 0,                                                        # 每一集的选择顺序，0表示选择最新的
    }
}]                              # config.yaml
tasks: List[Task] = []          # tasks



def relative_path(path: str, level: int = 1, check_exist: bool = False) -> str:
    """ 
    path: 
        relative path to caller's directory/path 
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
    return f'{g.gi_code.co_filename}:{g.gi_frame.f_lineno}'

def valid_title_filter(d: Any) -> Dict:
    if not isinstance(d, dict):
        d = {}
    epsodes = d.get('epsodes', '(?<=[^\\da-zB-DF-Z])\\d\\d(?=[^\\db])|(?<=第)\\d(?=话)') 
    must = d.get('must', ['動畫', '简|CHS|GB|繁|CHT|BIG5']) 
    score = d.get('score', ['简|CHS|GB', '1080|2160'])
    select = d.get('select', 0) 

    try:
        re.compile(epsodes) 
    except:
        epsodes = '(?<=[^\\da-zB-DF-Z])\\d\\d(?=[^\\db])|(?<=第)\\d(?=话)' 
    try: 
        [re.compile(i, re.I) for i in must] 
    except:
        must = ['動畫', '简|CHS|GB|繁|CHT|BIG5'] 
    try:
        [re.compile(i, re.I) for i in score] 
    except:
        score = ['简|CHS|GB', '1080|2160'] 
    if not isinstance(select, int) or select < 0:
        select = 0 
    return {
        'epsodes': epsodes,
        'must': must,
        'score': score,
        'select': select,
    }


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
        self.task_log: List[str] = []                
        self.task_status: Literal['head', 'body', 'tail', 'exit', 'idle'] = 'idle' 

    def __exec__(self, stage: Literal['head', 'body', 'tail', 'exit']):             # 执行任务 
        if stage not in ['head', 'body', 'tail', 'exit']:
            return 
        if stage == 'head':
            self.task_log.clear()                                                   # 清空本地log
        func = getattr(self, f'loop_{stage}')                                       # 获取任务函数
        if not inspect.isgeneratorfunction(func):                                   # 只执行生成器
            return  
        
        self.task_status = stage                                                    # 哪个阶段 
        _t = time.time()                                                            # 开始计时
        try:
            for i in (g:=func()):
                if isinstance(i, SleepEvent):
                    time.sleep(i.t)  
                    self.task_log.append(f'[{stage}->{self.__class__.__name__}] sleep {i.t}s')
                elif isinstance(i, str):
                    self.task_log.append(f'[{stage}->{self.__class__.__name__}] {i}')  
                elif isinstance(i, InfoEvent):
                    _s = f'[{stage}->{self.__class__.__name__}] {i.s}'
                    self.task_log.append(_s) 
                    log.info(f'({generator_info(g)}) {_s}', stacklevel=3) 
                elif isinstance(i, ErrorEvent):
                    _s = f'[{stage}->{self.__class__.__name__}] {i.s}' 
                    self.task_log.append(_s) 
                    log.debug(f'({generator_info(g)}) {_s}', stacklevel=3)
                elif i is None:
                    continue
                else:
                    raise TypeError(f'unknown event type: {type(i)}')
            self.task_log.append(f'[{stage}->{self.__class__.__name__}] finished at {datetime.datetime.now()} for {time.time()-_t:.3f}s')
        except: 
            self.task_log.append(f'[{stage}->{self.__class__.__name__}] error    at {datetime.datetime.now()} for {time.time()-_t:.3f}s') 
            self.task_log.append(traceback.format_exc()) 
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

    def loop_body(self):
        """ exec """ 

    def loop_tail(self):
        """ end loop """ 

    def loop_exit(self):
        """ clean up """

    def __str__(self) -> str:
        return '\n'.join(self.task_log)



class load_config(Task):

    def __init__(self):
        """ load yaml """ 
        super().__init__()
        global config  
        self.path = relative_path('../config.yaml')
        self.path_backup = relative_path('../config.backup.yaml')
        try:
            with open(self.path, 'r', encoding='utf8') as f:
                config_raw = yaml.load(f, Loader=yaml.CLoader)  
        except:
            with open(self.path_backup, 'w', encoding='utf8') as f:
                config_raw = yaml.load(f, Loader=yaml.CLoader)  

        config = config_raw  
        self.fix_config() 
        print('load config:')
        print(yaml.dump(config, Dumper=yaml.CDumper, allow_unicode=True, sort_keys=False))

    def fix_config(self):
        global config 
        if not isinstance(config, list) or len(config) < 1 or not isinstance(config[0], dict):
            config = [{}] 
        c = config[0]           # only check global part of config 
        if 'max_log_lines' not in c or not isinstance(c['max_log_lines'], int) or c['max_log_lines'] < 10:
            c['max_log_lines'] = 10
        if 'max_cache_items' not in c or not isinstance(c['max_cache_items'], int) or c['max_cache_items'] < 100:
            c['max_cache_items'] = 100
        if 'max_interval' not in c or not isinstance(c['max_interval'], int) or c['max_interval'] < 10:
            c['max_interval'] = 10
        if 'download_dir' not in c or not isinstance(c['download_dir'], str):
            c['download_dir'] = '../../anime'
        if 'aria2' not in c or not isinstance(c['aria2'], str):
            c['aria2'] = 'http://127.0.0.1:6800/rpc' 
        if 'proxies_en' not in c or not isinstance(c['proxies_en'], bool):
            c['proxies_en'] = False
        if 'proxies_url' not in c or not isinstance(c['proxies_url'], str):
            c['proxies_url'] = 'http://localhost:7890' 
        if 'sources' not in c or not isinstance(c['sources'], dict):
            c['sources'] = {'dmhy': ['https://dmhy.org/topics/list/page/{}', 5]}
        c['title'] = valid_title_filter(c.get('title'))
        for i in range(1, len(config)):
            if not isinstance(config[i], dict):
                config[i] = {}

    def loop_head(self):  
        self.fix_config()
        yield self.debug(f'config len={len(config)}')

    def loop_tail(self):
        global config_lock
        global config 

        shutil.copyfile(self.path, self.path_backup) 
        yield self.debug(f'{self.path} backup to {self.path_backup}')

        with config_lock:
            self.fix_config()
            with open(self.path, 'w', encoding='utf8') as f:
                yaml.dump(config, f, Dumper=yaml.CDumper, allow_unicode=True, sort_keys=False) 
            yield self.debug(f'config len={len(config)} store to {self.path}')

    

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
        self.logger.info(f'----------------------- start log {len(self.history)} lines')
        self.logger.debug('logging debug')

    def loop_head(self):
        # check config
        n = config[0].get('max_log_lines', 100) 
        # reduce log
        if len(self.history.logs) > n*1.2:
            self.history.logs = self.history.logs[-n:] 
            # write log 
            with open(self.info_file, 'w+', encoding='utf8') as f:
                f.writelines(self.history.logs) 
        yield f'log write to {self.info_file}'   # do not yield self.info and self.debug 


    def info(self, *args, stacklevel = 2):
        s = ' '.join(str(i) for i in args)
        self.logger.info(s, stacklevel=stacklevel) 

    def debug(self, *args, stacklevel = 2): 
        s = ' '.join(str(i) for i in args)
        self.logger.debug(s, stacklevel=stacklevel) 

# first task 
tasks.append(load_config())
# second task
log = Log()
tasks.append(log)

