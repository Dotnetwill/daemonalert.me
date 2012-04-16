from daemonAlertMe.site import create_app

if __name__ == '__main__':
    app = create_app()
    app.config['TRAP_BAD_REQUEST_ERRORS'] = True
    app.run(host='0.0.0.0',debug=True)
