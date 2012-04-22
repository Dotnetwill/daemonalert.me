from fabric.api import task
from daemonAlertMe import monitor, models

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


