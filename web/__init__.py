
import traceback

from flask import Flask, render_template_string, request, jsonify

import log 


app = Flask('AnimeDownloader')

@app.route('/', methods=['GET','POST'])
def main(): 
    with open(log.relative_path('web.html'), 'r', encoding='utf8') as f:
        template = f.read()
    return render_template_string(template)


@app.route('/get_config')
def get_config():  
    try:
        r  = {k:v for k,v in log.config[0].items()}
        r['sources'] = log.data2yaml(r['sources'])
        r['title'] = log.data2yaml(r['title']) 
        r['status'] = log.get_status() 
        r['log'] = log.get_log() 
        # items 
        items = []
        for i in log.config[1:]:
            if 'title' not in i:
                items.append(i['filters'] + '\n' + i['epsodes']) 
            else:
                items.append(log.data2yaml(i))
        while len(items) < 40:
            items.append('')
        r['data'] = items
        return jsonify(r)
    except:
        return jsonify({'log': traceback.format_exc()})


@app.route('/toggle_task',methods=['GET', 'POST'])
def toggle_task(): 
    data = request.json 
    if data['status'] == True:      # web running, want to stop (just lock)
        if log.running:
            with log.config_lock:
                log.running = False 
        return jsonify({'status': False})
    else:                           # web stopped, want to run (just unlock)
        if not log.running:
            with log.config_lock:
                log.running = True
        return jsonify({'status': True})


@app.route('/init_task',methods=['GET','POST'])
def init_task(): 
    log.status = 1
    return jsonify({'data':'success'})



@app.route('/set_config',methods=['GET','POST'])
def set_config(): 
    data = request.json 
    try:
        result = '\n'.join(log.update_config(data, web=True))
        return jsonify({'data': result})
    except:
        return jsonify({'data': traceback.format_exc()})

@app.route('/search_cache',methods=['GET','POST'])
def search_cache(): 
    data = request.json 
    try:
        result = log.search_cache(data['search_input'])
        return jsonify({'data':result})
    except:
        return jsonify({'data': traceback.format_exc()})


