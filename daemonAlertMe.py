from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
import hashlib
import datetime

Base = declarative_base()

class UriCheck(Base):
    __tablename__ = 'UriChecks'
    
    id = Column(Integer, primary_key=True)
    url = Column(String)
    check_type = Column(String)
    check_options = Column(String)
    last_check = Column(DateTime, default=datetime.datetime.now)
    
class Alert(Base):
    __tablename__ = 'Alerts'
    
    id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('UriCheck.id'))
    check = relationship('UriCheck')
    email = Column(String)
    num_of_times = Column(Integer)
    num_of_times_alerted = Column(Integer)
    stop = Column(Boolean) 

def create_database():
    engine = create_engine('sqlite:///./site.db')
    Base.metadata.create_all(engine)
    db_session = scoped_session(sessionmaker(autocommit=True,
                                         autoflush=True,
                                         bind=engine))
    return db_session

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
        pass
    
    
