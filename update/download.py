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
            dir: str,               # download directory name
            title: re.Pattern,      # title filter 
            epsodes: str,           # ex. 0b11111111001100110
            title_must: List[re.Pattern],   # title must contain keyword
            title_score: List[re.Pattern],  # title score keyword
            epsode_filter: re.Pattern,    # epsode filter
            order: int = 0,     
        ) -> None:

        self.dir = dir 
        self.epsodes = self.epsode_str2int(epsodes)
        self.title_must = title_must + [title] 
        self.title_score = title_score 
        self.epsode_filter = epsode_filter
        self.order = order  
        # {epsode:[Anime]}
        self.matched: Dict[int, List[anime.Anime]] = {} 

    def match(self, item: anime.Anime) -> bool:
        """
        item: [release_time, release_type, release_title, release_magnet,release_size]
        """
        title = item.release_type + item.release_title
        for regex in self.title_must:
            if not regex.search(title):
                return False     # title not match 

        epsode_ = self.epsode_filter.findall(title)
        if len(epsode_) > 0 and re.match(r'\d+', epsode_[-1]):  # 选集
            epsode = int(epsode_[-1])
            if not self.epsodes & (1<<epsode):
                return False     # epsode not match    
        else:
            log.log.error(f"[filter] epsode error: {title}")
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
        return True

    def delete(self, epsode: int):
        self.epsodes &= ~(1<<epsode)


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


class match_rule(log.Task):

    def __init__(self):
        super().__init__()


    def loop_head(self):
        # aria2  
        self.aria2_url = log.config[0].get('aria2')
        self.aria2_dir = log.relative_path(log.config[0].get('download_dir'))
        yield self.debug(f'download url={self.aria2_url}, dir={self.aria2_dir}')


    def _read_log(self, item: Dict[str,str]):
        """
        {
            'filters': '忍者一时|Shinobi no Ittoki',
            'epsodes': '1, 2, 3-4, 7+,'
            'title':{
                'epsodes': '(?<=[^\\da-zB-DF-Z])\\d\\d(?=[^\\db])|(?<=第)\\d(?=话)',        # epsode filter
                'must': ['動畫', '简|CHS|GB|繁|CHT|BIG5'],                                  # 标题必须包含的关键字
                'score': ['简|CHS|GB', '1080|2160'],                                       # 标题得分
                'select': 0,                                                              # 每一集的选择顺序
            }
        }
        """  
        title = log.valid_title_filter(item.get('title'))

        title_must: list = title.get('must')
        title_score: list = title.get('score')
        epsode_filter: str = title.get('epsodes')
        title_select: int = title.get('select') 

        return RuleItem(
            dir = self._valid_dir_name(item['filters']), 
            title = re.compile(item['filters']),  
            epsodes=str(item['epsodes']),
            title_must=[re.compile(i, re.I) for i in title_must], 
            title_score=[re.compile(i, re.I) for i in title_score],
            epsode_filter=re.compile(epsode_filter, re.I),
            order = title_select,
        )
                
    def _valid_dir_name(self, s: str) -> str:
        ret = s.split('|')[0]  
        return re.sub(r'[<>/\\\|:"*? ]', '', ret)

    def loop_body(self):
        with log.config_lock:
            # load rules 
            rule_items: List[RuleItem] = []  
            for i in log.config[1:]:
                rule_items.append(self._read_log(i))       # if error, break this stage
            yield self.debug(f'matcher find {len(rule_items)} rules')
        
            total = 0 
            n = 0
            for source in log.tasks:
                if isinstance(source, anime.AnimeSource):
                    for new_item in source.cache.values():
                        total += 1
                        for rule in rule_items:
                            if rule.match(new_item): 
                                n += 1
            yield self.debug(f'matcher match {n} of {total} items')

            s = xmlrpc.client.ServerProxy(self.aria2_url)
            for rule in rule_items:
                for epsode, animes in rule.matched.items():
                    animes = sorted(animes, key=lambda x: x.score, reverse=True)  # score high to low
                    try:
                        target = animes[rule.order]
                    except:
                        target = animes[-1] 
                    new_info = f"epsode={epsode} score={target.score} title={target.release_title}"
                    try:
                        id_ = s.aria2.addUri([target.release_magnet],{'dir': f'{self.aria2_dir}/{rule.dir}'}) 
                        aria_status = s.aria2.tellStatus(id_) 
                        rule.delete(epsode)
                        yield self.info(f"[✔download] {new_info} --> {aria_status['dir']}")
                    except Exception as e:
                        yield self.info(f"[✘download] {new_info}\n  --> aria={self.aria2_url}: {e}")

            for idx, rule in enumerate(rule_items):
                log.config[idx+1]['epsodes'] = rule.epsode_int2str(rule.epsodes)   



