from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
import re
import datetime
import os
import time
import traceback
import json
import log 

from dataclasses import dataclass 


_title_sub = re.compile(r'[\n,]')

@dataclass 
class Anime: 
    release_time: str = ''
    release_type: str = ''
    release_title: str = ''
    release_magnet: str = ''
    release_size: str = ''
    score: int = 0 

    def __post_init__(self):
        self.release_title = _title_sub.sub('',self.release_title)

    def __str__(self):
        return ','.join([
            self.release_time, 
            self.release_type, 
            self.release_title, 
            self.release_magnet,
            self.release_size
        ]) 

    @staticmethod 
    def load(s: str) -> Optional[Anime]:
        """ load a line to Anime """
        i = s.split(',')
        if len(i) != 5: 
            return None 
        if i[3][:8] != 'magnet:?':
            return None 
        return Anime(i[0],i[1],i[2],i[3],i[4]) 

    def copy(self):
        """ return a new copy """
        return Anime(**self.__dict__)


class AnimeSource(log.Task):
    def __init__(self):
        self.cache_dir = log.relative_path(f'../log/cache/{self.__class__.__name__}') 
        self.url: str = ''
        self.proxies = None
        self.pages: int = 0  
        # release_magnet: [release_time, release_type, release_title, release_magnet,release_size]
        self.cache: Dict[str, Anime] = {} 
        log.error_log.error(f'[loop_init] anime cache dir: {self.cache_dir}')
        

    def loop_head(self): 
        # get url, page
        if 'sources' not in log.config[0]:
            log.config[0]['sources'] = {} 
        sources: List[Dict] = log.config[0]['sources'] 
        name = self.__class__.__name__ 
        try: 
            self.url, self.pages = sources.get(name)
        except:
            pass   
        # get cache size
        n = log.config[0].get('max_cache_items') 
        if not isinstance(n, int) or n < 10:
            log.config[0]['max_cache_items'] = 10 
            n = 10
        # get proxies
        if log.config[0].get('proxies_en'):
            self.proxies = {'https': log.config[0].get('proxies_url')}
            log.error_log.error(f'[loop_head] proxies: {self.proxies}')
        # active
        if self.pages:
            log.error_log.error(f'[loop_head] anime source active {name}:{self.url}, pages:{self.pages}')
            if not os.path.isdir(self.cache_dir):
                os.makedirs(self.cache_dir)  
            self._reduce_cache()

    def loop_body(self):
        if self.pages:
            curr_date = datetime.date.today() 
            file_curr = f'{self.cache_dir}/{curr_date}.txt'  
            new_items: Dict[str, Anime] = {} 
            stop = False
            for n in range(self.pages):
                try:
                    new_page: List[Anime] = self.update_source(n+1)
                except:
                    log.error_log.error(f'[loop_body] {self.__class__.__name__} error: ', traceback.format_exc())
                    new_page = []
                
                for item in new_page:
                    # new to odd 
                    magnet = item.release_magnet
                    if magnet not in self.cache:
                        new_items[magnet] = item 
                    else:
                        stop = True 
                        break 
                if stop:
                    break

            with open(file_curr, 'a+', encoding='utf8') as f:
                for _, i in reversed(new_items.items()):        # odd to new
                        self.cache[i.release_magnet] = i        # update cache
                        f.write(str(i))                         # update cache file 
                        f.write('\n\n')
            if l:=len(new_items):
                log.error_log.info(f'[loop_body] anime source {self.__class__.__name__} update {l} items, cached {len(self.cache)} items')


    def update_source(self, nth: int) -> list:
        # child class
        pass


    def _reduce_cache(self): 
        """ if cache too small, read cache; if too big, reduce """
        n = log.config[0]['max_cache_items']
        if len(self.cache) < n:
            self._read_cache(n)
        elif len(self.cache) > n * 2:  
            x = len(self.cache) - n - 2
            new_cache = {k:v for i, (k, v) in enumerate(self.cache.items()) if i > x}
            self.cache = new_cache

    def _read_cache(self, n: int): 
        """ read n items from file """
        dicts = [] 
        count = 0
        # new to odd
        for file in sorted(os.listdir(self.cache_dir), reverse=True): 
            if count >= n:
                break
            try:
                with open(f'{self.cache_dir}/{file}', 'r', encoding='utf8') as f:
                    lines = f.readlines()
                new_items = {}
                for i in lines: 
                    if item:=Anime.load(i):
                        new_items[item.release_magnet] = item
                dicts.append(new_items)
                count += len(new_items) 
            except Exception as e:
                log.error_log.error(f"[loop_head] read odd cache {file} error: {e}") 
        # odd to new
        for d in reversed(dicts):
            self.cache.update(d)  
        log.error_log.error(f'[loop_head] anime source {self.__class__.__name__} read {len(self.cache)} items from cache')

    def __iter__(self):
        return iter(self.cache.values()) 

    def __str__(self) -> str:
        return f"AnimeSource: {self.__class__.__name__}, url={self.url}, pages={self.pages}, cached items={len(self.cache)}"


@log.add_task 
class nyaa(AnimeSource):

    def update_source(self, nth: int) -> List[Anime]:
        url = self.url.format(nth) 

        for n_try in range(3):
            try:
                raw= requests.get(url, proxies=self.proxies, timeout=15).text
            except Exception as e:
                raw = ''
                log.error_log.error(f"[error] getting {url}! try={n_try} response={raw} error_info={e}")
                time.sleep(1)
            if len(raw) > 20:
                break
        tables = re.findall(r'<tbody>[\s\S]*</tbody>',raw)
        if len(tables) == 0:
            return []
        table = tables[0]    
        rows = re.findall(r'<tr[\s\S]*?</tr>',table)   
        new_items = []
        for i in rows:
            if 'Anime - Non' in i and re.search(r"简|CHS|GB|繁|CHT|BIG5", i):
                try:
                    detail = re.findall(r'<td[\s\S]*?</td>',re.sub(r'[\n\t]','',i))  # cols in a row
                    release_type = re.findall(r'alt="(.*?)"', detail[0])[-1]
                    release_title = re.findall(r'<a.*?>(.*?)</a>', detail[1])[-1]
                    release_magnet = re.findall( r'href="([^"]*)"',detail[2])[-1]
                    release_size = re.findall(r'>(.*?)<',detail[3])[-1]
                    release_time = re.findall(r'>(.*?)<',detail[4])[-1]
                    new_items.append(Anime(release_time, release_type, release_title, release_magnet,release_size))  
                except:
                    log.error_log.error(traceback.format_exc())
                    log.error_log.error(f"[regex] row: {i}")            
        return new_items




@log.add_task 
class dmhy(AnimeSource):

    def update_source(self, nth: int) -> List[Anime]:
        url = self.url.format(nth)
        for n_try in range(3):
            try:
                raw=requests.get(url, proxies=self.proxies, timeout = 6).text 
            except Exception as e:
                raw = ''
                log.error_log.error(f"[loop_body] dmhy try={n_try} getting {url} error: {e}")
                time.sleep(n_try*2+2)
            if len(raw) > 20:
                break

        tables = re.findall(r'<tbody>[\s\S]*</tbody>',raw)
        log.error_log.error(f"[loop_body] dmhy page={nth} try={n_try} requests.get {url} r.text={len(raw)} tables={len(tables)}")        
        if len(tables) == 0:
            return []
            
        table = tables[0]    
        rows = re.findall(r'<tr[\s\S]*?</tr>',table)                          
        new_items = []
        for i in rows:
            try:
                detail = re.findall(r'<td[\s\S]*?</td>',re.sub(r'[\n\t]','',i))  # cols in a row
                release_time = re.findall(r'<span.*?>(.*?)</span>',detail[0])[0]
                release_type = re.sub(r'<.*?>','',detail[1])
                release_title = re.findall(r'<a.*?>(.*?)</a>',detail[2])[-1]
                release_title = re.sub(r',','.',release_title)
                release_magnet = re.findall( r'href="([^"]*)"',detail[3])[0]
                assert release_magnet[0:6] == 'magnet'
                release_size = re.sub(r'<.*?>','',detail[4])
                new_items.append(Anime(release_time, release_type, release_title, release_magnet,release_size))  
            except:
                log.error_log.info('parse dmhy table error', traceback.format_exc()) 
        log.error_log.error(f"[loop_body] dmhy page={nth} try={n_try} get items number={len(new_items)}")
        return new_items



@log.add_task 
class dmhy2(AnimeSource):

    def update_source(self, nth: int) -> List[Anime]:
        main_url = self.url
        try:
            r = requests.post(main_url, proxies=self.proxies, data={'page':str(nth)}, timeout=15)
            r = json.loads(str(r.content, encoding='utf8'))
            r:list = r['data']['searchData']
            """ 
            {'id': 3108564,
            'date': '2021/12/07 14:12',
            'type': '動畫',
            'group': '喵萌奶茶屋',
            'title': '【喵萌奶茶屋】★09月新番★[加油吧同期酱/Ganbare Douki-chan][12END][1080p][简体][招募翻译校对]',
            'link': '/topics/view/587385_09_Ganbare_Douki-chan_12END_1080p.html',
            'size': '42.3MB',
            'finishNum': '-'}
            """
        except Exception as e:
            log.error_log.error(f"[error] post {main_url}! error_info={e}")
            return []

        def post_item(_id:int, _link:str, title:str="") -> str:
            time.sleep(0.6)
            url = 'https://dongmanhuayuan.myheartsite.com/api/acg/detail'
            data = {'link':_link, 'id':_id}
            for i in range(6):
                try:
                    r = requests.post(url, proxies=self.proxies, data=data, timeout=15) 
                    r = str(r.content, encoding='utf8')
                    r = json.loads(r)
                    r = r['data']['magnetLink1']    
                    assert r[:8] == 'magnet:?'
                    return r 
                except:
                    log.error_log.error(f"[error post n_try={i}] url={url}, \ndata={data}, \ntitle={title}\n{traceback.format_exc(1)}")
                    log.error_log.error(f"[error post n_try={i}] {title}")
                    time.sleep(i*2+2.5)
            return None
                
        new_items = []
        for items_raw in r:
            release_time = items_raw['date']
            release_type = items_raw['type']
            release_title = items_raw['title']
            release_size = items_raw['size']
            _id = items_raw['id']
            _link = items_raw['link']
            release_magnet = post_item(_id, _link, release_title)
            if release_magnet is None: continue 
            new_items.append(Anime(release_time, release_type, release_title, release_magnet,release_size))
        return new_items

