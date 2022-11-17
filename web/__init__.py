import time 
import psutil 
import datetime
import threading

from flask import Flask, render_template_string, request

import log 


app = Flask(__name__)

@app.route('/get_log',methods=['GET','POST'])
def get_log(): 
    return {
        'log'   : log.get_log_lines(), 
        'status': log.get_status(), 
        'config': log.get_config(),
    }

@app.route('/stop_app',methods=['GET','POST'])
def stop_app(): 
    log.idle = True 
    for _ in range(10):
        if log.status:
            time.sleep(0.2) 
        else:
            return 'stopped'
    return 'cannot stop'

@app.route('/set_config',methods=['GET','POST'])
def set_config(): 
    if log.status: 
        return f'status: {log.status}' 
    s = request.form['config']   
    if not log.set_config(s):
        return 'invalid config'
    log.idle = False
    return 'success'
 
@app.route('/', methods=['GET','POST'])
def main(): 
    with open(log.relative_path('web.html'), 'r', encoding='utf8') as f:
        template = f.read()
    return render_template_string(template)


t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=log.flask_port, debug=False, use_reloader=False))
t.daemon = True
t.start()

