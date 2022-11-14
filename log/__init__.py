from __future__ import annotations
from typing import List, Dict, Callable
import os 
import inspect
import re
import logging 
import yaml 
import shutil
import traceback 

# global variables
# ----------------
# config.yaml
config: List[Dict] = [{}]
tasks: List[Task] = []
debug = False


class Task: 
    def __init__(self):
        """ before loop. ex. set log handler """

    def loop_head(self):
        """ start loop. ex. check config, get url, dir, filter """ 

    def loop_body(self):
        """ loop body. ex. get cache, match and download """ 

    def loop_tail(self):
        """ end loop. ex. write back config """ 

    def __str__(self) -> str:
        return self.__class__.__name__


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
            self.loop_head()

    def loop_head(self):
        global config
        if not isinstance(config, list) or not config or not isinstance(config[0], dict):
            config = [{}]  

    def loop_tail(self):
        global config
        with open(self.path, 'w', encoding='utf8') as f:
            yaml.dump(config, f, Dumper=yaml.CDumper, allow_unicode=True, sort_keys=False) 


    def load_str(self, s: str) -> bool:
        global config
        try: 
            new_config = yaml.load(s, Loader=yaml.CLoader)  
            _ = new_config[0]['max_log_lines'] 
            config = new_config
            return True
        except: 
            error_log.info(traceback.format_exc())
            return False


    def __str__(self) -> str:
        return yaml.dump(config, allow_unicode = True, sort_keys=False, Dumper=yaml.CDumper)
    

    

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
        self.format = logging.Formatter(
            "%(asctime)s (%(filename)s:%(lineno)d) %(message)s ",'%Y/%m/%d %H:%M:%S'
        )
        # formatter = logging.Formatter("%(asctime)s %(message)s",'%Y/%m/%d %H:%M:%S')
        debug_file = relative_path('./debug.log')  
        # load log and reduce log size
        try:
            with open(debug_file, 'r', encoding='utf8') as f: 
                self.history.logs = f.readlines()
        finally: 
            self.loop_head()
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
        self.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")  

    def loop_head(self):
        # check config
        n = config[0].get('max_log_lines') 
        if not isinstance(n, int) or n < 100:
            config[0]['max_log_lines'] = 100  
            n = 100 
        # reduce log
        if len(self.history.logs) > 2*n:
            self.history.logs = self.history.logs[-n:] 


    def get_history(self) -> List[str]:
        return self.history.logs

    def info(self, *args, stacklevel = 2):
        s = ' '.join(str(i) for i in args)
        self.logger.info(s, stacklevel=stacklevel) 

    def error(self, *args, stacklevel = 2): 
        if debug:
            s = ' '.join(str(i) for i in args)
            self.logger.error(s, stacklevel=stacklevel) 

    def __str__(self) -> str:
        return f'error_log: keep {len(self.history.logs)} lines of log'


