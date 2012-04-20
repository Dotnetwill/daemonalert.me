import urllib2
import hashlib
import datetime
from marrja_mail import MarrjaMailer
from daemonAlertMe import log, config
from daemonAlertMe.models import UriCheck, Alert 

email_sender = MarrjaMailer('daemonAlertMe', server=config.EMAIL_HOST, 
        username=config.EMAIL_USER, password=config.EMAIL_PWD, 
        default_sender=config.EMAIL_SENDER)


class HashCheck(object):
    """
        Creates a sha1 has of a URL then compares it with what we have stored
    """
    def __init__(self, uri_check):
        self.uri_check = uri_check
    
    def get_hash(self, url_stream):
        page = url_stream.read()
        return hashlib.sha1(page).hexdigest()

    def has_changes(self, url_stream):
        page_hash = self.get_hash(url_stream)
        if not page_hash == self.uri_check.check_options:
            self.uri_check.check_options = page_hash
            return True
        else:
            return False
    
class UriMonitor(object):
    """
        Finds all the url that have associated alerts and runs a check on them
    """
    def __init__(self, dbsession, alerter):
        self.db_session = dbsession
        self.alerter = alerter
        
    def run_all(self):
        checks_to_run = self.db_session.query(UriCheck)\
                .from_statement("""SELECT UriChecks.check_id, url, check_type,
                                          check_options, last_check 
                                   FROM UriChecks 
                                   JOIN Alerts AS a ON 
                                       UriChecks.check_id = a.check_id 
                                   WHERE a.stop = 0""").all()
        for check in checks_to_run:
            log.info('about to run check on ' + check.url)
            check.last_check = datetime.datetime.utcnow()

            try:
                hash_check = HashCheck(check)
                url_stream = urllib2.urlopen(check.url)
                if hash_check.has_changes(url_stream):
                    log.info('hash changes requesting alert sent')
                    self.alerter.send_alerts_for_id(check.check_id, check.url)
            except urllib2.URLError, e:
                log.error('unable to query url: %s' % e)

class EmailAlert(object):
    """
        Finds alerts setup for a url change and sends an email
    """
    NO_LIMIT = -1
    def __init__(self, db_session):
        self.db_session = db_session

    def send_alerts_for_id(self, check_id, url):
        alerts = self.db_session.query(Alert)\
          .from_statement("""SELECT * FROM Alerts
                        WHERE check_id = :cid 
                            AND stop=0 
                            AND (num_of_times = :no_limit_value
                              OR num_of_times_alerted < num_of_times)""")\
          .params(cid = check_id, no_limit_value = EmailAlert.NO_LIMIT).all()

        for alert in alerts:
            log.info('found someone to alert ' + alert.email)
            self._create_email(alert, url)
            alert.num_of_times_alerted = alert.num_of_times_alerted + 1

            if not alert.num_of_times_alerted == self.NO_LIMIT \
                    and alert.num_of_times_alerted >= alert.num_of_times:
                alert.stop = True

    def _create_email(self, alert, url):
        template_name = 'alert'
        if alert.num_of_times == self.NO_LIMIT:
            template_name = 'forever_alert'
        elif alert.stop:
            template_name = 'last_alert'

        email_sender.send_email(alert.email, template_name, 
                'Alert: URL Change', url=url, aid=alert.id)

