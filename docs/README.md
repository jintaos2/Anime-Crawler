### Introducton 

自用动漫爬虫，每隔10分钟爬取 dmhy.org 首页并跟新本地缓存，自动匹配番剧，自动 aria2c 下载。还包含全局动漫搜索和纪录片爬取的 jupyter notebook.

##### 环境　

- aria2c
- python3

### Files


```
Animate_crawler                  
├─ history                               
│  ├─ dmhy_update_all.ipynb      
│  └─ docuwiki_update_all.ipynb  
├─ live_update                                 
│  ├─ anime.py                   
│  ├─ config.json                
│  ├─ logs.py                    
│  ├─ main.py                    
│  ├─ subscribe.py               
│  └─ updater.py                 
├─ LICENSE                       
└─ README.md                     
                         
```

### live_update

run: `python main.py`

`config.json`

```json 
{
    "log_dir": "./log",
    "download_dir": "/root/anime",
    "aria2": "http://192.168.3.123:6800/rpc"
}
```

番剧列表: `./log/mylist.json`

```json
[{
    "dir": "致不灭的你",
    "title": [
        "致不灭的你|Fumetsu no Anata",
        "動畫"
    ],
    "title_optional": [
        "简|CHS|GB",
        "1080"
    ],
    "epsode_filter": "[^a-zA-Z0-9](\\d\\d)[^a-zA-Z0-9]",
    "order": 0,
    "status": "active",
    "epsodes": [
        "11-15"
    ]
},
{
    "dir": "Back Arrow",
    "title": [
        "Back Arrow",
        "動畫"
    ],
    "title_optional": [
        "简|CHS|GB",
        "1080"
    ],
    "epsode_filter": "[^a-zA-Z0-9](\\d\\d)[^a-zA-Z0-9]",
    "order": 0,
    "status": "active",
    "epsodes": [
        "24-26"
    ]
}]
```

### dmhy_update_all.ipynb 

1. 指定页数，爬取 dmhy 历史数据，按月存在本地。如果本地没有缓存，先爬老的数据，再爬新的数据，反之顺序将出错。
2. 指定上述规则，搜索历史番剧，自动下载。 

### docuwiki_update_all.ipynb 

爬取 docuwiki.net 上按年分类记录片，每次新增记录会再次保持在另一文件。爬取内容为标题和 ed2k 链接



