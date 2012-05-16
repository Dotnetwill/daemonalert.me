import urllib2
import hashlib
import datetime
import twitter
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
            self.uri_check.check_options = page_hash.encode('utf-8')
            return True
        else:
            return False


class UriMonitor(object):
    """
        Finds all the url that have associated alerts and runs a check on them
    """

    def __init__(self, dbsession, alerters):
        self.db_session = dbsession
        self.alerters = alerters

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
                    for alerter in self.alerters:
                        alerter.send_alerts_for_id(check.check_id, check.url)
            except urllib2.URLError, e:
                log.error('unable to query url: %s' % e)


class BaseAlert(object):
    """Base class for sending out notifications"""

    NO_LIMIT = -1
    def __init__(self, db_session):
        "Sets the DBsession to find alerts in"
        self.db_session = db_session

    def send_alerts_for_id(self, check_id, url):
        pass

    def _get_valid_alerts_by_type(self, alert_type, check_id):
        alerts = self.db_session.query(Alert)\
          .from_statement("""SELECT * FROM Alerts
                        WHERE check_id = :cid 
                            AND alert_type = :atype
                            AND stop = 0
                            AND (num_of_times = :no_limit_value
                              OR num_of_times_alerted < num_of_times)""")\
          .params(cid = check_id, no_limit_value = EmailAlert.NO_LIMIT, 
                  atype = alert_type).all()

        #Return items one by one and see if we need to stop the alert
        for alert in alerts:
            #Hand off to child class
            yield alert
            #Work out if we should stop
            alert.num_of_times_alerted = alert.num_of_times_alerted + 1
            if not alert.num_of_times == self.NO_LIMIT \
               and alert.num_of_times_alerted >= alert.num_of_times:
                alert.stop = True


class GeneralTweetAlert(BaseAlert):
    """
        Sends out a tweet for every URL update
    """
    
    def __init__(self):
        super(GeneralTweetAlert, self).__init__(None)

    def send_alerts_for_id(self, check_id, url):
        try:
            twitter_api = twitter.Api(consumer_key=config.TW_CONSUMER_KEY,
                            consumer_secret=config.TW_CONSUMER_SECRET,
                            access_token_key=config.TW_ACCESS_TOKEN,
                            access_token_secret=config.TW_ACCESS_TOKEN_SECRET)

            twitter_api.PostUpdate(u"URL Changed: %s" % url)
            log.info("Tweeted to public stream")

        except twitter.TwitterError, e:
            log.error(u"TwitterError: %s" % e)

class EmailAlert(BaseAlert):
    """
        Finds alerts setup for a url change and sends an email
    """

    def __init__(self, db_session):
        super(EmailAlert,self).__init__(db_session)

    def send_alerts_for_id(self, check_id, url):
        for alert in self._get_valid_alerts_by_type(u"email", check_id):
            log.info('found someone to alert ' + alert.target)
            self._create_email(alert, url)

    def _create_email(self, alert, url):
        template_name = 'alert'
        if alert.num_of_times == self.NO_LIMIT:
            template_name = 'forever_alert'
        elif alert.stop:
            template_name = 'last_alert'

        email_sender.send_email(alert.target, template_name, 
                'Alert: URL Change', url=url, aid=alert.alert_id)

class TwitterAlert(BaseAlert):
    """ Sends an @ message to a twitter username to when a URL is updated"""
    ALERT_TYPE = u"twitter"
    def __init__(self, db_session):
        super(TwitterAlert, self).__init__(db_session)

    def send_alerts_for_id(self, check_id, url):
        for alert in self._get_valid_alerts_by_type(self.ALERT_TYPE, check_id):
            log.info('found someone to tweet @ ' + alert.target)
            self._send_tweet(alert.target, url)
    
    def _send_tweet(self, target, url):
        try:
            twitter_api = twitter.Api(consumer_key=config.TW_CONSUMER_KEY,
                            consumer_secret=config.TW_CONSUMER_SECRET,
                            access_token_key=config.TW_ACCESS_TOKEN,
                            access_token_secret=config.TW_ACCESS_TOKEN_SECRET)

            twitter_api.PostUpdate(u"%s URL Changed: %s" %
                                        (self._tidy_name(target), url))
            log.info("Tweeted %s to say there was a change" % target)

        except twitter.TwitterError, twe:
            log.error(u"TwitterError: %s" % twe)

    def _tidy_name(self, target):
        if not target.startswith('@'):
            return '@' + target
        return target
