import logging
import logging.handlers


LOG_NAME = 'uvo.log'
LOG_PATH = '/home/pi/source/UVO/'
LOG_SIZE = 50 * 1024 * 1024 # 50MB
LOG_COUNT = 5
LOG_FULL_PATH = LOG_PATH + LOG_NAME

log = logging.getLogger(LOG_NAME)
log.setLevel(logging.DEBUG)


log_handler = logging.handlers.RotatingFileHandler(LOG_FULL_PATH, maxBytes=LOG_SIZE, backupCount=LOG_COUNT)
log.addHandler(log_handler)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

log_handler.setFormatter(formatter)
