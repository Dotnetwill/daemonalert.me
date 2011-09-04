import unittest
import urllib2
import daemonAlertMe
import smtplib
from daemonAlertMe import HashCheck, init_engine, UriCheck, Alert, UriMonitor, EmailAlert
from sqlalchemy.orm import sessionmaker , scoped_session
import site

class FakeSMTP():
    instance = None
    def __init__(self, server_name):
        FakeSMTP.instance = self
        self.sendmail_called = False
        self.target_email_sent_to = None
        self.sent_email = None
        
    def sendmail(self, server, target_email, email):
        self.sendmail_called = True
        self.target_email_sent_to = target_email
        self.sent_email = email
        
    def __getattr__(self, name):
        return lambda a = None, b = None: False

class FakeAlerter():
    def __init__(self):
        self.alert_called = False
        
    def send_alerts_for_id(self, check_id, url):
        self.alert_called = True
        self.alert_for_id = check_id
        self.alert_url = url
            
class FakeCheck():
    last_instance = None
    change_return_value = False
    def __init__(self, checkOptions):
        FakeCheck.last_instance = self
        self.has_changes_called = False
    
    def has_changes(self, url_stream):
        self.has_changes_called = True
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
    md_hash_page = '71860c77c6745379b0d44304d66b6a13' #MD5 of the word page
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
        
class DbInMemoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._engine = init_engine('sqlite:///:memory:')
        cls.Session = sessionmaker(autocommit=True,
                                   autoflush=True,
                                   bind=cls._engine)
        
    def setUp(self):
        self.cur_session = self.Session()
        self.setup_for_test()
        
    def tearDown(self):
        self.cur_session.connection().execute("DELETE FROM " + UriCheck.__tablename__)
        self.cur_session.connection().execute("DELETE FROM " + Alert.__tablename__)
        self.clean_up_after_test()
        
    def add_with_one_uri_check_with_id_and_no_alerts(self, id = 1, url='google.com'):
        uri_check = UriCheck()
        uri_check.id = id
        uri_check.check_options = ''
        uri_check.url = url
        self.cur_session.add(uri_check)
    
    def add_alert_for_uri_check_with_id(self, uri_check_id=1, target_email='test@test.com', num_of_times = 1, num_of_times_alerted=0):
        alert = Alert()
        alert.check_id = uri_check_id
        alert.email = target_email
        alert.num_of_times = num_of_times
        alert.num_of_times_alerted = num_of_times_alerted
        self.cur_session.add(alert)

class UriMonitorTests(DbInMemoryTest):
    def setup_for_test(self):
        #Fale alerter
        self.alerter = FakeAlerter()
        
        #The class under test
        self.monitor = UriMonitor(self.cur_session, self.alerter)
        
        #Patch out urlopen
        self.fake_url_reader = FakeUrlReader()
        self.patched_openurl = urllib2.urlopen
        
        urllib2.urlopen = self.fake_url_reader.open
        
        #patch out hashcheck class
        self.old_hash_check = daemonAlertMe.HashCheck
        daemonAlertMe.HashCheck = FakeCheck
        
    def clean_up_after_test(self):
        #Restore hashcheck class
        daemonAlertMe.HashCheck = self.old_hash_check
        
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
        self.add_with_one_uri_check_with_id_and_no_alerts(id = 2, url=expected_url)
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
        self.add_with_one_uri_check_with_id_and_no_alerts(id = expected_check_id, url=expected_url)
        self.add_alert_for_uri_check_with_id(uri_check_id = expected_check_id)
        FakeCheck.change_return_value = True
        
        self.monitor.run_all()
        
        self.assertTrue(self.alerter.alert_called)
        self.assertEqual(self.alerter.alert_for_id, expected_check_id)
        self.assertEqual(self.alerter.alert_url, expected_url)
        
    def test_run_all_1_check_with_alert_check_no_changed_alert_not_sent(self):
        expected_check_id = 1
        expected_url = 'google.com'
        self.add_with_one_uri_check_with_id_and_no_alerts(id = expected_check_id, url=expected_url)
        self.add_alert_for_uri_check_with_id(uri_check_id = expected_check_id)
        FakeCheck.change_return_value = False
        
        self.monitor.run_all()
        
        self.assertFalse(self.alerter.alert_called)
   
class EmailAlertTests(DbInMemoryTest):
    def setup_for_test(self):
        self.email_alert = EmailAlert(self.cur_session)
        self.patched_out_smtp_lib = smtplib.SMTP
        smtplib.SMTP = FakeSMTP
        
    def clean_up_after_test(self):
        smtplib.SMTP = self.patched_out_smtp_lib
        FakeSMTP.instance = None
        
    def test_send_alerts_for_id_no_alert_nothing_sent(self):
        uri_check_id = 1
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        
        self.email_alert.send_alerts_for_id(uri_check_id, '')

        self.assertIsNone(FakeSMTP.instance)
        
    def test_send_alerts_for_id_1_alert_msg_sent(self):
        uri_check_id = 1
        expected_target_email = 'target@test.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, expected_target_email)
        
        self.email_alert.send_alerts_for_id(uri_check_id, '')
        
        self.assertTrue(FakeSMTP.instance.sendmail_called)
        self.assertEqual(FakeSMTP.instance.target_email_sent_to, expected_target_email)
        
    def test_send_alerts_for_id_1_alert_msg_sent_with_url_in(self):
        uri_check_id = 1
        expected_url = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id)
        
        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)
        
        self.assertTrue(FakeSMTP.instance.sent_email.find(expected_url) > 1)
        
    def test_send_alerts_for_id_1_under_alert_count_msg_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, num_of_times = 1)
        
        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)
        
        self.assertTrue(FakeSMTP.instance.sendmail_called)
        
    def test_send_alerts_for_id_1_alert_count_incremented_and_commited(self):
        uri_check_id = 1
        expected_url = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, num_of_times = 1)
        
        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)
        
        self.assertEquals(self.cur_session.query(Alert).all()[0].num_of_times_alerted, 1)
        
    def test_send_alerts_for_id_1_at_alert_count_msg_not_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, num_of_times = 1, num_of_times_alerted = 1)
        
        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)

        self.assertIsNone(FakeSMTP.instance)
        
    def test_send_alerts_for_id_1_over_alert_count_msg_not_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, num_of_times = 1, num_of_times_alerted = 2)
        
        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)
        
        self.assertIsNone(FakeSMTP.instance)
        
    def test_send_alerts_for_id_1_unlimited_alerts_msg_sent(self):
        uri_check_id = 1
        expected_url = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(uri_check_id)
        self.add_alert_for_uri_check_with_id(uri_check_id, num_of_times = EmailAlert.NO_LIMIT, num_of_times_alerted = 2)
        
        self.email_alert.send_alerts_for_id(uri_check_id, expected_url)
        
        self.assertTrue(FakeSMTP.instance.sendmail_called)

class SiteTests(DbInMemoryTest):
    def setup_for_test(self):
        site.app.db = scoped_session(self.Session) 
        self.cur_session = site.app.db
        site.app.config['TESTING'] = True
        self.app = site.app.test_client()
        
    def clean_up_after_test(self):
        pass
    
    def test_index_no_entries_empty_message_shown(self):
        res = self.app.get('/') 
        assert "Sorry, we're empty at the moment!" in res.data
    
    def test_index_2_entries_both_urls_shown(self):
        expected_url1 = 'google.com'
        
        self.add_with_one_uri_check_with_id_and_no_alerts(id = 0, url = expected_url1)
        expected_url2 = 'knvrt.me'
        self.add_with_one_uri_check_with_id_and_no_alerts(id = 1, url = expected_url2)
         
        res = self.app.get('/') 
       
        assert '<a href="' + expected_url1 + '">' + expected_url1 + '</a>' in res.data
        assert '<a href="' + expected_url2 + '">' + expected_url2 + '</a>' in res.data
        
    def test_add_1_entry_added_database(self):
        expected_url = 'http://test'
        expected_email = 'test@domain.com'
        expected_alert_times = 1
        
        self.app.post('/add', data=dict(Url=expected_url, Email=expected_email, AlertTimes=expected_alert_times)) 
       
        checks_in_db = self.cur_session.query(UriCheck).all()
        alerts_in_db = self.cur_session.query(Alert).all()

        assert checks_in_db[0].url == expected_url
        assert alerts_in_db[0].email == expected_email
        assert alerts_in_db[0].check_id == checks_in_db[0].id 
        assert alerts_in_db[0].num_of_times == expected_alert_times
        
    def test_add_1_entry_no_http_at_start_add_when_inserted(self):
        expected_url = 'test'
      
        self.app.post('/add', data=dict(Url=expected_url, Email='test@domain.com', AlertTimes=1)) 
       
        checks_in_db = self.cur_session.query(UriCheck).all()
        assert checks_in_db[0].url == 'http://' + expected_url
    
    def test_add_1_entry_starts_with_https_no_http_prepensws(self):
        expected_url = 'https://test'
      
        self.app.post('/add', data=dict(Url=expected_url, Email='test@domain.com', AlertTimes=1)) 
       
        checks_in_db = self.cur_session.query(UriCheck).all()
        assert checks_in_db[0].url == expected_url
        
    def test_add_1_entry_added_redirect_back_to_home_page(self):
        res = self.app.post('/add', data=dict(Url='http://tart', Email='test@domain.com', AlertTimes=1))
        assert res.status_code == 302 

    def test_add_1_entry_added_uri_already_exists_only_alert_created(self):
        test_url = 'http://tart'
        self.add_with_one_uri_check_with_id_and_no_alerts(id = 1, url = test_url)
       
        
        self.app.post('/add', data=dict(Url=test_url, Email='test@domain.com', AlertTimes=1))
        
        assert self.cur_session.query(UriCheck).count() == 1         