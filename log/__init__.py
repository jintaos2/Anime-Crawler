from __future__ import annotations
from typing import List, Dict, Callable
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

# global variables
# ----------------
os_name = platform.system()

# debug flag
debug = len(sys.argv) > 1

# app status
idle = False   
status = 'not start'
flask_port = 6801

# config.yaml
config: List[Dict] = [{}]
tasks: List[Task] = []


class Task: 
    def __init__(self):
        """ before loop. ex. set log handler """

    def loop_head(self):
        """ start loop. ex. check config, get url, dir, filter """ 

    def loop_body(self):
        """ loop body. ex. get cache, match and download """ 

    def loop_tail(self):
        """ end loop. ex. write back config """ 

    def loop_exit(self):
        """ clean up """

    def __str__(self) -> str:
        return f'Task: {self.__class__.__name__}'


def add_task(cls):
    """ decorator """ 
    ret = cls() 
    tasks.append(ret) 
    return ret


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


@add_task 
class load_config(Task):
    def __init__(self):
        """ load yaml """
        global config  
        self.path = relative_path('../config.yaml')
        self.path_backup = relative_path('../config.backup.yaml')
        try:
            with open(self.path, 'r', encoding='utf8') as f:
                config = yaml.load(f, Loader=yaml.CLoader)  
            shutil.copyfile(self.path, self.path_backup)
        except:
            with open(self.path_backup, 'w', encoding='utf8') as f:
                config = yaml.load(f, Loader=yaml.CLoader)  
        finally:
            self._check_config()
            print(f'[loop_init] load_config len={len(config)}')

    def _check_config(self):
        global config
        if not isinstance(config, list) or not config or not isinstance(config[0], dict):
            config = [{}]         

    def loop_head(self):
        self._check_config() 
        error_log.error(f'[loop_head] config check: len={len(config)}')

    def loop_tail(self):
        with open(self.path, 'w', encoding='utf8') as f:
            yaml.dump(config, f, Dumper=yaml.CDumper, allow_unicode=True, sort_keys=False) 
        error_log.error(f'[loop_tail] config store to {self.path}')

    

class LogStream(object):
    """ store log as lines """
    def __init__(self):
        self.logs: List[str] = []

    def write(self, s): 
        for i in s.splitlines(keepends=True):
            self.logs.append(i)

    def flush(self):
        pass

    def __str__(self):
        return str(self.logs)


@add_task 
class error_log(Task):
    def __init__(self):
        self.logger = logging.getLogger('error') 
        self.logger.setLevel(logging.INFO)  
        self.history = LogStream()
        self.format = logging.Formatter("{asctime} ({filename:>12}:{lineno:<3}) {message}", r'%Y/%m/%d %H:%M:%S', style='{')
        debug_file = relative_path('./debug.log')  
        # load log and reduce log size
        try:
            with open(debug_file, 'r', encoding='utf8') as f: 
                self.history.logs = f.readlines()
        finally: 
            self._check_config()
            with open(debug_file, 'w+', encoding='utf8') as f:
                f.writelines(self.history.logs) 
        # add handler
        fh = logging.FileHandler(debug_file, mode='a', encoding='utf8') 
        ch = logging.StreamHandler() 
        sh = logging.StreamHandler(self.history) 
        for i in [fh, ch, sh]:
            i.setLevel(logging.INFO)
            i.setFormatter( self.format)
            self.logger.addHandler(i) 
        self.error(f'[loop_init] error_log cache: {len(self.history.logs)} lines')

    def _check_config(self):
        # check config
        n = config[0].get('max_log_lines') 
        if not isinstance(n, int) or n < 100:
            config[0]['max_log_lines'] = 100  
            n = 100 
        # reduce log
        if len(self.history.logs) > n*1.4:
            self.history.logs = self.history.logs[-n:] 

    def loop_head(self):
        self._check_config()
        self.error(f'[loop_head] error_log cache: {len(self.history.logs)} lines')

    def info(self, *args, stacklevel = 2):
        s = ' '.join(str(i) for i in args)
        self.logger.info(s, stacklevel=stacklevel) 

    def error(self, *args, stacklevel = 2): 
        if debug:
            s = ' '.join(str(i) for i in args)
            self.logger.error(s, stacklevel=stacklevel) 

    def __str__(self) -> str:
        return f'error_log: keep {len(self.history.logs)} lines of log'



def get_log_lines():
    return ''.join(error_log.history.logs)


def get_config():
    return yaml.dump(config, allow_unicode = True, sort_keys=False, Dumper=yaml.CDumper)


def get_status() -> str:
    cpu = psutil.cpu_percent() 
    m = psutil.virtual_memory() 
    m_used = m.used/(1 << 30) 
    m_total = m.total/(1<<30)
    m_app = psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2
    return f"{datetime.datetime.now()}<br>{os_name} cpu: <mark>{cpu}%</mark> mem: <mark>{m_app}MB/{m_used:.2f}GB/{m_total:.2f}GB</mark><br>status: <mark>{status or 'stopped'}</mark>"


def set_config(s:str) -> bool: 
    if status:
        return False
    global config
    try: 
        new_config = yaml.load(s, Loader=yaml.CLoader)  
        _ = new_config[0]['max_log_lines'] + 1
        config = new_config
        return True
    except: 
        error_log.info('[parse config from web error] ', traceback.format_exc())
        return False