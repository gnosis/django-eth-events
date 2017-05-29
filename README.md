# Django Ethereum Log Watcher

Watch Ethereum logs and respond to them.

1. Add "eth-log-watch" to your INSTALLED_APPS
2. Run `python manage.py migrate`
3. Start the development server and visit the admin interface to specify contracts to watch.
4. Specify the callback to be executed on the monitored logs.
