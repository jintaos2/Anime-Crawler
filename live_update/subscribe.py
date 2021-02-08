import re
import datetime
import os

  
def update_message(new_items, message_file):
    rules = [Rule(i) for i in read_rules()]
    for i in rules:
        i.title_and = []
        i.epsodes = '*'
    for item in reversed(new_items):
        for rule in rules:
            idx = rule.match(item[1] + ' ' + item[2])
            if idx != -1:
                with open(message_file,'a+', encoding='utf8') as f:
                    f.write('{}'.format(datetime.datetime.today())[:-7] + ' [new] ' + item[2] + '\n')
                break 


def download(message_file):
    items = read_history(7)
    rules = [Rule(i) for i in read_rules()]
    for rule in rules:
        results = {}
        for item in items:
            idx = rule.match(item[1] + ' ' + item[2])
            if idx != -1:
                key = idx
                if not key in results:
                    results[key] = []
                results[key].append(item)
        download2(results, message_file)
        for i in results.keys():      # delete some rules
            if i == '*':
                rule.epsodes = []
                break
            # else i is a number
            rule.delete(i)
        if len(rule.epsodes) == 0:
            rules.remove(rule)
    write_rules(rules)
        
def download2(results, message_file):
    if '*' in results.keys():
        for i in results['*']:
            download3(i,message_file)
    else:
        for i in results.values():
            download3(i[0],message_file)

def download3(item, message_file):
    with open(message_file,'a+', encoding='utf8') as f:
        f.write('{}'.format(datetime.datetime.today())[:-7] + ' [download] ' + item[2] + ', ' + item[4], '\n')




def read_rules():
    ret = []
    try:
        with open('subscribe/mylist.txt', 'r', encoding='utf8') as f:
            l = f.read()
            ret += re.findall(r'{[\s\S]*?}',l)
    except:
        pass            
    return ret

def write_rules(rules):
    try:
        with open('subscribe/mylist.txt', 'w+', encoding='utf8') as f:
            for i in rules:
                f.write(i.store()+'\n')
    except:
        pass 


def read_history(days):
    files = [i for i in sorted(os.listdir('dmhy'), reverse=True) if len(i)==14][0:days]
    items = []
    for i in files:
        with open('dmhy/'+i, 'r',encoding='utf8') as f:
            records = f.readlines()
            for record in reversed(records):
                record_ = record[:-1].split(',')
                if len(record_) >3 and record_[3] != '':
                    items.append(record_)     
    return items

class Rule():
    def __init__(self, s):
        temp = re.findall(r'title_or.*',s)[0]
        self.title_or = re.findall(r"'(.*?)'",temp)
        temp = re.findall(r'title_and.*',s)[0]
        self.title_and = re.findall(r"'(.*?)'",temp)
        temp = re.findall(r'epsode_re.*',s)[0]
        temp = re.findall(r"'(.*?)'",temp)
        self.epsode_re = '' if len(temp)==0 else temp[0]  
        temp = re.findall(r'epsodes.*',s)[-1]
        epsodes_ = re.findall(r"'(.*?)'",temp)
        self.epsodes = []
        for i in epsodes_:
            if i == '*':
                self.epsodes = ['*']
                break
            ii = i.split('-')
            if len(ii) == 1:
                self.epsodes.append(int(i))
            elif len(ii) == 2:
                self.epsodes += list(range(int(ii[0]),int(ii[1])+1))
                
    def show(self):
        return  [','.join(["'"+i+"'" for i in self.title_or]), 
                 ','.join(["'"+i+"'" for i in self.title_and]), 
                           "'"+self.epsode_re+"'",
                 ','.join(["'"+self.tostr(i)+"'" for i in self.epsodes])]
    def tostr(self,n):
        if n == '*':
            return n
        if n < 10:
            return '0{}'.format(n)
        else:
            return '{}'.format(n)

    def store(self):
        ll = self.show()
        r = '{\n\ttitle_or = ' + ll[0] + '\n\ttitle_and = ' + ll[1] + '\n\tepsode_re = ' + ll[2]  + '\n\tepsodes = ' + ll[3] + '\n}'
        return r
    
    def match(self,s):
        count_title_or = 0
        for i in self.title_or:
            if len(re.findall(i,s))>0:
                count_title_or += 1
        count_title_and = 0
        for i in self.title_and:
            if len(re.findall(i,s))>0:
                count_title_and += 1   
        if count_title_or > 0 and count_title_and == len(self.title_and):
            if '*' in self.epsodes:
                return '*'
            epsode_ = re.findall(self.epsode_re, s)
            if len(epsode_) > 0:
                epsode = int(epsode_[-1])
                if epsode in self.epsodes:
                    return epsode
        return -1
    def delete(self, epsode):
        while epsode in self.epsodes:
            self.epsodes.remove(epsode)


