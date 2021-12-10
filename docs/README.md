### Introducton 

自用动漫爬虫，每隔10分钟爬取 dmhy.org 及其镜像站首页并跟新本地缓存，自动匹配番剧，自动 aria2c 下载。
每季度更新自用动漫列表

### Environment　

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
[  
  {
    "dir": "86-不存在的战区",
    "title": [
      "不存在的战区|EIGHTY SIX",
      "動畫",
      "简|CHS|GB|繁|CHT|BIG5"
    ],
    "order": 0,
    "epsodes": [
      "20-24"
    ]
  },
  {
    "dir": "看得见的女孩",
    "title": [
      "看得见的女孩|Mieruko-chan",
      "動畫",
      "简|CHS|GB|繁|CHT|BIG5"
    ],
    "order": 0,
    "epsodes": [
      "11-13"
    ]
  }
]
```



