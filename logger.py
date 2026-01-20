import logging

LOG_FILENAME = "logfile.log"
logging.basicConfig(filename='log_execucao.log',level=logging.DEBUG,
                    filemode='w+',
                    format='%(asctime)s - %(levelname)s:%(message)s', datefmt='%d/%m/%Y %I:%M:%S %p',
                    encoding='utf-8'
                    )