from __future__ import annotations
from typing import List, Dict, Callable, Literal, Generator, Optional
import time 
import os
import sys 
import subprocess 
import xmlrpc.client
import traceback
import datetime
import psutil
import yaml
import re
import threading

import log 
import update

import web



class aria2(log.Task):
    def __init__(self):
        super().__init__()  
        self.p = None
        
    def loop_head(self):
        try:
            aria2 = xmlrpc.client.ServerProxy("http://127.0.0.1:6800/rpc")
            aria2.aria2.getGlobalStat() 
            yield self.debug('aria2 already running')
        except:
            try:
                if log.os_name == 'Windows':
                    self.p = subprocess.Popen(
                        log.relative_path('aria2/aria.bat'), 
                        cwd=log.relative_path('aria2/'), 
                        stdout=None, 
                        stderr=None, 
                    ) 
                    yield self.info('aria2 start on windows')
                elif log.os_name == 'Linux':
                    self.p = subprocess.Popen(
                        log.relative_path('aria2/aria.sh'), 
                        cwd=log.relative_path('aria2/'), 
                        stdout=None, 
                        stderr=None,
                    ) 
                    yield self.info('aria2 start on linux')
            except:
                yield self.info('aria2 not found and start failed')

    def loop_exit(self):
         yield self.debug(f'aria2 exit: {self.p}')
         if self.p is not None:
            self.p.kill()
            yield 


log.tasks.append(aria2())
log.tasks.append(update.anime.dmhy()) 
log.tasks.append(update.download.match_rule())




t = threading.Thread(target=lambda: web.app.run(host='0.0.0.0', port=2333, debug=False, use_reloader=False))
t.daemon = True
t.start()



n_loop = 0
try:
    while 1:                                            # 正常循环  
        time.sleep(2)
        with log.config_lock:
            if not log.running:
                continue
            if log.status < 0:                          # 等待
                log.status += 2
            else:
                log.status = - max(int(log.config[0].get('max_interval')), 3)  
                n_loop += 1
                log.debug(f'--------------------------- loop {n_loop} ---------------------------')
                for task in log.tasks:
                    task.__exec__('head')
                for task in log.tasks:
                    task.__exec__('body') 
                for task in log.tasks:
                    task.__exec__('tail')
except (KeyboardInterrupt, SystemExit):                 # 终止程序
    log.debug(f'keyboard interrupt on {datetime.datetime.now()}')
    for task in log.tasks:
        task.__exec__('exit') 
except:                                                 # 其他异常
    log.debug(f'other exception on {datetime.datetime.now()}') 
    log.debug(traceback.format_exc())
finally:
    sys.exit(0)



