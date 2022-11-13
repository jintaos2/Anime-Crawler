import threading
import time 
import datetime

from flask import Flask, render_template_string, request

log = ['start\n'] 
config = 'hhhhhh'
status = 'running'
wait = False 

def run():
    global status, config, log
    while 1:
        if wait:
            status = 'waiting' 
            time.sleep(1)
            continue 
        status = 'running' 
        log.append(f'config:{config}, time:{datetime.datetime.now()}\n')
        time.sleep(1) 


task = threading.Thread(target=run)
task.daemon = True
task.start()

app = Flask(__name__)

# 定义接口把处理日志并返回到前端
@app.route('/get_log',methods=['GET','POST'])
def get_log():
    _log = ''.join(log) 
    print(_log)
    return {
        'log' : _log, 
        'status': status, 
        'config': config,
    }

@app.route('/stop_app',methods=['GET','POST'])
def stop_app():
    return 'stopped'

@app.route('/set_config',methods=['GET','POST'])
def set_config():
    global config
    print(request.form) 
    config = request.form['config']  
    return 'success\nhhh'

with open('web.html', 'r', encoding='utf8') as f:
    template = f.read()
 
@app.route('/', methods=['GET','POST'])
def main(): 
    print('call main')
    return render_template_string(template)


app.run(host='127.0.0.1', port = 6888, debug=True) 

