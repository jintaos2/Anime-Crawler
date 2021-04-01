import requests
import re
import datetime

# update list from nyaa main page
def nyaa():
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
    return update_list('nyaa', new_items)

# update list from dmhy main page
def dmhy():
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
    return update_list('dmhy', new_items)


# if the list of new records will be cut off at the position where 3 duplicated records appears in history records
# then write new records in dmhy/[localtime].txt
def update_list(source, new_items):
    curr_date = datetime.date.today()
    file_curr = '{}/{}.txt'.format(source, curr_date)
    file_prev = '{}/{}.txt'.format(source, curr_date - datetime.timedelta(days=1))
    recent_records = set()
    find_record(file_curr,recent_records)
    find_record(file_prev,recent_records)
    for i in reversed(new_items):
        if i[3] in recent_records:
            new_items.remove(i)
    with open(file_curr, 'a+', encoding='utf8') as f:
        for i in  reversed(new_items):
            f.write(','.join(i)+'\n\n')    # newline
    return new_items


# find order records by file name
def find_record(file_curr, recent_records):
    try:
        with open(file_curr,'r',encoding='utf8') as f:
            for record in f.readlines():
                record_ = record.split(',')
                if len(record_) < 4 or record_[3] == '':
                    continue
                recent_records.add(record_[3])    #  magnet link
    except:
        pass