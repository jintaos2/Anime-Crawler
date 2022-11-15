import time 
import datetime
import sys
import os
import threading 
import subprocess 
import platform 
import psutil
import xmlrpc.client
import traceback

from flask import Flask, render_template_string, request

import log
import live_update

# debug flag
if len(sys.argv) > 1:
    log.debug = True

os_name = platform.system()


# start aria 
try:
    aria2 = xmlrpc.client.ServerProxy("http://127.0.0.1:6800/rpc")
    aria2.aria2.getGlobalStat() 
except:
    if os_name == 'Windows':
        aria = subprocess.Popen(
            log.relative_path('aria2/aria.bat'), 
            cwd=log.relative_path('aria2/'), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            shell=True,
        ) 
    elif os_name == 'Linux':
        aria = subprocess.Popen(
            log.relative_path('aria2/aria.sh'), 
            cwd=log.relative_path('aria2/'), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        ) 

# app status
status = 'not start'
idle = False  

def get_system_status() -> str:
    cpu = psutil.cpu_percent() 
    m = psutil.virtual_memory() 
    m_used = m.used/(1 << 30) 
    m_total = m.total/(1<<30)
    return f"{datetime.datetime.now()}<br>{os_name} cpu: <mark>{cpu}%</mark> mem: <mark>{m_used:.2f}GB/{m_total:.2f}GB</mark><br>status: <mark>{status or 'stopped'}</mark>"

def run():
    global status, idle
    counter = 0
    while 1:
        time.sleep(0.2) 
        counter += 1
        if idle: 
            status = '' 
            counter = 0 
        elif counter == 1:  
            status = 'loop_head' 
            t = time.time() 
            try:
                for task in log.tasks:
                    task.loop_head() 
                status = 'loop_body'
                for task in log.tasks:
                    task.loop_body()
                status = 'loop_tail'
                for task in log.tasks:
                    task.loop_tail()   
            except:
                log.error_log.info(traceback.format_exc())
            log.error_log.error(f'[total cost] {time.time()-t} s')
        elif counter > 900*5:         # loop interval
            counter = 0
        else:
            status = f'loop_waiting {counter*0.2} s' 
 


task = threading.Thread(target=run)
task.daemon = True
task.start()

app = Flask(__name__)

@app.route('/get_log',methods=['GET','POST'])
def get_log(): 
    return {
        'log' : ''.join(log.error_log.get_history()), 
        'status': get_system_status(), 
        'config': str(log.load_config),
    }

@app.route('/stop_app',methods=['GET','POST'])
def stop_app(): 
    log.error_log.error('press stop')
    global idle, status
    idle = True 
    for _ in range(10):
        if status:
            time.sleep(0.2) 
        else:
            return 'stopped'
    return 'cannot stop'

@app.route('/set_config',methods=['GET','POST'])
def set_config(): 
    global idle, status 
    if status: 
        return f'status: {status}' 
    else:
        config_str = request.form['config']   
        if not log.load_config.load_str(config_str):
            return 'invalid config'
    idle = False
    while not status:
        time.sleep(0.2) 
    return 'success'

 
@app.route('/', methods=['GET','POST'])
def main(): 
    with open(log.relative_path('web.html'), 'r', encoding='utf8') as f:
        template = f.read()
    return render_template_string(template)


app.run(host='0.0.0.0', port = 6801)  


