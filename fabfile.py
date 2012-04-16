from fabric.api import task
from daemonAlertMe import monitor, models

@task
def run_check():
    models.init_model()
    a_session = models.Session()
    alerter = monitor.EmailAlert(a_session)

    #Run app
    monitor.UriMonitor(a_session, alerter).run_all()
    a_session.flush()
    #teardown
    models.Session.remove()


