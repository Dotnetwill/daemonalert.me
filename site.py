from flask import Flask, render_template, redirect, request, abort
from daemonAlertMe import get_session, UriCheck, Alert, HashCheck
import urllib2

app = Flask(__name__)

def create_app():    
    app.db = get_session()
    return app

@app.teardown_request
def shutdown_session(exception=None):
    app.db.remove()

@app.route('/')
def index():
    checks = app.db.query(UriCheck).all()
    return render_template('index.html', checks = checks)

@app.route('/add', methods=['POST'])
def add_check_and_alert():
    check = create_or_get_uri_check(app.db, request.form['Url'])
    
    if check == None:
        abort(500)
    
    alert = Alert()
    alert.check_id = check.id
    alert.check = check
    alert.email = request.form['Email']
    alert.num_of_times = request.form['AlertTimes']
    app.db.add(alert)
    
    app.db.flush()
    
    return redirect('/')

@app.route('/add-alert/<id>')
def add_alert(id):
    check = app.db.query(UriCheck).filter(UriCheck.id == id).one()
    return render_template('add_alert.html', check = check)

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
    
if __name__ == '__main__':
    create_app()
    app.run(debug=True)
