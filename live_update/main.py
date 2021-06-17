import time 
import updater
import logs


if __name__ == "__main__":

    time.sleep(1)

    module = updater.Updater()

    while True:
        try:
            module.update()
            module.download()
        except Exception as e:
            logs.error_logger.info(f"[error] {e}")
        time.sleep(600)

