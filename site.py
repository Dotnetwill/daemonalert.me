from flask import Flask, render_template, redirect, request
from daemonAlertMe import get_session, UriCheck, Alert

app = Flask(__name__)



@app.teardown_request
def shutdown_session(exception=None):
    app.db.remove()

@app.route('/')
def index():
    checks = app.db.query(UriCheck).all()
    return render_template('index.html', checks = checks)

@app.route('/add', methods=['POST'])
def add_alert():
    check = create_or_get_uri_check(app.db, request.form['Url'])
    
    alert = Alert()
    alert.check_id = check.id
    alert.check = check
    alert.email = request.form['Email']
    alert.num_of_times = request.form['AlertTimes']
    app.db.add(alert)
    
    app.db.flush()
    
    return redirect('/')
def create_or_get_uri_check(db, url):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    
    found_checks = db.query(UriCheck).filter(UriCheck.url == url)
    if found_checks.count() > 0:
        return found_checks[0]
    else:
        check = UriCheck()    
        check.url = url 
        return check
    
if __name__ == '__main__':
    app.db = get_session()
    app.run(debug=True)
