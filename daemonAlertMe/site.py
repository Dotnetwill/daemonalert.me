from flask import Flask, render_template, redirect, request, url_for, g,\
                  flash, make_response
from daemonAlertMe.models import UriCheck, Alert, init_model 
from daemonAlertMe.monitor import HashCheck, TwitterAlert
from daemonAlertMe import config, log
from sqlalchemy.orm.exc import NoResultFound
import urllib2
import daemonAlertMe.models

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

def create_app():
    init_model()
    return app

@app.before_request
def start_request():
    g.db = daemonAlertMe.models.Session()

@app.teardown_request
def shutdown_session(exception=None):
    g.db.flush()
    daemonAlertMe.models.Session.remove()

    if not exception is None:
        log.error(u"Request exceptioned out %s: " % exception)

@app.route('/')
def index():
    checks = g.db.query(UriCheck).all()
    email = request.args.get('Email')
    if email is None and 'email' in request.cookies:
        email = request.cookies['email']
    else:
        email = ''

    return render_template('index.html', checks = checks, 
            url=request.args.get('Url', ''), email = email)

@app.route('/add', methods=['POST'])
def add_check_and_alert():
    check = create_or_get_uri_check(g.db, request.form['Url'])

    if check == None:
        flash('Invalid Url', 'error')
        return redirect(url_for('index', Url=request.form['Url'], 
          Email=request.form['Email'], AlertTimes=request.form['AlertTimes']))

    alert = Alert()
    alert.check_id = check.check_id
    alert.check = check
    alert.target = request.form['Email']
    alert.num_of_times = request.form['AlertTimes']
    alert.alert_type = get_alert_type(request.form['Email'])

    g.db.add(alert)

    flash('Created Alert!', 'success')

    res = make_response(redirect(url_for('index')))
    res.set_cookie('email', request.form['Email'])

    return res

def get_alert_type(target):
    EMAIL_REGEX = """^([0-9a-zA-Z]([-.\w]*[0-9a-zA-Z])*@([0-9a-zA-Z][-\w]*[0-9a-zA-Z]\.)+[a-zA-Z]{2,9})"""
    import re
    if re.match(EMAIL_REGEX, target):
        return u"email"

    return TwitterAlert.ALERT_TYPE

@app.route('/continue/<uid>', methods=['GET'])
def continue_email(uid):
    try:
        alert = g.db.query(Alert).filter(Alert.alert_id == uid).one()
        alert.num_of_times_alerted = 0
        alert.num_of_times = 1
        alert.stop = False
        flash('We\'ll let you know the next time it changes!')
    except NoResultFound:
        flash('No alert found')

    return redirect('index')

@app.route('/delete-alert/<uid>', methods=['GET'])
def delete_alert(uid):
    try:
        alert = g.db.query(Alert).filter(Alert.alert_id == uid, 
                                         Alert.stop==False)\
                 .one()
        alert.stop = True
        flash('Alert deleted!', 'success')
    except NoResultFound:
        flash('No such alert', 'error')

    return redirect(url_for('index'))

def create_or_get_uri_check(db, url):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    
    try:
        found_check = db.query(UriCheck).filter(UriCheck.url == url).one()
        return found_check
    except NoResultFound:
        #Url is not being monitored, ignore the error and create it
        pass

    check = UriCheck()
    check.url = url 
    check.check_options 

    first_monitor = HashCheck(check)
    try:
        url_stream = urllib2.urlopen(check.url)
        first_monitor.has_changes(url_stream)
    except urllib2.URLError, e:
        if not isinstance(e, urllib2.HTTPError):
            log.error(e.reason)
            return None
    return check

