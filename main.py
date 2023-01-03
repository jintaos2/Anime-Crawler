import time 
import os
import subprocess 
import xmlrpc.client
import traceback

import log
import web
import update


@log.add_task 
class aria2(log.Task):
    def __init__(self):
        self.p = None
        try:
            aria2 = xmlrpc.client.ServerProxy("http://127.0.0.1:6800/rpc")
            aria2.aria2.getGlobalStat() 
            log.error_log.error('[loop_init] aria2 found')
        except:
            try:
                if log.os_name == 'Windows':
                    self.p = subprocess.Popen(
                        log.relative_path('aria2/aria.bat'), 
                        cwd=log.relative_path('aria2/'), 
                        stdout=None, 
                        stderr=None, 
                    ) 
                    log.error_log.error('[loop_init] aria2 start on windows')
                elif log.os_name == 'Linux':
                    self.p = subprocess.Popen(
                        log.relative_path('aria2/aria.sh'), 
                        cwd=log.relative_path('aria2/'), 
                        stdout=None, 
                        stderr=None,
                    ) 
                    log.error_log.error('[loop_init] aria2 start on linux')
            except:
                log.error_log.error('[loop_init] aria2 not found and start failed')

    def loop_exit(self):
         if self.p is not None:
            self.p.kill()
            log.error_log.error('[loop_exit] aria2 killed')


if __name__ == '__main__':
    try:
        counter = 0
        while 1: 
            time.sleep(0.2) 
            counter += 1
            if log.idle: 
                log.status = '' 
                counter = 0 
            elif counter == 1:  
                try:
                    log.status = 'loop_head' 
                    for task in log.tasks: task.loop_head() 
                    log.status = 'loop_body'
                    for task in log.tasks: task.loop_body()
                    log.status = 'loop_tail'
                    for task in log.tasks: task.loop_tail()   
                except:
                    log.error_log.info(traceback.format_exc()) 
                log.error_log.error()
            elif 1 < counter < 900*5:
                log.status = f'loop_waiting {counter*0.2:.1f} s' 
            else: 
                counter = 0
    except (KeyboardInterrupt, SystemExit):
        for task in log.tasks:
            task.loop_exit() 
        time.sleep(0.2)
        os._exit(0)
 


