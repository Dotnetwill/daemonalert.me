import urllib2
import hashlib
import datetime
import smtplib
from daemonAlertMe import log
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from daemonAlertMe.models import UriCheck, Alert 

SMTP_SERVER = 'localhost'
SMTP_SERVER_UNAME = ''
SMTP_SERVER_PWD = ''
SENDER_EMAIL = 'alert@daemonalert.me'


class HashCheck(object):
    def __init__(self, uri_check):
        self.uri_check = uri_check
    
    def get_hash(self, url_stream):
        page = url_stream.read()
        return hashlib.md5(page).hexdigest()

    def has_changes(self, url_stream):
        hash = self.get_hash(url_stream)
        if not hash == self.uri_check.check_options:
            self.uri_check.check_options = hash
            return True
        else:
            return False
    
class UriMonitor(object):
    def __init__(self, dbsession, alerter):
        self.db_session = dbsession
        self.alerter = alerter
        
    def run_all(self):
        checks_to_run = self.db_session.query(UriCheck).from_statement("SELECT UriChecks.id, url, check_type, check_options, last_check FROM UriChecks JOIN Alerts AS a ON UriChecks.id = a.check_id").all()
        for check in checks_to_run:
            log.info('about to run check on ' + check.url)
            check.last_check = datetime.datetime.now()
            try:
                hash_check = HashCheck(check)
                url_stream = urllib2.urlopen(check.url)
                if hash_check.has_changes(url_stream):
                    log.info('hash changes requesting alert sent')
                    self.alerter.send_alerts_for_id(check.id, check.url)
            except urllib2.URLError, e:
                log.error('unable to query url: %s' % e)

class EmailAlert(object):
    
    NO_LIMIT = -1
    def __init__(self, db_session):
        self.db_session = db_session
        
    def send_alerts_for_id(self, check_id, url):
        alerts = self.db_session.query(Alert).from_statement("SELECT * FROM Alerts WHERE check_id = :id AND (num_of_times = :no_limit_value OR num_of_times_alerted < num_of_times)").params(id = check_id, no_limit_value = EmailAlert.NO_LIMIT).all()
        for alert in alerts:
            log.info('found someone to alert ' + alert.email)
            self._create_email(alert, url)
            alert.num_of_times_alerted = alert.num_of_times_alerted + 1
       
            
            
    def _create_email(self, alert, url):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Alert: URL Changed!'
        msg['To'] = alert.email
        msg['From'] = SENDER_EMAIL
        
        text = "Hi\nThe URL you asked us to monitor has change: " +  url
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               
               The URL you asked us to monitor has change:<a href="{0}">{0}</a>.
            </p>
          </body>
        </html>
        """.format(url)
        plain_part = MIMEText(text, 'plain')
        html_part = MIMEText(html, 'html')
        
        msg.attach(plain_part)
        msg.attach(html_part)
      
        self._send_mail(msg, alert.email)

    def _send_mail(self, email, target_email):
        s = smtplib.SMTP(SMTP_SERVER)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(SMTP_SERVER_UNAME, SMTP_SERVER_PWD)
        s.sendmail(SMTP_SERVER_UNAME, target_email, email.as_string())
        s.quit()

#if __name__ == '__main__':
#    a_session = get_session(init_engine(config.SQL_CONNECTION))()
#    alerter = EmailAlert(a_session)
#    #Run app
#    UriMonitor(a_session, alerter).run_all()
    
    #teardown
#    a_session.remove()
    