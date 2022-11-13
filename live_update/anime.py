import requests
import re
import datetime
from . import logs
import os
import time
import traceback
import json

__sources__ = {}
# proxies={'https':'http://localhost:7890'}
proxies=None
n_pages = 3

def nyaa(nth:int)->list:
    url = f"https://nyaa.si/?p={nth}"   # 1, 2, 3 ...
    for n_try in range(3):
        time.sleep(1)
        try:
            raw= requests.get(url, proxies=proxies, timeout=15).text
        except Exception as e:
            raw = ''
            logs.error_logger.info(f"[error] getting {url}! try={n_try} response={raw} error_info={e}")
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
                new_items.append([release_time, release_type, release_title, release_magnet,release_size])  
            except:
                logs.error_logger.info(traceback.format_exc())
                logs.error_logger.info(f"[regex] row: {i}")            
    return new_items
# __sources__['nyaa'] = nyaa


def dmhy(nth:int)->list:
    """
    read nth page
    return list([release_time, release_type, release_title, release_magnet,release_size])
    """
    url = f"https://www.dmhy.org/topics/list/page/{nth}"   # 1, 2, 3 ...
    
    for n_try in range(3):
        time.sleep(1)
        try:
            raw=requests.get(url, proxies=proxies, timeout = 15).text 
        except Exception as e:
            raw = ''
            logs.error_logger.info(f"[error] getting {url}! try={n_try} response={raw} error_info={e}")
        if len(raw) > 20:
            break

    tables = re.findall(r'<tbody>[\s\S]*</tbody>',raw)
    if logs._debug:
        logs.error_logger.info(f"[debug] requests.get {url} n_try={n_try} r.text={raw} items = {len(tables)}")        
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
            new_items.append([release_time, release_type, release_title, release_magnet,release_size])  
        except:
            logs.error_logger.info(traceback.format_exc())
            logs.error_logger.info(f"[regex] row: {i}")
    return new_items
__sources__['dmhy'] = dmhy




def dmhy2(nth:int)->list:
    main_url = 'https://dongmanhuayuan.myheartsite.com/api/acg/search'
    try:
        r = requests.post(main_url, proxies=proxies, data={'page':str(nth)}, timeout=15)
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
        logs.error_logger.info(f"[error] post {main_url}! error_info={e}")
        return []

    def post_item(_id:int, _link:str, title:str="") -> str:
        time.sleep(0.6)
        url = 'https://dongmanhuayuan.myheartsite.com/api/acg/detail'
        data = {'link':_link, 'id':_id}
        for i in range(6):
            try:
                r = requests.post(url, proxies=proxies, data=data, timeout=15) 
                r = str(r.content, encoding='utf8')
                r = json.loads(r)
                r = r['data']['magnetLink1']    
                assert r[:8] == 'magnet:?'
                return r 
            except:
                if logs._debug:
                    logs.error_logger.info(f"[error post n_try={i}] url={url}, \ndata={data}, \ntitle={release_title}\n{traceback.format_exc(1)}")
                else:
                    logs.error_logger.info(f"[error post n_try={i}] {release_title}")
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
        new_items.append([release_time, release_type, release_title, release_magnet,release_size])
    return new_items
# __sources__['dmhy2'] = dmhy2



################################################################################################
################################################################################################
################################################################################################


class Anime:
    """
    update cache
    return new list
    """
    def __init__(self, cache_dir:str):
        self.cache_dir = cache_dir 
        for i in __sources__.keys():
            source_dir = self.cache_dir + i + '/'
            logs.error_logger.info(f"[init] add cache_dir {source_dir}")
            if not os.path.isdir(source_dir):
                os.makedirs(source_dir)


    def update_source(self, name:str) -> int:
        # ex. ./log/cache/dmhy/
        cache = self.cache_dir + name + '/'
        curr_date = datetime.date.today()
        prev_date = curr_date - datetime.timedelta(days=1)        
        # ex. 2021-06-17.txt
        file_curr = f'{cache}{curr_date}.txt'
        file_prev = f'{cache}{prev_date}.txt'
        odd_items: set = self.find_record(file_prev) | self.find_record(file_curr)
        
        new_items: list = []
        for i in range(n_pages if not os.path.isfile(file_prev) else 1):
            try:
                new_page: list = __sources__[name](i+1)
            except:
                logs.error_logger.info(traceback.format_exc())
                new_page = []
            new_items += new_page
            time.sleep(1) 
            
        valid_items: list = []
        for i in reversed(new_items):
            i[2] = re.sub(r'\n|,', '', i[2])    # replace ',' and '\n' in title
            magnet = i[3]
            if magnet[:8] == 'magnet:?' and i[3] not in odd_items:      # check whether items are cached 
                valid_items.append(i)
        with open(file_curr, 'a+', encoding='utf8') as f:
            for i in valid_items:
                f.write(','.join(i)+'\n\n')     # update cache
                
        if logs._debug:
            self.new_items = new_items 
            self.valid_items = valid_items
        return len(valid_items)                 # how many valid new items
        
        
    def update(self) -> None:
        for name in __sources__.keys():
            n = self.update_source(name)
            logs.error_logger.info(f"[new] {name} cached {n} items")        

    def find_record(self, file_curr:str)->set:
        """
        input: 
            file name 
        output:
            a set of magnet links
        cache: 
            [release_time, release_type, release_title, release_magnet,release_size]
        """
        if os.path.isfile(file_curr):
            try:  # magnet links exists
                f = open(file_curr,'r',encoding='utf8')
                lines = [i.split(',') for i in f.readlines()]
                f.close()
                
                valid = set()
                for i in lines:
                    if len(i) < 4: continue
                    magnet = i[3]
                    if magnet[:8] == 'magnet:?':
                        valid.add(magnet)     
                return valid
            
            except Exception as e:
                logs.error_logger.info(f"[read odd cache {file_curr} error]{e}")
        return set()