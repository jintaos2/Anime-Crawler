import time 
import updater
import logs
import sys
import os
import traceback

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        logs._debug = True 
        module = updater.Updater()
        module.update()
        module.download()
        os._exit(1)


    time.sleep(1)

    module = updater.Updater()

    while True:
        curr_time = time.time()
        try:
            logs.error_logger.info("++++++++++++++++++++++++++++++++++++++")
            module.update()
            logs.error_logger.info(f"------ crawl cost:{time.time() - curr_time} seconds")
            curr_time = time.time()
            module.download()
            logs.error_logger.info(f"------ match cost:{time.time() - curr_time} seconds")
        except Exception as e:
            logs.error_logger.info(traceback.format_exc())
        time.sleep(900)

