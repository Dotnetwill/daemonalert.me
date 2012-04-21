import unittest
import urllib2
import daemonAlertMe
from daemonAlertMe.models import UriCheck, Alert, init_model
from daemonAlertMe.monitor import HashCheck,  UriMonitor, EmailAlert
from daemonAlertMe.site import create_app
import daemonAlertMe.models
import daemonAlertMe.monitor as monitor


class FakeEmailer(object):
    def __init__(self):
        self.send_called = False
        self.send_args = None
        self.sent_to = None
        self.with_template = None
        self.sent_with_subject = None

    def send_email(self, send_to, template, subject, **kwargs):
        self.send_called = True
        self.send_args = kwargs
        self.sent_to = send_to
        self.with_template = template
        self.sent_with_subject = subject


class FakeAlerter(object):
    def __init__(self):
        self.alert_called = False

    def send_alerts_for_id(self, check_id, url):
        self.alert_called = True
        self.alert_for_id = check_id
        self.alert_url = url


class FakeCheck(object):
    last_instance = None
    change_return_value = False
    set_hash = ''
    def __init__(self, checkOptions):
        FakeCheck.last_instance = self
        self.has_changes_called = False
        self.uri_check = checkOptions

    def has_changes(self, url_stream):
        self.has_changes_called = True
        self.uri_check.check_options = self.set_hash
        return FakeCheck.change_return_value


class FakeUrlReader():
    def __init__(self, page = ''):
        self.page = page
        self.called_open = False
        self.open_call_count = 0
        self.opened_url = []

    def read(self):
        return self.page

    def open(self, url, data = None, proxies = None):
        self.called_open = True
        self.opened_url.append(url)
        self.open_call_count = self.open_call_count + 1
        return self


class HashCheckTests(unittest.TestCase):
    #SHA1 of the word page
    md_hash_page = '767013ce0ee0f6d7a07587912eba3104cfaabc15'
    def test_has_changes_hashTheSame_NoChange(self):
        uri_check = UriCheck()
        uri_check.check_options = HashCheckTests.md_hash_page

        check = HashCheck(uri_check) 
        url_reader_fake = FakeUrlReader('page')

        self.assertFalse(check.has_changes(url_reader_fake))

    def test_has_changes_hashDifferentSame_ReturnsTrue(self):
        uri_check = UriCheck()
        check = HashCheck(uri_check)
        url_reader_fake = FakeUrlReader('page')

        self.assertTrue(check.has_changes(url_reader_fake))

    def test_has_changes_hash_is_different_stored_hash_updated(self):
        uri_check = UriCheck()
        check = HashCheck(uri_check)
        url_reader_fake = FakeUrlReader('page')

        check.has_changes(url_reader_fake)
        self.assertEqual(uri_check.check_options, HashCheckTests.md_hash_page)


class DbTest(unittest.TestCase):
    def setUp(self):
        daemonAlertMe.config.SQL_CONNECTION = u'sqlite:///::memory::'
        init_model()
        self.cur_session = daemonAlertMe.models.Session()
        self.setup_for_test()

    def tearDown(self):
        self.cur_session.connection().execute("DELETE FROM " \
                                                + UriCheck.__tablename__)
        self.cur_session.connection().execute("DELETE FROM " \
                                                + Alert.__tablename__)
        self.clean_up_after_test()

    def add_with_one_uri_check_with_id_and_no_alerts(self, aid = 1, url='google.com'):
        uri_check = UriCheck()
        uri_check.check_id = aid
        uri_check.check_options = ''
        uri_check.url = url
        self.cur_session.add(uri_check)
        self.cur_session.flush()

    def add_alert_for_uri_check_with_id(self, uri_check_id=1,
            target_email='test@test.com', num_of_times = 1,
            num_of_times_alerted=0):

        alert = Alert()
        alert.check_id = uri_check_id
        alert.target = target_email
        alert.num_of_times = num_of_times
        alert.num_of_times_alerted = num_of_times_alerted
        self.cur_session.add(alert)
        self.cur_session.flush()


class UriMonitorTests(DbTest):
    def setup_for_test(self):
        #Fale alerter
        self.alerter = FakeAlerter()

        #The class under test
        self.monitor = UriMonitor(self.cur_session, [self.alerter])

        #Patch out urlopen
        self.fake_url_reader = FakeUrlReader()
        self.patched_openurl = urllib2.urlopen

        urllib2.urlopen = self.fake_url_reader.open

        #patch out hashcheck class
        self.old_hash_check = daemonAlertMe.monitor.HashCheck
        daemonAlertMe.monitor.HashCheck = FakeCheck

    def clean_up_after_test(self):
        #Restore hashcheck class
        daemonAlertMe.monitor.HashCheck = self.old_hash_check

        #Restore urlopen from patch
        urllib2.urlopen = self.patched_openurl

    def test_run_all_1_check_no_alerts_no_url_opened(self):
        self.add_with_one_uri_check_with_id_and_no_alerts()

        self.monitor.run_all()

        self.assertFalse(self.fake_url_reader.called_open)

    def test_run_all_1_check_with_alert_url_opened(self):
        self.add_with_one_uri_check_with_id_and_no_alerts()
        self.add_alert_for_uri_check_with_id()

        self.monitor.run_all()

        self.assertTrue(self.fake_url_reader.called_open)
        self.assertEquals('google.com', self.fake_url_reader.opened_url[0])

    def test_run_all_2_check_with_1_alert_url_opened(self):
        expected_url = 'open_me'
        self.add_with_one_uri_check_with_id_and_no_alerts()
        self.add_with_one_uri_check_with_id_and_no_alerts(aid = 2,
                                                          url=expected_url)
        self.add_alert_for_uri_check_with_id(uri_check_id = 2)

        self.monitor.run_all()

        self.assertTrue(self.fake_url_reader.open_call_count == 1)
        self.assertEquals(expected_url, self.fake_url_reader.opened_url[0])

    def test_run_all_1_check_with_alert_hash_check_called(self):
        self.add_with_one_uri_check_with_id_and_no_alerts()
        self.add_alert_for_uri_check_with_id(uri_check_id = 1)

        self.monitor.run_all()

        self.assertTrue(FakeCheck.last_instance.has_changes_called)

    def test_run_all_1_check_with_alert_check_changed_alert_sent(self):
        expected_check_id = 1
        expected_url = 'google.com'
        self.add_with_one_uri_check_with_id_and_no_alerts(
                                aid = expected_check_id, url=expected_url)
        self.add_alert_for_uri_check_with_id(uri_check_id = expected_check_id)
        FakeCheck.change_return_value = True

        self.monitor.run_all()

        self.assertTrue(self.alerter.alert_called)
        self.assertEqual(self.alerter.alert_for_id, expected_check_id)
        self.assertEqual(self.alerter.alert_url, expected_url)

    def test_run_all_1_check_with_hash_change_new_hash_and_time_saved(self):
        expected_check_id = 1
        expected_url = 'google.com'
        self.add_with_one_uri_check_with_id_and_no_alerts(
                                aid = expected_check_id, url=expected_url)
        self.add_alert_for_uri_check_with_id(uri_check_id = expected_check_id)
        FakeCheck.change_return_value = True
        FakeCheck.set_hash = 'updated_hash'

        self.monitor.run_all()

        check = self.cur_session.query(UriCheck)\
                .filter_by(check_id = expected_check_id).one() 
        
        assert 'updated_hash' == check.check_options

    def test_run_all_1_check_with_alert_check_no_changed_alert_not_sent(self):
        expected_check_id = 1
        expected_url = 'google.com'
        self.add_with_one_uri_check_with_id_and_no_alerts(
                                                aid = expected_check_id,
                                                url=expected_url)
        self.add_alert_for_uri_check_with_id(uri_check_id = expected_check_id)
        FakeCheck.change_return_value = False

        self.monitor.run_all()

        self.assertFalse(self.alerter.alert_called)

class EmailAlertTests(DbTest):
    def setup_for_test(self):
        self.email_alert = EmailAlert(self.cur_session)
        self.patched_out_sender = monitor.email_sender
        monitor.email_sender = FakeEmailer()

    def clean_up_after_test(self):
        monitor.email_sender = self.patched_out_sender

    def test_send_alerts_for_id_no_alert_nothing_sent(self):
        uri_check_id = 1
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)

        self.email_alert.send_alerts_for_id(uri_check_id, '')

        assert not  monitor.email_sender.send_called

    def test_send_alerts_for_id_1_alert_msg_sent(self):
        uri_check_id = 1
        expected_target_email = 'target@test.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, 
                                             expected_target_email)

        self.email_alert.send_alerts_for_id(uri_check_id, '')

        assert monitor.email_sender.send_called
        assert monitor.email_sender.sent_to == expected_target_email 

    def test_send_alerts_for_id_1_alert_msg_sent_with_url_in(self):
        uri_check_id = 1
        expected_url = 'google.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id)

        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        assert monitor.email_sender.send_args['url'] == expected_url

    def test_send_alerts_for_id_1_under_alert_count_msg_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, num_of_times = 1)

        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        assert monitor.email_sender.send_called 

    def test_send_alerts_for_id_1_alert_count_incremented_and_commited(self):
        uri_check_id = 1
        expected_url = 'google.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id,
                                             num_of_times = 2,
                                             num_of_times_alerted=0)

        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        self.assertEquals(self.cur_session.query(Alert).all()[0].num_of_times_alerted, 1)

    def test_send_alerts_for_id_1_reaches_message_count_stop_is_set_on_alert(self):
        uri_check_id = 1
        expected_url = 'google.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, 
                                             num_of_times = 1, 
                                             num_of_times_alerted = 0)

        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        assert self.cur_session.query(Alert).one().stop

    def test_send_alerts_for_id_1_over_alert_count_msg_not_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id,
                                             num_of_times = 1,
                                             num_of_times_alerted = 2)

        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        assert not monitor.email_sender.send_called 

    def test_send_alerts_for_id_1_unlimited_alerts_msg_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'

        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id,
                                           num_of_times = EmailAlert.NO_LIMIT,
                                           num_of_times_alerted = 2)

        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        assert monitor.email_sender.send_called

class SiteTests(DbTest):
    def setup_for_test(self):
        self._site = create_app()
        self._site.config['TESTING'] = True
        self.app = self._site.test_client()

        #Patch out urlopen
        self.fake_url_reader = FakeUrlReader()
        self.patched_openurl = urllib2.urlopen

        urllib2.urlopen = self.fake_url_reader.open

    def clean_up_after_test(self):
        urllib2.urlopen = self.patched_openurl
        daemonAlertMe.models.Session.remove()

    def test_index_no_entries_empty_message_shown(self):
        res = self.app.get('/') 
        assert "Sorry, we're empty at the moment!" in res.data

    def test_index_entries_both_urls_shown(self):
        expected_url1 = 'google.com'
        self.add_with_one_uri_check_with_id_and_no_alerts(aid = 0,
                                                          url = expected_url1)

        expected_url2 = 'knvrt.me'
        self.add_with_one_uri_check_with_id_and_no_alerts(aid = 1,
                                                          url = expected_url2)

        res = self.app.get('/') 

        assert 'href="' + expected_url1 + '"' in res.data
        assert 'href="' + expected_url2 + '"' in res.data

    def test_add_1_entry_added_database(self):
        expected_url = 'http://test'
        expected_email = 'test@domain.com'
        expected_alert_times = 1

        self.app.post('/add', data=dict(Url=expected_url,
                                        Email=expected_email,
                                        AlertTimes=expected_alert_times))

        checks_in_db = self.cur_session.query(UriCheck).all()
        alerts_in_db = self.cur_session.query(Alert).all()

        assert checks_in_db[0].url == expected_url
        assert alerts_in_db[0].target == expected_email
        assert alerts_in_db[0].check_id == checks_in_db[0].check_id
        assert alerts_in_db[0].num_of_times == expected_alert_times

    def test_add_1_entry_no_http_at_start_add_when_inserted(self):
        expected_url = 'test'

        self.app.post('/add', data=dict(Url=expected_url,
                                        Email='test@domain.com',
                                        AlertTimes=1)) 

        checks_in_db = self.cur_session.query(UriCheck).all()
        assert checks_in_db[0].url == 'http://' + expected_url

    def test_add_1_entry_starts_with_https_no_http_prepensws(self):
        expected_url = 'https://test'

        self.app.post('/add', data=dict(Url=expected_url, 
                                        Email='test@domain.com',
                                        AlertTimes=1)) 

        checks_in_db = self.cur_session.query(UriCheck).all()
        assert checks_in_db[0].url == expected_url

    def test_add_1_entry_added_redirect_back_to_home_page(self):
        res = self.app.post('/add', data=dict(Url='http://tart',
                                              Email='test@domain.com',
                                              AlertTimes=1))
        assert res.status_code == 302

    def test_add_1_entry_added_uri_already_exists_only_alert_created(self):
        test_url = 'http://tart'
        self.add_with_one_uri_check_with_id_and_no_alerts(aid = 1,
                                                          url = test_url)

        self.app.post('/add', data=dict(Url=test_url,
                                        Email='test@domain.com',
                                        AlertTimes=1))

        assert self.cur_session.query(UriCheck).count() == 1
