from fabric.api import local, sudo, put, task, abort
from fabric.contrib.project import rsync_project
from os import path
from daemonAlertMe import monitor, models

remote_path = '/srv/www/daemonalert.me/app'
#remote_path = '~/test_sync/'
rsync_exclude = ['*.pyc', 
                 'dev_conf.py', 
                 '*.log', 
                 '*.db', 
                 'env', 
                 '.git', 
                 '.svn', 
                 '.idea',
                 '*.swp',  
                 '.DS_Store']

local_path = path.dirname(__file__) + '/'

@task
def deploy():
    local("git pull origin master")
    test()
    rsync_project(remote_path, local_path, exclude=rsync_exclude)
    update_site_config()

@task
def update_site_config():
    put(path.join(local_path, 'prod_conf.py'), path.join(remote_path, 'prod_conf.py'))
    restart_services()

@task
def test(args=None):
    """
        Run nosetests and can optionally pass args
    """

    if args is None:
        args = ""
    local("nosetests " + args)

def restart_services():
    sudo('supervisorctl restart all')


@task
def run_check():
    models.init_model()
    a_session = models.Session()
    email_alert = monitor.EmailAlert(a_session)
    tweet_all_alert = monitor.GeneralTweetAlert()
    tweet_at_alert = monitor.TwitterAlert(a_session)

    #Run app
    monitor.UriMonitor(a_session, [email_alert, tweet_all_alert, 
                                                 tweet_at_alert]).run_all()
    a_session.flush()
    #teardown
    models.Session.remove()


