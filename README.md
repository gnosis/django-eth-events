# Django Ethereum Log Watcher

Watch Ethereum logs and respond to them.

1. Add "eth-log-watch" to your INSTALLED_APPS
2. Provide custom Alerts model (optional) and the callback to be executed on the monitored logs in settings.
3. Run `python manage.py migrate`.
4. Start the development server and visit the admin interface to specify contracts to watch.
5. Add the periodic cronjob.
