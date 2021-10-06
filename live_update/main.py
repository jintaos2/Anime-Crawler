import time 
import updater
import logs
import sys
import os

if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
        logs._debug = True 
        module = updater.Updater()
        module.update()
        module.download()
        os._exit(1)


    time.sleep(60)

    module = updater.Updater()

    while True:
        try:
            module.update()
            module.download()
        except Exception as e:
            logs.error_logger.info(f"[error] {e}")
        time.sleep(600)

