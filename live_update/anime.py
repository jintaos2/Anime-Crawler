import requests
import re
import datetime
import logs
import os
import time
import traceback

def dmhy(nth:int)->list:
    """
    read nth page
    return list([release_time, release_type, release_title, release_magnet,release_size])
    """
    url = f"https://dmhy.org/topics/list/page/{nth}"   # 1, 2, 3 ...
    
    
    for n_try in range(3):
        time.sleep(2)
        try:
            raw=requests.get(url, timeout = 15).text 
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


def get_new_items(n:int)->list:
    """
    read latest n pages of multiple sources
    return:
        [release_time, release_type, release_title, release_magnet,release_size]
    """
    new_items = []
    for i in range(n):
        new_items += dmhy(i+1)
        time.sleep(2)
    return new_items


################################################################################################


class Anime:
    """
    update cache
    return new list
    """
    def __init__(self, cache_dir:str):
        self.cache_dir = cache_dir 

    def update(self) -> None:
        """
        new_items: [release_time, release_type, release_title, release_magnet,release_size]
        """
        curr_date = datetime.date.today()
        prev_date = curr_date - datetime.timedelta(days=1)
        # ex. 2021-06-17.txt
        file_curr = f'{self.cache_dir}{curr_date}.txt'
        file_prev = f'{self.cache_dir}{prev_date}.txt'
        odd_list = self.find_record(file_prev) | self.find_record(file_curr)

        n_pages:int = 8 if not os.path.isfile(file_prev) else 1
        new_items = []
        try:
            new_items = get_new_items(n_pages)    # read n pages
            with open(file_prev, 'a+', encoding='utf8') as f: pass       # make an empty file
        except Exception as e:
            logs.error_logger.info(traceback.format_exc())

        new_items_vaild = []
        for i in reversed(new_items):
            if not i[3] in odd_list:       # check whether items are cached 
                new_items_vaild.append(i)
        with open(file_curr, 'a+', encoding='utf8') as f:
            for i in new_items_vaild:
                f.write(','.join(i)+'\n\n')    # update cache

        self.new_anime = new_items_vaild       # how many valid new items
        logs.error_logger.info(f"[new] cache {len(self.new_anime)} items")

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
                with open(file_curr,'r',encoding='utf8') as f:
                    lines = [i.split(',') for i in f.readlines()]
                    vaild = [i[3] for i in lines if len(i) > 3 and i[3] != '']
                    return set(vaild)
            except Exception as e:
                logs.error_logger.info(f"[read odd cache {file_curr} error]{e}")
        return set()