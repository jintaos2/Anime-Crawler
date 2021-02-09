import time 
import datetime
import os
import animate
import subscribe


if __name__ == "__main__":

    message_file = os.path.join(os.path.expanduser("~"), 'Desktop', 'massage_sync', 'log.txt') # another log file on desktop

    while True:

        source_list = [animate.dmhy]
        time_curr = '{}'.format(datetime.datetime.today())[:-7]
        new_items = []
        for i_ in source_list:
            try:
                new_items = i_()  # update local cache of records 
                subscribe.update_message(new_items, message_file)  # write title of subscribed items into log file 
                subscribe.download(message_file)  # download items match rules, write log file, update rules
            except Exception as e:
                with open("log.txt",'a+', encoding='utf8') as f:
                    f.write("{} [error] {} update error! {}\n".format(time_curr, i_.__name__, e)) 
                with open(message_file,'a+', encoding='utf8') as f:
                    f.write("{} [error] {} update error! {}\n".format(time_curr, i_.__name__, e))             
            else:
                with open("log.txt",'a+', encoding='utf8') as f:
                    f.write("{} [update] {} update {} items.\n".format(time_curr, i_.__name__, len(new_items)))    

        with open(message_file,'a+', encoding='utf8') as f:
            f.write("\n") 
        time.sleep(720)