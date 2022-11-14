import time 
import datetime
import sys
import threading

from flask import Flask, render_template_string, request

import log
import live_update

# debug flag
if len(sys.argv) > 1:
    log.debug = True

# app status
status = 'not start'
idle = False 

def run():
    global status
    counter = 0
    while 1:
        time.sleep(1) 
        counter += 1
        if idle: 
            status = '' 
            counter = 0 
        elif counter == 1: 
            status = 'loop_head' 
            t = time.time()
            for task in log.tasks:
                task.loop_head() 
            status = 'loop_body'
            for task in log.tasks:
                task.loop_body()
            status = 'loop_tail'
            for task in log.tasks:
                task.loop_tail()  
            log.error_log.error(f'[total cost] {time.time()-t} s')
        elif counter > 900:         # loop interval
            counter = 0
        else:
            status = 'waiting' 
 


task = threading.Thread(target=run)
task.daemon = True
task.start()

app = Flask(__name__)

@app.route('/get_log',methods=['GET','POST'])
def get_log(): 
    _log = ''.join(log.error_log.get_history()) 
    _status = status or 'stopped' 
    _config = str(log.load_config)
    return {
        'log' : _log, 
        'status': f'{_status} ━━━━━━━━━━━━━━━━━━━━ {datetime.datetime.now()}', 
        'config': _config,
    }

@app.route('/stop_app',methods=['GET','POST'])
def stop_app(): 
    global idle, status
    idle = True
    while status:
        time.sleep(0.5)
    return 'stopped'

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
        time.sleep(0.5) 
    return 'success'

 
@app.route('/', methods=['GET','POST'])
def main(): 
    with open(log.relative_path('web.html'), 'r', encoding='utf8') as f:
        template = f.read()
    return render_template_string(template)


app.run(host='127.0.0.1', port = 6888)  


