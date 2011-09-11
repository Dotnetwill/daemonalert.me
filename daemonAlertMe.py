from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker , scoped_session
from sqlalchemy.ext.declarative import declarative_base
import hashlib
import datetime

engine = create_engine('sqlite:///./site.db')
Base = declarative_base()
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

class UriCheck(Base):
    __tablename__ = 'UriChecks'
    
    id = Column(Integer, primary_key=True)
    url = Column(String)
    check_type = Column(String)
    check_options = Column(String)
    last_check = Column(DateTime, default=datetime.datetime.now)
    

Base.metadata.create_all(engine)

class HashCheck():
    def __init__(self, checkOptions):
        self.check_options = checkOptions
    
    def has_changes(self, url_stream):
        page = url_stream.read()
        hash = hashlib.md5(page).hexdigest()
        return hash != self.check_options
    
def run_checks():
    pass
