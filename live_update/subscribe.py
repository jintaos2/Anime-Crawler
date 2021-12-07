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
    def __init__(self, list_file:str, cache_dir:str, aria2_url:str, aria2_dir:str):
        self.list_file = list_file
        self.cache_dir = cache_dir
        self.aria2_url = aria2_url
        self.aria2_dir = aria2_dir
  
        self.items = []    # new items 
        self.rules = []    # new rules

    def download(self):    
        self.read_rules()  # odd rules
        self.read_history(12)  # cached items
        self.n_new = 0    # number of new mached items

        for rule in self.rules:
            curr_rule = Rule(rule)

            if rule["status"] == "dead":  # no need to match
                continue
            results = {}                        # {epsode: [(score, link, dir, title), (score, link, dir, title)]}
            for item in self.items:             # [release_time, release_type, release_title, release_magnet,release_size]
                epsode, score = curr_rule.match(item)
                if epsode == -1:
                    continue
                if not epsode in results:
                    results[epsode] = []
                results[epsode].append((score, item[3], rule["dir"], item[2]))  #  item match!
            for i in results.keys():                        # download per epsode
                results_per_epsode = results[i]
                results_per_epsode.sort(key = lambda x: x[0], reverse=True)
                idx = rule["order"]
                idx = idx if idx < len(results_per_epsode) else -1
                if self.download_item(results_per_epsode[idx]):  # download by order
                    if rule["status"] == "once":    # change status
                        rule["status"] = "dead"
                    elif rule["status"] == "active":
                        curr_rule.delete(i)         # delete downloaded epsode

            curr_rule.store()         # restore epsode

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
            return True
        except Exception as e:
            logs.error_logger.info(traceback.format_exc(limit=1))
            logs.error_logger.info(f"[aria2 error] port={self.aria2_url}, will try again]")
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
        files = [i for i in sorted(os.listdir(self.cache_dir), reverse=True) if len(i)==14][0:days]
        self.items = []
        for file in files:
            with open(self.cache_dir + file, 'r', encoding='utf8') as f:
                lines = [i.split(',') for i in f.readlines()]
                vaild = [i for i in lines if len(i) > 3 and i[3] != '']
                self.items += vaild
        return self.items


class Rule():
    def __init__(self, rules:dict):
        self.rules = rules
        self.title_must = [re.compile(i, re.I) for i in rules["title"]]      # ["进击的巨人|進擊的巨|Shingeki no Kyojin", "動畫"]
        self.title_optional = [re.compile(i, re.I) for i in rules["title_optional"]] # ["简|CHS|GB", "1080"]
        self.epsode_filter = re.compile(rules["epsode_filter"])                      # "[^a-zA-Z0-9](\\d\\d)[^a-zA-Z0-9]"
        self.epsodes = []
        epsodes_ = rules["epsodes"]   # ["01", "02", "03-08"] -> [1,2,3,4,5,6,7,8]
        for i in epsodes_:    
            ii = i.split('-')
            if len(ii) == 1:
                self.epsodes.append(int(i))
            elif len(ii) == 2:
                self.epsodes += list(range(int(ii[0]),int(ii[1])+1))

    def match(self, item: list):
        """
        input:  [release_time, release_type, release_title, release_magnet,release_size]
        output: epsode , score
        """
        title = item[1] + item[2]
        for regex in self.title_must:
            if not regex.search(title):
                return -1, 0     # title not match 

        if self.rules["status"] == "once":  # epsode does not matter 
            epsode = 0
        else:
            epsode_ = self.epsode_filter.findall(title)
            if len(epsode_) > 0 and re.match(r'\d+', epsode_[-1]):
                epsode = int(epsode_[-1])
                if epsode not in self.epsodes:
                    return -1, 0 # epsode not match 
            else:
                return -1, 0     # epsode not match 

        # epsode match
        score = 0
        for regex in self.title_optional:
            if regex.search(title):
                score += 1
        return epsode, score

    def delete(self, epsode:int):
        while epsode in self.epsodes:   # avoid repeat
            self.epsodes.remove(epsode)
                 
    def int2str(self,n):
        return '0{}'.format(n) if n < 10 else '{}'.format(n)

    def store(self):
        self.rules["epsodes"] = [self.int2str(i) for i in self.epsodes]