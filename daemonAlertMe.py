from sqlalchemy import create_engine, Column, Integer, Unicode, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
import urllib2
import hashlib
import datetime

Base = declarative_base()

class UriCheck(Base):
    __tablename__ = 'UriChecks'
    
    id = Column(Integer, primary_key=True)
    url = Column(Unicode)
    check_type = Column(Unicode)
    check_options = Column(Unicode)
    last_check = Column(DateTime, default=datetime.datetime.now)
    
class Alert(Base):
    __tablename__ = 'Alerts'
    
    id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('UriChecks.id'))
    check = relationship('UriCheck')
    email = Column(Unicode)
    num_of_times = Column(Integer)
    num_of_times_alerted = Column(Integer)
    stop = Column(Boolean) 


class HashCheck():
    def __init__(self, checkOptions):
        self.check_options = checkOptions
    
    def has_changes(self, url_stream):
        page = url_stream.read()
        hash = hashlib.md5(page).hexdigest()
        return hash != self.check_options
    
class UriMonitor():
    def __init__(self, dbsession):
        self.db_session = dbsession
        
    def run_all(self):
        checks_to_run = self.db_session.query(UriCheck).from_statement("SELECT UriChecks.id, url, check_type, check_options, last_check FROM UriChecks JOIN Alerts AS a ON UriChecks.id = a.check_id").all()
        for check in checks_to_run:
            hash_check = HashCheck(check.check_options)
            url_stream = urllib2.urlopen(check.url)
            
def init_engine(connection_string):
    engine = create_engine(connection_string,  echo=True)
    Base.metadata.create_all(engine)
    return engine
    
