### Introducton 

自用动漫爬虫，每隔10分钟爬取 dmhy.org 首页并跟新本地缓存，自动匹配番剧，自动 aria2c 下载。还包含全局动漫搜索和纪录片爬取的 jupyter notebook.

### Files


```
Animate_crawler                    
├─ dmhy                        # all data of dmhy.org, by month  
├─ docu                        # all data of docuwiki.net, by year   
├─ live_update                 # real time update 
│  ├─ dmhy                     # data of dmhy.org, by day 
│  ├─ nyaa                     # data of nyaa.si, by day    
│  ├─ subscribe                    
│  │  └─ mylist.txt            # user rules of subscribe items
│  ├─ animate.py              
│  ├─ log.txt                  # log file
│  ├─ main.py                  # main file
│  └─ subscribe.py             
├─ dmhy_update_all.ipynb           
└─ docuwiki_update_all.ipynb                            
```

### live_update

`python main.py`

`mylist.txt` 订阅规则示例：
```
{
    title_or = '进击的巨人','Shingeki no Kyojin'
    title_and = '動畫','简|CHS|GB','1080'
    epsode_re = '[^a-zA-Z0-9](\d\d)[^a-zA-Z0-9]'
    epsodes = '65-67','68'
}
```

- `title_or`: 正则表达式列表，匹配番剧大类，其中之一匹配即匹配，不能为空
- `title_and`: 正则表达式列表，附加条件，每一项加一分，对于番剧的某一集，下载得分最高且至少1分的项。以上即为默认值，可以不写
- `epsode_re`: 匹配集数的正则表达式，以上为默认值。仅支持两位数字
- `epsodes`: 要下载的集数。支持形如 `'01-03'` 这样的缩写。`'*'` 表示完全忽略集数全部下载，默认 `'*'`
- 每一集开始下载后将删除 `mylist.txt` 规则中的集数。如果某规则集数为空，将删除该规则

简写示例
```
{
    title_or = '无职转生','Mushoku Tensei Isekai'
    epsodes = '01-12'
}
```

指定某一集示例
```
{
    title_or = '进击的巨人 The Final Season / Shingeki no Kyojin The Final Season [66][1080p][简日内嵌]'
}
```


### dmhy_update_all.ipynb 

1. 指定页数，爬取 dmhy 历史数据，按月存在本地。如果本地没有缓存，先爬老的数据，再爬新的数据，反之顺序将出错。
2. 指定上述规则，搜索历史番剧，自动下载。 

### docuwiki_update_all.ipynb 

爬取 docuwiki.net 上按年分类记录片，每次新增记录会再次保持在另一文件。爬取内容为标题和 ed2k 链接

### Other features 

两个 log 文件，一个形如
```
2021-02-09 03:33:35 [update] dmhy update 80 items.
2021-02-09 03:35:11 [update] dmhy update 7 items.
2021-02-09 03:36:58 [update] dmhy update 2 items.
2021-02-09 03:48:19 [update] dmhy update 0 items.
2021-02-09 04:00:19 [update] dmhy update 0 items.
```

一个如
```
2021-02-09 03:32:21 [new] title
2021-02-09 03:32:21 [new] title
2021-02-09 03:32:21 [download] title, 磁链
2021-02-09 03:32:21 [download] title, 磁链
```
用于消息同步

### Notice 

自用版本，仅供参考

