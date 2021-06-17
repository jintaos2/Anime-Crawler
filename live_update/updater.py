from subscribe import Subscribe
import time 
import os
import re
import json 
import logs 
from anime import Anime
from subscribe import Subscribe

# output:  c:/a/b/
def path_format(a:str):
    ret = re.sub(r'\\|/', r'/', a)
    if ret[-1] != '/':
        ret += '/'
    return ret

class Updater:
    def __init__(self):
        self.load_config() 
        self.anime = Anime(self.cache_dir)
        self.downloader = Subscribe(self.list_path, self.cache_dir, self.aria2_url, self.aria2_dir)

    def load_config(self):
        self.main_dir = os.path.abspath(os.path.dirname(__file__))
        try: 
            with open(os.path.join(self.main_dir,"config.json"), 'r',  encoding='utf8') as f:
                config = json.load(f)

            self.log_dir = path_format(config["log_dir"])
            if not os.path.isdir(self.log_dir):
                raise Exception("log dir not exist!") 

            # aria2 parameter
            self.aria2_dir = path_format(config["download_dir"])
            self.aria2_url = config["aria2"]

            # two log files
            self.error_log = self.log_dir + "error.log"
            self.update_log = self.log_dir + "update.log"
            logs._init(self.error_log, self.update_log)

            # list file path
            self.list_path = self.log_dir + "mylist.json"
            if not os.path.isfile(self.list_path):
                raise Exception("list.json not exist!")

            # cache dir path: ./log/cache/
            self.cache_dir = self.log_dir + "cache/"
            if not os.path.isdir(self.cache_dir):
                os.makedirs(self.cache_dir)

        except Exception as e:
            print("[error] init: {}".format(e))
            os._exit(1)

    def update(self):
        self.anime.update()

    def download(self):
        self.downloader.download() 