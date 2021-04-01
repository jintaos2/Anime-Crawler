import re
import datetime
import os
import xmlrpc.client


class subscribe:
    def __init__(self, logfile, download_dir, aria2_server):
        self.logfile = logfile
        self.download_dir = download_dir
        self.download_count = 0
        self.aria2_server = aria2_server
  
    def update_message(self,new_items):
        rules =  self.read_rules()
        for i in rules:
            i.epsodes = '*'
        for item in reversed(new_items):
            for rule in rules:
                idx, _ = rule.match(item[1] + ' ' + item[2])
                if idx != -1:      # new match
                    with open(self.logfile,'a+', encoding='utf8') as f:
                        f.write('{}'.format(datetime.datetime.today())[:-7] + ' [new] ' + item[2] + '\n')
                    break 


    def download(self): 
        self.download_count = 0
        items = self.read_history(30)
        rules =  self.read_rules()
        for rule in rules:
            results = {}
            for item in items:
                idx, score = rule.match(item[1] + ' ' + item[2])
                if idx != -1:
                    key = idx
                    if not key in results:
                        results[key] = []
                    results[key].append([score] + item[1:])
            self.download_score(results, rule.title_or[0])  # select the highest score for multi matches
            for i in results.keys():      # delete some rules
                if i == '*':
                    rule.epsodes = []
                    break
                # else i is a number
                rule.delete(i)
            if len(rule.epsodes) == 0:
                rules.remove(rule)
        if self.download_count > 0:
            with open(self.logfile,'a+', encoding='utf8') as f:
                f.write('-----------------\n')         
        self.write_rules(rules)
            
    def download_score(self,results, title):
        if '*' in results.keys():
            for i in results['*']:
                self.download_item(i, title)
        else:
            for i in results.values():
                i.sort(key = lambda x: x[0], reverse=True)
                self.download_item(i[0], title)         

    # item format: date, title, link, size, xxx
    def download_item(self,item, title):
        if item[0] < 1:
            return
        with open(self.logfile,'a+', encoding='utf8') as f:
            f.write('{}'.format(datetime.datetime.today())[:-7] + ' [download] ' + item[2] + '\n')
            self.download_count += 1
        try:
            s = xmlrpc.client.ServerProxy(self.aria2_server)
            s.aria2.addUri([item[3]],{'dir': os.path.join(self.download_dir, title)})
        except Exception as e:
            with open(self.logfile,'a+', encoding='utf8') as f:
                f.write('{}'.format(datetime.datetime.today())[:-7] + ' [error] download error! ' + e + '\n')  

    def read_rules(self):
        ret = []
        try:
            with open('subscribe/mylist.txt', 'r', encoding='utf8') as f:
                l = f.read()
                ret += re.findall(r'{[\s\S]*?}',l)
        except:
            pass            
        return [Rule(i) for i in ret]

    def write_rules(self,rules):
        try:
            with open('subscribe/mylist.txt', 'w+', encoding='utf8') as f:
                for i in rules:
                    f.write(i.store()+'\n')
        except:
            pass 

    def read_history(self,days):
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
        temp = re.findall(r'title_and.*',s)
        if len(temp) == 0:
            temp = [r"""'動畫','简|CHS|GB','1080'"""]
        self.title_and = re.findall(r"'(.*?)'",temp[0])
        temp = re.findall(r'epsode_re.*',s)
        if len(temp)==0:
            temp = [r"""'[^a-zA-Z0-9](\d\d)[^a-zA-Z0-9]'"""]
        temp = re.findall(r"'(.*?)'",temp[0])
        self.epsode_re = '' if len(temp)==0 else temp[0]  
        temp = re.findall(r'epsodes.*',s)
        if len(temp)==0:
            temp = [r"""'*'"""]
        epsodes_ = re.findall(r"'(.*?)'",temp[-1])
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
        if count_title_or > 0:
            if '*' in self.epsodes:
                return '*', count_title_and
            epsode_ = re.findall(self.epsode_re, s)
            if len(epsode_) > 0 and re.match(r'\d\d', epsode_[-1]):
                epsode = int(epsode_[-1])
                if epsode in self.epsodes:
                    return epsode, count_title_and
        return -1, 0
    def delete(self, epsode):
        while epsode in self.epsodes:
            self.epsodes.remove(epsode)


