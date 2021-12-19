import re
import os
import xmlrpc.client
import json
import logs
import traceback

class Subscribe:
    """rules
    [{
        "dir": "平稳世代的韦驮天们",
        "title": [ "平稳世代的韦驮天们|Heion Sedai no Idaten", "動畫" ],
        "title_optional": [ "简|CHS|GB", "简|CHS|GB|繁|CHT|BIG5", "1080|2160" ],
        "epsode_filter": "[^a-zA-Z0-9](\\d\\d)[^a-zA-Z0-9]",
        "order": 0,
        "status": "active",
        "epsodes": [ "12", "13" ]
    }]
    """
    def __init__(self, list_file:str, cache_dir:str, sources:list, aria2_url:str, aria2_dir:str):
        self.list_file = list_file  # './log/mylist.json'
        self.cache_dir = cache_dir  # './log/cache/'
        self.sources = sources      # ['dmhy','dmhy2']
        self.aria2_url = aria2_url  # "http://127.0.0.1:6800/rpc"
        self.aria2_dir = aria2_dir  # "E:/anime"
  
        self.items = []    # new items 
        self.rules = []    # new rules

    def download(self):    
        self.read_rules()  # odd rules
        self.read_history(10)  # cached items
        self.n_new = 0    # number of new mached items

        for rule in self.rules:
            curr_rule = Rule(rule)

            results = {}                        # {epsode: [(score, link, dir, title), (score, link, dir, title)]}
            for item in self.items:             # [release_time, release_type, release_title, release_magnet,release_size]
                epsode, score = curr_rule.match(item)
                if epsode == -1: continue
                if epsode not in results: results[epsode] = []
                results[epsode].append((score, item[3], rule["dir"], item[2]))  #  item match!
            for epsode, results_per_epsode in results.items():         # download per epsode
                results_per_epsode.sort(key = lambda x: x[0], reverse=True)
                idx = rule["order"]
                idx = idx if idx < len(results_per_epsode) else -1
                if self.download_item(results_per_epsode[idx]):     # download by order
                    curr_rule.delete(epsode)                        # delete downloaded epsode
                    
            curr_rule.store()                   # restore epsode

        logs.error_logger.info(f"[new] {self.n_new} items match the rule")
        if self.n_new > 0:
            logs.update_logger.info("----------------------------")
        self.write_rules()
                 

    # (score, link, dir, title)
    def download_item(self,item):
        self.n_new += 1
        _, link, subdir, title = item
        logs.update_logger.info(f"[new] {title}")
        try:
            s = xmlrpc.client.ServerProxy(self.aria2_url)
            id_ = s.aria2.addUri([link],{'dir': self.aria2_dir + subdir})
            aria_status = s.aria2.tellStatus(id_)
            logs.update_logger.info(f"[download] {title} dir:{aria_status['dir']}")
            logs.error_logger.info(f"[download] {title} dir:{aria_status['dir']}")
            return True
        except Exception as e:
            logs.error_logger.info(f"[aria2 error] port={self.aria2_url}, will try again]")
            logs.error_logger.info(traceback.format_exc(limit=1))
            return False

    def read_rules(self):
        try:
            with open(self.list_file, 'r', encoding='utf8') as f:
                self.rules = json.load(f)
        except Exception as e:
            logs.error_logger.info(f"[error] read_rules: {e}")   
    def write_rules(self):
        try:
            with open(self.list_file, 'w+', encoding='utf8') as f:
                json.dump(self.rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logs.error_logger.info(f"[error] write_rules: {e}") 
    def read_history(self, days:int):
        filepaths: list = []
        for name in self.sources:
            cache = self.cache_dir + name + '/'
            filepaths += [cache+i for i in sorted(os.listdir(cache), reverse=True) if len(i)==14][0:days]
        self.items = []
        for filepath in filepaths:
            valid = []
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [i.split(',') for i in f.readlines() if i != '\n']
                for i in lines:
                    if len(i) < 4: continue
                    if len(i) > 5: logs.error_logger.info(f'[read cache] unexpected items: {i}')
                    magnet = i[3]
                    if magnet[:8] == 'magnet:?': valid.append(i)
            self.items += valid
        return self.items


class Rule():
    def __init__(self, rules:dict):
        self.rules = rules
        
        self.title_must = [re.compile(i, re.I) for i in rules["title"]]                 # ["进击的巨人|進擊的巨|Shingeki no Kyojin", "動畫"]
        
        if "title_optional" not in rules:
            self.title_optional = [ "简|CHS|GB", "1080|2160"]
        else:
            self.title_optional = rules["title_optional"]
        self.title_optional = [re.compile(i, re.I) for i in self.title_optional]        
        
        self.epsode_filter = re.compile(r'[^a-zA-Z0-9](\d\d)[^a-zA-Z0-9]')              # "[^a-zA-Z0-9](\\d\\d)[^a-zA-Z0-9]"
        self.epsodes:set = self.epsode_str2int(rules["epsodes"] )

                
    def epsode_str2int(self,a:list) -> set: # ["01", "02", "003-08"] -> [1,2,3,4,5,6,7,8]
        ret: list = []
        for i in a:    
            ii = i.split('-')
            if len(ii) == 1:
                ret.append(int(i))
            elif len(ii) == 2:
                ret += list(range(int(ii[0]),int(ii[1])+1))
        return set(ret)        
    
    def epsode_int2str(self,a:set) -> list:    # {1,2,3,5,6,7,8} -> ["01-03", "05-08"]
        
        def subset(a:list) -> str:
            '''pop int from a, reuturn str 
            '''
            start = a.pop()
            end = start 
            while end + 1 in a:
                end = a.pop()
            if start == end:
                return str(end)
            else:
                return str(start) + '-' + str(end)
        ret = []
        a = list(a)
        a.sort(reverse=True)
        while a:
            ret.append(subset(a))
        return ret

    def match(self, item: list):
        """
        input:  [release_time, release_type, release_title, release_magnet,release_size]
        output: 
            epsode: -1 means no match 
            score
        """
        title = item[1] + item[2]
        for regex in self.title_must:
            if not regex.search(title):
                return -1, 0     # title not match 
        epsode_ = self.epsode_filter.findall(title)
        if len(epsode_) > 0 and re.match(r'\d+', epsode_[-1]):
            epsode = int(epsode_[-1])
            if epsode not in self.epsodes:
                return -1, 0     # epsode not match    
        else:
            logs.error_logger.info(f"[error filter epsode] {title}")
            return -1, 0     
        
        score = 0
        for regex in self.title_optional:
            if regex.search(title):
                score += 1
        return epsode, score

    def delete(self, epsode:int):
        self.epsodes.remove(epsode)

    def store(self):
        self.rules["epsodes"] = self.epsode_int2str(self.epsodes)