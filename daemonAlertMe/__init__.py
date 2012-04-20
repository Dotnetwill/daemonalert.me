__author__ = 'will@will.yt'

import logging

class DefaultConfig(object):
    LOG_LEVEL = logging.DEBUG
    LOG_PATH = 'daemonAlertMe.log'
    CONN_STRING = u'sqlite:///site.db'
    ECHO_SQL = False
    EMAIL_HOST = u'localhost'
    EMAIL_USER = u''
    EMAIL_PWD = u''
    EMAIL_SENDER = u'info@DaemonAlert.me'
    FLASK_SECRET_KEY = 'BIG_NIPS'

config = DefaultConfig()

#Config logging
log = logging.getLogger("daemonAlertMe")
log.setLevel(config.LOG_LEVEL)

fh = logging.FileHandler(config.LOG_PATH)
formatter = logging.Formatter("%(asctime)s - %(filename)s :: #%(lineno)d ::" +
"%(funcName)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)

log.addHandler(fh)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
log.addHandler(console_handler)


