import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker 
from daemonAlertMe import HashCheck, Base

class fake_url_reader():
    def __init__(self, page):
        self.page = page
    
    def read(self):
        return self.page

class HashCheckTests(unittest.TestCase):
    def test_has_changes_hashTheSame_NoChange(self):
        check = HashCheck('71860c77c6745379b0d44304d66b6a13') #MD5 of the word page
        url_reader_fake = fake_url_reader('page')
        
        self.assertFalse(check.has_changes(url_reader_fake))
        
    def test_has_changes_hashDifferentSame_ReturnsTrue(self):
        check = HashCheck('')
        url_reader_fake = fake_url_reader('page')
        
        self.assertTrue(check.has_changes(url_reader_fake))

class UriMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._engine = create_engine('sqlite:///./site.db')
        Base.metadata.create_all(cls._engine)
        cls._db_session = scoped_session(sessionmaker(autocommit=True,
                                         autoflush=True,
                                         bind=cls._engine))
        