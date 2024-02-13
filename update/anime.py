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


class AnimeSource(log.AnimeBase):
    def __init__(self):
        super().__init__()
        self.cache_dir = log.relative_path(f'../log/cache/{self.__class__.__name__}') 
        self.url: str = ''
        self.proxies = None
        self.pages: int = 0  
        self.stop: bool = False
        # release_magnet: [release_time, release_type, release_title, release_magnet,release_size]
        self.cache: Dict[str, Anime] = {} 
        self.cache_new: List[Anime] = []

    def loop_head(self): 
        # get url, page
        sources: List[Dict] = log.config[0]['sources'] 
        try: 
            self.url, self.pages = sources.get(self.__class__.__name__)
        except:
            yield self.info(f'cannot get config.sources.{self.__class__.__name__}')   
        yield self.debug(f'anime source {self.__class__.__name__} url={self.url}, pages={self.pages}')
        # get proxies
        if log.config[0].get('proxies_en'):
            self.proxies = {'https': log.config[0].get('proxies_url')} 
        else:
            self.proxies = None
        yield self.debug(f'proxies={self.proxies}')

        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)  
        yield from self._reduce_cache()
        yield self.debug(f'cache size={len(self.cache)}')


    def loop_body(self):
        self.stop = False
        new_items: Dict[str, Anime] = {} 
        self.pages = max(self.pages, 0)
        if self.pages > 0:
            curr_date = datetime.date.today() 
            file_curr = f'{self.cache_dir}/{curr_date}.txt'  
            for n in range(self.pages): 
                if self.stop:
                    break
                self.cache_new = []
                yield from self.update_source(n+1)
                for item in self.cache_new:
                    # new to odd 
                    magnet = item.release_magnet
                    if magnet not in self.cache:
                        new_items[magnet] = item 
                    else:
                        self.stop = True 
                        break 

            with open(file_curr, 'a+', encoding='utf8') as f:
                for _, i in reversed(new_items.items()):        # odd to new
                    self.cache[i.release_magnet] = i            # update cache
                    f.write(str(i))                             # update cache file 
                    f.write('\n\n') 

        yield self.debug(f'anime source {self.__class__.__name__} read max {self.pages} pages, get {len(new_items)} new items')


    def update_source(self, nth: int)-> None:
        yield


    def _reduce_cache(self): 
        """ if cache too small, read cache; if too big, reduce """
        n = log.config[0]['max_cache_items']
        if len(self.cache) < n:
            yield from self._read_cache(n)
        elif len(self.cache) > n * 1.5:  
            x = len(self.cache) - n - 2
            temp = {k:v for i, (k, v) in enumerate(self.cache.items()) if i > x}
            self.cache = temp
        yield

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
                yield self.debug(f"read odd cache {file} error: {e}") 
        # odd to new
        for d in reversed(dicts):
            self.cache.update(d)  
        yield self.debug(f'anime source {self.__class__.__name__} read {len(self.cache)} items from cache')

    def __iter__(self):
        return iter(self.cache.values()) 



class dmhy(AnimeSource):

    def update_source(self, nth: int)-> None:
        url = self.url.format(nth)
        for n_try in range(3):
            try:
                raw=requests.get(url, proxies=self.proxies, timeout = 6).text 
            except Exception as e:
                raw = ''
                yield self.debug(f"[loop_body] dmhy try={n_try} getting {url} error: {e}")
                yield self.sleep(n_try*2+2)
            if len(raw) > 20:
                break

        tables = re.findall(r'<tbody>[\s\S]*</tbody>',raw)
        yield self.debug(f'dmhy page={nth} last_try={n_try} requests.get {url} r.text={len(raw)} tables={len(tables)}')   

        if len(tables) == 0:
            self.stop = True 
            yield self.info(f'early stop {self.__class__.__name__} {url}')
            return 
            
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
                assert release_magnet[0:6] == 'magnet', f'{release_magnet}'
                release_size = re.sub(r'<.*?>','',detail[4])
                new_items.append(Anime(release_time, release_type, release_title, release_magnet,release_size))  
            except:
                yield self.info('parse dmhy table error: '+ traceback.format_exc()) 
        yield self.debug(f'dmhy page={nth} try={n_try} get items number={len(new_items)}')
        self.cache_new = new_items



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
            yield self.debug(f"[error] post {main_url}! error_info={e}")
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
                    yield self.debug(f"[error post n_try={i}] url={url}, \ndata={data}, \ntitle={title}\n{traceback.format_exc(1)}")
                    yield self.debug(f"[error post n_try={i}] {title}")
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
        self.cache_new = new_items
        yield 




class nyaa(AnimeSource):

    def update_source(self, nth: int) -> List[Anime]:
        url = self.url.format(nth) 

        for n_try in range(3):
            try:
                raw= requests.get(url, proxies=self.proxies, timeout=15).text
            except Exception as e:
                raw = ''
                yield self.debug(f"[error] getting {url}! try={n_try} response={raw} error_info={e}")
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
                    yield self.debug(traceback.format_exc())
                    yield self.debug(f"[regex] row: {i}")            
        self.cache_new = new_items 
        yield   

