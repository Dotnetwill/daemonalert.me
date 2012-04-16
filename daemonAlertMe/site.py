from flask import Flask, render_template, redirect, request, abort, g, flash
from daemonAlertMe.models import UriCheck, Alert, init_model 
from daemonAlertMe.monitor import HashCheck
from daemonAlertMe import config
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
    daemonAlertMe.models.Session.remove()

@app.route('/')
def index():
    checks = g.db.query(UriCheck).all()
    return render_template('index.html', checks = checks)

@app.route('/add', methods=['POST'])
def add_check_and_alert():
    check = create_or_get_uri_check(g.db, request.form['Url'])
    
    if check == None:
        abort(400)
    
    alert = Alert()
    alert.check_id = check.id
    alert.check = check
    alert.email = request.form['Email']
    alert.num_of_times = request.form['AlertTimes']
    g.db.add(alert)
    
    g.db.flush()
    flash('Created Alert!')

    return redirect('/')

@app.route('/add-alert/<uid>', methods=['GET']) 
def add_alert(uid):
    try:
        check = g.db.query(UriCheck).filter(UriCheck.id == uid).one()
    except:
        abort(400)

    return render_template('add_alert.html', check = check)

@app.route('/delete-alert/<uid>', methods=['GET'])
def delete_alert(uid):
    flash('Note implemented yet!')
    redirect('/')

def create_or_get_uri_check(db, url):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    
    found_checks = db.query(UriCheck).filter(UriCheck.url == url)
    if found_checks.count() > 0:
        return found_checks[0]
    else:
        check = UriCheck()    
        check.url = url 
        check.check_options 
        
        first_monitor = HashCheck(check)
        try:
            url_stream = urllib2.urlopen(check.url)
            first_monitor.has_changes(url_stream)
        except urllib2.URLError, e:
            print e.reason
            return None
        
        return check
    

