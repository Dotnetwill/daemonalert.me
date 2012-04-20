from sqlalchemy import create_engine, Column, Integer, Unicode, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
from . import config
import datetime

Base = declarative_base()

class UriCheck(Base):
    "Represents a URL to be monitored"
    __tablename__ = u"UriChecks"

    check_id = Column(Integer, primary_key=True)
    url = Column(Unicode, nullable=False)
    check_type = Column(Unicode)
    check_options = Column(Unicode)
    last_check = Column(DateTime, default=datetime.datetime.utcnow())

class Alert(Base):
    "Represents someone to be alerted when a url changes"
    __tablename__ = u"Alerts"

    alert_id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('UriChecks.check_id'))
    check = relationship('UriCheck')
    email = Column(Unicode, nullable=False)
    num_of_times = Column(Integer, nullable=False)
    num_of_times_alerted = Column(Integer, nullable = False, default=0)
    stop = Column(Boolean, default=False) 

class ChangeHistory(Base):
    "Takes a snapshot of the latests state of a url, so we can send out diffs"
    __tablename__ = u"ChangeHistory"

    change_id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('UriChecks.check_id'))
    check = relationship('UriCheck')
    snapshot = Column(Unicode, nullable=False)
    date_taken = Column(DateTime, default=datetime.datetime.utcnow(), 
                        nullable=False)

Session = None

def init_model():
    engine = create_engine(config.CONN_STRING,  echo=config.ECHO_SQL, pool_recycle=3600)
    Base.metadata.create_all(engine)
    global Session
    Session = scoped_session(sessionmaker(autocommit=True,
                                          autoflush=True,
                                          bind=engine))
