import re
import datetime
    
def update_subscribe(N):
    records = []
    curr_date = datetime.date.today()
    for i in range(N):
        file_curr = 'dmhy/{}.txt'.format(curr_date - datetime.timedelta(days=i))
        print(file_curr)
        find_record(file_curr,records)

    keywords = []
    with open('subscribe/mylist.txt', 'r', encoding='utf8') as f:
        l = f.readlines()
        for i in l:
            keywords += i.split(',')[1:-1]
    
    result = []
    for i in records:
        for j in keywords:
            if re.search(j,i[0]):
                result.append(','.join([i[0],i[1],'']))
    with open("subscribe/results.txt", 'w', encoding='utf8') as f:
        for i in result:
            f.write(i+'\n')


def find_record(file_curr, records):
    try:
        with open(file_curr,'r',encoding='utf8') as f:
            l = f.readlines()
            for line in reversed(l):
                record_ = line[:-1].split(',')
                if len(record_) < 4 or record_[1] != '動畫':
                    continue
                else:
                    records.append([record_[2],record_[3]])     
    except:
        pass


update_subscribe(7)