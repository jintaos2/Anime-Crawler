import requests
import re
import datetime
import logs
import os

def nyaa()->list:
    r=requests.get("https://nyaa.si/")
    table = re.findall(r'<tbody>[\s\S]*</tbody>',r.text)[0]    
    rows = re.findall(r'<tr[\s\S]*?</tr>',table) 
    new_items = []
    for i in rows:
        detail = re.findall(r'<td[\s\S]*?</td>',re.sub(r'[\n\t]','',i))  # cols in a row
        release_time = re.sub(r'<.*?>','',detail[4])
        release_type = re.findall(r'title="([^"]*)?"',detail[0])[0]
        release_title = re.findall(r'<a.*?>(.*?)</a>',detail[1])[-1]
        release_magnet = re.findall(r'href="([^"]*)"',detail[2])[-1]
        release_size = re.sub(r'<.*?>','',detail[3])
        new_items.append([release_time, release_type, release_title, release_magnet,release_size])
    return new_items


def dmhy()->list:
    """
    return list([release_time, release_type, release_title, release_magnet,release_size])
    """
    r=requests.get("https://share.dmhy.org/")
    table = re.findall(r'<tbody>[\s\S]*</tbody>',r.text)[0]    
    rows = re.findall(r'<tr[\s\S]*?</tr>',table)                          
    new_items = []
    for i in rows:
        detail = re.findall(r'<td[\s\S]*?</td>',re.sub(r'[\n\t]','',i))  # cols in a row
        release_time = re.findall(r'<span.*?>(.*?)</span>',detail[0])[0]
        release_type = re.sub(r'<.*?>','',detail[1])
        release_title = re.findall(r'<a.*?>(.*?)</a>',detail[2])[-1]
        release_title = re.sub(r',','.',release_title)
        release_magnet = re.findall( r'href="([^"]*)"',detail[3])[-1]
        release_size = re.sub(r'<.*?>','',detail[4])
        new_items.append([release_time, release_type, release_title, release_magnet,release_size])  
    return new_items


class Anime:
    """
    update cache
    return new list
    """
    sources = {'dmhy':dmhy}

    def __init__(self, cache_dir:str):
        self.cache_dir = cache_dir 

    def update(self):
        """
        figure out new_anime
        """
        new_items = []
        for i in self.sources.keys():             # merge result of all sources
            try:
                new_items += self.sources[i]()    # get new page 
            except Exception as e:
                logs.error_logger.info(f"[error update sources] {e}")
                
        self.new_anime = self.update_cache(new_items) # get vaild items
        logs.error_logger.info(f"[new] {len(self.new_anime)} items")

    def update_cache(self, new_items:list)->list:
        """
        input:
            new_items: [release_time, release_type, release_title, release_magnet,release_size]
        output: 
            new_items_vaild
        """
        curr_date = datetime.date.today()
        prev_date = curr_date - datetime.timedelta(days=1)
        # ex. 2021-06-17.txt
        file_curr = f'{self.cache_dir}{curr_date}.txt'
        file_prev = f'{self.cache_dir}{prev_date}.txt'
        odd_list = self.find_record(file_prev) | self.find_record(file_curr)
        new_items_vaild = []
        for i in reversed(new_items):
            if not i[3] in odd_list:
                new_items_vaild.append(i)
        with open(file_curr, 'a+', encoding='utf8') as f:
            for i in new_items_vaild:
                f.write(','.join(i)+'\n\n')    # newline
        return new_items_vaild

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
                logs.error_logger.info(f"[odd cache error]{e}")
        return set()