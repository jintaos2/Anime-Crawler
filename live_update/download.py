from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Union 

import re
import xmlrpc.client
import log
import time

from . import anime


class RuleItem:
    def __init__(
            self, 
            dir: str, 
            title: re.Pattern, 
            epsodes: int, 
            title_must: List[re.Pattern],
            title_score: List[re.Pattern], 
            epsode_filter: re.Pattern,
            order: Optional[int] = None
        ) -> None:

        self.dir = dir 
        self.epsodes = epsodes  
        self.title_must = title_must + [title] 
        self.title_score = title_score 
        self.epsode_filter = epsode_filter
        # {epsode:Anime}
        self.matched: Dict[int, List[anime.Anime]] = {} 
        self.order = order  
        log.error_log.error(f'[new rule] epsodes={(epsodes & ((1<<32)-1)):0>25b} dir={dir}')

    def match(self, item: anime.Anime) -> bool:
        """
        item: [release_time, release_type, release_title, release_magnet,release_size]
        """
        title = item.release_type + item.release_title
        for regex in self.title_must:
            if not regex.search(title):
                return False     # title not match 

        epsode_ = self.epsode_filter.findall(title)
        if len(epsode_) > 0 and re.match(r'\d+', epsode_[-1]):
            epsode = int(epsode_[-1])
            if not self.epsodes & (1<<epsode):
                return False     # epsode not match    
        else:
            log.error_log.info(f"[error filter epsode] {title}")
            return False 
        
        score = 0
        for regex in self.title_score:
            if regex.search(title):
                score += 1  
        if epsode not in self.matched: 
            self.matched[epsode] = [] 
        temp = item.copy()
        temp.score = score
        self.matched[epsode].append(temp) 

    def delete(self, epsode: int):
        self.epsodes &= ~(1<<epsode)



@log.add_task
class match_rule(log.Task):

    rule_items: List[RuleItem]

    def __init__(self):

        self.re_dir_name = re.compile(r'[<>/\\\|:"*? ]')


    def loop_head(self):
        """ load log """
        if 'title_must' not in log.config[0]:
            log.config[0]['title_must'] = ["動畫", "简|CHS|GB|繁|CHT|BIG5"]  
        if 'title_score' not in log.config[0]:
            log.config[0]['title_score'] = ["简|CHS|GB", "1080|2160"]  
        if 'title_epsodes' not in log.config[0]:
            log.config[0]['title_epsodes'] = r'[ \[【第](\d\d)[v\- \]】（集话]'  

        self.title_must = [re.compile(i, re.I) for i in log.config[0]['title_must']] 
        self.title_score = [re.compile(i, re.I) for i in log.config[0]['title_score']]
        self.epsode_filter = re.compile(log.config[0]['title_epsodes'], re.I)

        self.rule_items: List[RuleItem] = []  
        for i in log.config[1:]:
            self.rule_items.append(self._read_log(i))   


    def _read_log(self, item: Dict[str,str]):
        """
        {
            'filters': '忍者一时|Shinobi no Ittoki',
            'epsodes': '1, 2, 3-4, 7+,'
            'order': -1
        }
        """ 
        return RuleItem(
            dir = self._valid_dir_name(item['filters']), 
            title = re.compile(item['filters']),  
            epsodes=self.epsode_str2int(str(item['epsodes'])),
            title_must=self.title_must, 
            title_score=self.title_score, 
            epsode_filter=self.epsode_filter,
            order = item.get('order')
        )
                
    def _valid_dir_name(self, s: str):
        ret = s.split('|')[0] 
        return self.re_dir_name.sub('', ret)


    def epsode_str2int(self,a:str) -> set: # '1-2, 5-6, 9+' -> ...11111111001100110
        ret = 0 
        a = a.split(',')
        for i in a:
            if not i:
                continue
            if i[-1] == '+':        # '7+'
                ret |= ~((1 << int(i[:-1])) - 1)
                continue
            ii = i.split('-') 
            if len(ii) == 1:
                ret |= 1 << int(i) 
            elif len(ii) == 2:
                ii = [int(ii[0]), int(ii[1])+1]
                ret |= ((1 << ii[1]) - 1) & ~((1 << ii[0]) - 1) 
        return ret 
 
    
    def epsode_int2str(self, a: int) -> str:    # 11111111001100110 -> ['1-2', '5-6', '9-16']
        ret = []
        bit_idx = 0
        while 1:
            if a == 0:
                break 
            elif a == -1:
                ret.append(f'{bit_idx}+')
                break 
            elif a & 1:
                start = bit_idx 
                while a & 1: 
                    a >>= 1 
                    bit_idx += 1  
                if start == bit_idx - 1:
                    ret.append(f'{start}')
                else:
                    ret.append(f'{start}-{bit_idx-1}')
            else:
                bit_idx += 1 
                a >>= 1 
        return ','.join(ret) 


    def loop_body(self):
        t = time.time()
        self.matched_items = []
        for source in log.tasks:
            if isinstance(source, anime.AnimeSource):
                for new_item in source.cache.values():
                    for rule in self.rule_items:
                        if rule.match(new_item):
                            break
        log.error_log.error(f'[match_rule cost] {time.time()-t} s')

    def loop_tail(self):
        for idx, rule in enumerate(self.rule_items):
            log.config[idx+1]['epsodes'] = self.epsode_int2str(rule.epsodes)




@log.add_task
class download(log.Task):

    def __init__(self):
        self.aria2_url = None 
        self.aria2_dir = None

    def loop_head(self):
        """ read url, config """  
        self.aria2_url = log.config[0].get('aria2')
        self.aria2_dir = log.config[0].get('download_dir')
        log.error_log.error(f'[downloader config] url={self.aria2_url}, dir={self.aria2_dir}')


    def loop_body(self): 
        t = time.time()
        s = xmlrpc.client.ServerProxy(self.aria2_url)
        for rule in match_rule.rule_items:
            for epsode, animes in rule.matched.items():
                animes = sorted(animes, key=lambda x: x.score)
                try:
                    anime = animes[rule.order]
                except:
                    anime = animes[-1] 
                new_info = f"[epsode={epsode} score={anime.score}] {anime.release_title}"
                try:
                    id_ = s.aria2.addUri([anime.release_magnet],{'dir': f'{self.aria2_dir}/{rule.dir}'}) 
                    aria_status = s.aria2.tellStatus(id_) 
                    log.error_log.info('[download start]', new_info, f"--> {aria_status['dir']}")
                    rule.delete(epsode)
                except Exception as e:
                    log.error_log.info(f"[download error] {new_info}\n  --> port={self.aria2_url}: {e}")
        log.error_log.error(f'[download cost] {time.time()-t} s')
