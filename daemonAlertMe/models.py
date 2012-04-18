from sqlalchemy import create_engine, Column, Integer, Unicode, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
from . import config
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
    num_of_times_alerted = Column(Integer, nullable = False, default=0)
    stop = Column(Boolean, default=False) 

Session = None
    
def init_model():
    engine = create_engine(config.CONN_STRING,  echo=config.ECHO_SQL, pool_recycle=3600)
    Base.metadata.create_all(engine)
    global Session
    Session = scoped_session(sessionmaker(autocommit=True,
                                          autoflush=True,
                                          bind=engine))
