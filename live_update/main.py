import time 
import datetime
import os
import re
import animate
import subscribe


if __name__ == "__main__":
    time.sleep(5)
    config = {}
    config_necessary = ['subscribe_log', 'download_dir', 'aria2_server']
    with open('config.txt', 'r',encoding='utf8') as f:
        for i in f.readlines():
            config_items = re.findall(r'\s*(\w*)\s*=\s*(.*)', re.sub(r'[\n\t]','',i))
            if len(config_items) > 0 and len(config_items[0]) > 1:
                config[config_items[0][0]] = re.findall(r"'(.*?)'",config_items[0][1])[0]
    for i in config_necessary:
        if not i in config.keys(): 
            print('[error] ./config.txt')
            os._exit(1)
        
    subscribe_log = config['subscribe_log']
    download_dir = config['download_dir']
    aria2_server = config['aria2_server']
    if not os.path.exists(subscribe_log) or not os.path.exists(download_dir):
        print('[error] path does not exist')
        os._exit(1)
    downloader = subscribe.subscribe(subscribe_log, download_dir, aria2_server)
    
    while True:
        source_list = [animate.dmhy]
        time_curr = '{}'.format(datetime.datetime.today())[:-7]
        new_items = []
        for updater in source_list:
            try:
                new_items = updater()  # update local cache of records 
                downloader.update_message(new_items)  # write title of subscribed items into log file 
                downloader.download()  # download items match rules, write log file, update rules
            except Exception as e:
                with open("log.txt",'a+', encoding='utf8') as f:
                    f.write("{} [error] {} update error! {}\n".format(time_curr, updater.__name__, e))             
            else:
                with open("log.txt",'a+', encoding='utf8') as f:
                    f.write("{} [update] {} update {} items.\n".format(time_curr, updater.__name__, len(new_items)))    
        time.sleep(720)