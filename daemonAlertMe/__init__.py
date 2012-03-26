__author__ = 'will@will.yt'

import logging
log = logging.getLogger('daemonAlertMe')

fh = logging.FileHandler('daemonAlertMe.log')
formatter = logging.Formatter('%(asctime)s - %(filename)s :: #%(lineno)d :: %(funcName)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

log.addHandler(fh)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
log.addHandler(console_handler)

class DefaultConfig(object):
    CONN_STRING = u'sqlite:///site.db'
    ECHO_SQL = False
    EMAIL_HOST = u''
    EMAIL_USER = u''
    EMAIL_PWD = u''
    EMAIL_SENDER = u'info@DaemonAlert.me'

config = DefaultConfig()


