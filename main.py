from __future__ import annotations
from typing import List, Dict, Callable, Literal, Generator, Optional
import time 
import os
import sys 
import subprocess 
import xmlrpc.client
import traceback
import datetime
import threading
import psutil
import yaml
import re
import gradio as gr 


# def greet(name):
#     return "Hello " + name + "!!"

# with gr.Blocks() as demo:
#     name = gr.Textbox(label="Name")
#     output = gr.Textbox(label="Output Box")
#     greet_btn = gr.Button("Greet")
#     greet_btn.click(fn=greet, inputs=name, outputs=output, api_name="greet")
    
#     with gr.Blocks() as sub:
#         name = gr.Textbox(label="height")
#         output = gr.Textbox(label="Output Box") 
#         greet_btn = gr.Button("Greet")
#         greet_btn.click(fn=greet, inputs=name, outputs=output)

# demo.launch(inbrowser=True, debug=True)


# sys.exit(0)

import log 
import update


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
         if self.p is not None:
            self.p.kill()
            yield self.info('aria2 killed')

# third task
log.tasks.append(aria2())
log.tasks.append(update.anime.dmhy()) 
log.tasks.append(update.download.match_rule())



def get_status() -> str:
    cpu = psutil.cpu_percent() 
    m = psutil.virtual_memory() 
    m_used = m.used/(1 << 30) 
    m_total = m.total/(1<<30)
    m_app = psutil.Process(os.getpid()).memory_info().rss / 1024 ** 2
    return f"""## {log.os_name}: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ## cpu: {cpu}% mem: {m_app:.2f}MB/{m_used:.2f}GB/{m_total:.2f}GB
    ## status: {log.status}"""

def data2yaml(data)->Optional[str]:
    if data is None:
        return None
    else:
        return yaml.dump(data, allow_unicode = True, sort_keys=False, Dumper=yaml.CDumper)

def yaml2data(yaml_str)->Optional[Dict]:
    if yaml_str is None or yaml_str == '':
        return None
    else:
        return yaml.load(yaml_str, Loader=yaml.CLoader)

# define an app
with gr.Blocks(title='Anime Downloader') as app:
    # gr.HTML('''<h1 style="text-align:center;"> Anime Downloader </h1>''')
    with gr.Tab("status"):
        gr.Markdown(get_status, every=1)
        with gr.Column():
            for task in log.tasks:
                gr.Code(value=task.__str__, label=task.__class__.__name__, every=1, language=None, lines=8) 
            gr.Code(value=log.log.history.__str__, label='log', every=1, language=None, lines=20)
    with gr.Tab("config"): 
        with gr.Row():
            load_btn = gr.Button(value = 'load')
            set_global_btn = gr.Button(value = 'set_global') 
            set_rules_btn = gr.Button(value = 'set_rules') 
            download_btn = gr.Button(value = 'download_now')
        with gr.Row():
            action_info = gr.Textbox(value = '', label='info', interactive=False)
            max_log_lines = gr.Number(value=None, label='max_log_lines', interactive=True)
            max_cache_items = gr.Number(value = None, label='max_cache_items', interactive=True) 
            max_interval = gr.Number(value = None, label='max_interval', interactive=True) 
        with gr.Row():
            download_dir = gr.Textbox(value = None, label='download_dir', interactive=True)
            aria2_url = gr.Textbox(value = None, label='aria2', interactive=True) 
            proxies_en = gr.Checkbox(value = None, label='proxies_en', interactive=True) 
            proxies_url = gr.Textbox(value = None, label='proxies_url', interactive=True) 
        with gr.Row():
            sources = gr.Code(value = None, label = 'sources', language='yaml', interactive=True)
            title = gr.Code(value = None, label='title', language='yaml', interactive=True)  

        rules_button = []
        filters = []
        epsodes = []
        rules_title = []
        for _ in range(100):
            with gr.Row():
                rules_button.append(gr.Button(value = 'delete')) 
                with gr.Column(scale=2):
                    filters.append(gr.Textbox(value = '', label='filters', interactive=True))
                epsodes.append(gr.Textbox(value = '', label='epsodes',  interactive=True))
                rules_title.append(gr.Code(value = None, label='title', language='yaml', interactive=True, lines=1)) 

    with gr.Tab("playground"):
        with gr.Row():
            search_n = gr.Number(value = 10, label='search', interactive=True) 
            search_title = gr.Textbox(value = None, label='title_filter', interactive=True) 
            search_epsodes = gr.Code(value = log.config[0]['title'].get('epsodes'), label='epsode_filter', interactive=True)
        results = gr.Code(value = None, language=None, interactive=False)   
        
        def search_cache(_number, _titile, _epsode) -> str:
            n = max(10, int(_number))
            ret = []
            if _titile:
                title_re = re.compile(_titile)
            else:
                title_re = re.compile('.*')
            if _epsode:
                epsode_re = re.compile(_epsode, re.I) 
            else:
                return ''
            for task in log.tasks:
                if isinstance(task, update.anime.AnimeSource): 
                    ret.append(f'{task.__class__.__name__}:') 
                    count = 0
                    for i in reversed(task.cache.values()):
                        if title_re.search(i.release_title):
                            ret.append(f'{epsode_re.findall(i.release_title)}, {i}')  
                            count += 1 
                        if count >= n:
                            break 
            return '\n'.join(ret)

        search_n.change(fn=search_cache, inputs=[search_n, search_title, search_epsodes], outputs=results)

    # load all config
    def load_config(): 
        ret = [
            log.config[0].get('max_log_lines'), log.config[0].get('max_cache_items'), log.config[0].get('max_interval'), 
            log.config[0].get('download_dir'), log.config[0].get('aria2'), 
            log.config[0].get('proxies_en'), log.config[0].get('proxies_url'), 
            data2yaml(log.config[0].get('sources')),
            data2yaml(log.config[0].get('title')),
        ]  
        rules: List[Dict]  = log.config[1:len(filters)+1] 
        while len(rules) < len(filters):
            rules.append({})

        for rule in rules:
            ret.append(rule.get('filters'))
            ret.append(rule.get('epsodes'))
            ret.append(data2yaml(rule.get('title')))

        ret.append('config loaded')
        return ret

    load_btn.click(fn=load_config, inputs = None, outputs=[
        max_log_lines, max_cache_items, max_interval, 
        download_dir, aria2_url, proxies_en, proxies_url, 
        sources, title,
        *(i for _group in zip(filters, epsodes, rules_title) for i in _group),     # flatten list
        action_info,
    ]) 

    # set global config
    def set_global_config(*args):
        if not args[0]:
            return 'empty config' 
        with log.config_lock:
            try:
                if args[0]: log.config[0]['max_log_lines'] = max(10, int(args[0])) 
                if args[1]: log.config[0]['max_cache_items'] = max(10, int(args[1])) 
                if args[2]: log.config[0]['max_interval'] = max(10, int(args[2]))  
                if args[3]: log.config[0]['download_dir'] = str(args[3]) 
                if args[4]: log.config[0]['aria2'] = str(args[4]) 
                if args[5]: log.config[0]['proxies_en'] = bool(args[5]) 
                if args[6]: log.config[0]['proxies_url'] = str(args[6]) 
                if args[7]: log.config[0]['sources'] = yaml2data(args[7]) 
                if args[8]: log.config[0]['title'] = log.valid_title_filter(yaml2data(args[8]))
                return 'global config set'
            except:
                return 'set global config error'

    set_global_btn.click(fn=set_global_config, inputs=[
        max_log_lines, max_cache_items, max_interval,
        download_dir, aria2_url, proxies_en, proxies_url,
        sources, title,
    ],outputs=action_info)

    # set rules 
    def set_rules(*args):
        config_new = []
        for i in range(len(args)//3):
            filter, epsode, title = args[i*3:i*3+3] 
            if filters and epsode:  
                try:
                    rule_new = {
                        'filters': str(filter),
                        'epsodes': str(epsode),
                    }
                    if title:
                        rule_new['title'] = log.valid_title_filter(yaml2data(title))
                    config_new.append(rule_new) 
                except:
                    return 'set rules error'    # return if error 
        if len(config_new) > 0:    
            with log.config_lock:               # update config
                log.config[1:] = config_new 
        return f'set {len(config_new)} rules'
        

    set_rules_btn.click(
        fn=set_rules, 
        inputs=[i for _group in zip(filters, epsodes, rules_title) for i in _group],
        outputs=action_info,
    )

    # delete rule 
    def delete_rule():
        return None, None, None 
    
    for delete_btn, filter, epsode, title in zip(rules_button, filters, epsodes, rules_title):
        delete_btn.click(fn=delete_rule, inputs=None, outputs = [filter, epsode, title])

    # download 
    def download_now():
        log.status = 1  
        return 'download now'
    
    download_btn.click(fn=download_now, inputs=None, outputs=action_info)



app.queue()
app.launch(inbrowser=True, prevent_thread_lock=True)

n_loop = 0
try:
    while 1:                                            # 正常循环  
        log.log.debug(f'--------------------------- loop {n_loop} ---------------------------')
        n_loop += 1
        with log.config_lock:
            for task in log.tasks:
                task.__exec__('head')
        for task in log.tasks:
            task.__exec__('body') 
        for task in log.tasks:
            task.__exec__('tail')
        log.status = - max(int(log.config[0].get('max_interval')), 3)  
        while log.status < 0:                           # 等待
            log.status += 1
            time.sleep(1)
except (KeyboardInterrupt, SystemExit):                 # 终止程序
    log.log.debug(f'keyboard interrupt on {datetime.datetime.now()}')
    for task in log.tasks:
        task.__exec__('exit')
    # FIXME not work 
    # app.close()  
    log.log.debug(f'app closed on {datetime.datetime.now()}')
except:                                                 # 其他异常
    log.log.debug(f'other exception on {datetime.datetime.now()}') 
    log.log.debug(traceback.format_exc())
finally:
    sys.exit(0)



