import logging 

error_logger = logging.getLogger('error')
update_logger = logging.getLogger('info')

def _init(error_log:str, update_log:str):
    global error_logger
    global update_logger
    error_logger.setLevel(logging.INFO)
    update_logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler(error_log, mode='a', encoding='utf8')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s (%(filename)s:%(lineno)d) %(message)s ",'%Y/%m/%d %H:%M:%S')
    fh.setFormatter(formatter)
    error_logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    error_logger.addHandler(ch)

    fh = logging.FileHandler(update_log, mode='a', encoding='utf8')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(message)s",'%Y/%m/%d %H:%M:%S')
    fh.setFormatter(formatter)
    update_logger.addHandler(fh)
    error_logger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    
    with open(error_log, 'a+', encoding='utf8') as f:
        f.write("start\n")