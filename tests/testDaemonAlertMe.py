import unittest
from daemonAlertMe import HashCheck

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
