import unittest
import urllib2
from daemonAlertMe import HashCheck, init_engine, UriCheck, Alert, UriMonitor
from sqlalchemy.orm import sessionmaker 

class FakeUrlReader():
    def __init__(self, page = None):
        self.page = page
        self.called_open = False
        self.open_call_count = 0
    def read(self):
        return self.page
    
    def open(self, url, data = None, proxies = None):
        self.called_open = True
        self.opened_url = url
        return self.page

class HashCheckTests(unittest.TestCase):
    def test_has_changes_hashTheSame_NoChange(self):
        check = HashCheck('71860c77c6745379b0d44304d66b6a13') #MD5 of the word page
        url_reader_fake = FakeUrlReader('page')
        
        self.assertFalse(check.has_changes(url_reader_fake))
        
    def test_has_changes_hashDifferentSame_ReturnsTrue(self):
        check = HashCheck('')
        url_reader_fake = FakeUrlReader('page')
        
        self.assertTrue(check.has_changes(url_reader_fake))

class UriMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._engine = init_engine('sqlite:///:memory:')
        cls.Session = sessionmaker(autocommit=True,
                                   autoflush=True,
                                   bind=cls._engine)
        
    def setUp(self):
        self.cur_session = self.Session()
    
    def tearDown(self):
        self.cur_session.connection().execute("DELETE FROM " + UriCheck.__tablename__)
        self.cur_session.connection().execute("DELETE FROM " + Alert.__tablename__)
        
        
    def test_run_all_1_check_no_alerts_no_url_opened(self):
        self.setup_with_one_uri_check_with_id1_and_no_alerts()
        fake_url_reader = FakeUrlReader()
        urllib2.openurl = fake_url_reader.open
        monitor = UriMonitor(self.cur_session)
        monitor.run_all()
        
        self.assertFalse(fake_url_reader.called_open)
        
    def test_run_all_1_check_with_alert_url_opened(self):
        self.setup_with_one_uri_check_with_id1_and_no_alerts()
        self.add_alert_for_uri_check_1_with_url_googlecom()
        
        fake_url_reader = FakeUrlReader()
        
        urllib2.urlopen = fake_url_reader.open
        
        monitor = UriMonitor(self.cur_session)
        monitor.run_all()
        
        self.assertTrue(fake_url_reader.called_open)
        self.assertEquals('google.com', fake_url_reader.opened_url)
        
    def setup_with_one_uri_check_with_id1_and_no_alerts(self):
        uri_check = UriCheck()
        uri_check.id = 1
        uri_check.check_options = ''
        uri_check.url = 'google.com'
        self.cur_session.add(uri_check)
    
    def add_alert_for_uri_check_1_with_url_googlecom(self):
        alert = Alert()
        alert.check_id = 1
        self.cur_session.add(alert)
