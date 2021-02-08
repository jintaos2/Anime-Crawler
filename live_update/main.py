import time 
import datetime
import animate



while True:
    source_list = [animate.dmhy, animate.nyaa]
    time_curr = '{}'.format(datetime.datetime.today())[:-7]
    file_curr = ''
    N_new = 0
    for i_ in source_list:
        try:
            file_curr, N_new = i_()
        except Exception as e:
            with open("log.txt",'a+', encoding='utf8') as f:
                f.write("{} {} update error! {}\n".format(time_curr, i_.__name__, e)) 
        else:
            with open("log.txt",'a+', encoding='utf8') as f:
                f.write("{} {} update {} items.\n".format(time_curr, i_.__name__, N_new))        

    time.sleep(720)