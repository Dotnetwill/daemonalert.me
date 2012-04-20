__author__ = 'will@will.yt'

import logging

class DefaultConfig(object):
    """
        Configuration class with all the options set to sensible or
        publicly viewable defaults.  See the GetConfig method for details
        on how a config is loaded
    """
    LOG_LEVEL = logging.DEBUG
    LOG_PATH = 'daemonAlertMe.log'
    CONN_STRING = u'sqlite:///site.db'
    ECHO_SQL = False
    EMAIL_HOST = u'localhost'
    EMAIL_USER = u''
    EMAIL_PWD = u''
    EMAIL_SENDER = u'info@DaemonAlert.me'
    FLASK_SECRET_KEY = 'BIG_NIPS'
    TW_CONSUMER_KEY = ''
    TW_CONSUMER_SECRET = ''
    TW_ACCESS_TOKEN = ''
    TW_ACCESS_TOKEN_SECRET = ''

def GetConfig():
    """
        Tries to load configuration for the site in the following order:
            *Try to import prod_conf
            *Try to import debug_conf
            *Use DefaultConfig class
    """
    try:
        import prod_conf
        print("Using the production config")
        return prod_conf.Config()
    except ImportError:
        pass

    try:
        import debug_conf
        print("Using debug config")
        return debug_conf.Config()
    except ImportError:
        pass
    print("Using DefaultConfig")
    return DefaultConfig()

config = GetConfig()

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


