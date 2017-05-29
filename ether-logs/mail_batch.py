from utils import Singleton
from api.utils import send_email
from django.urls import reverse
from django.conf import settings


class MailBatch(Singleton):
    def __init__(self):
        super(MailBatch, self).__init__()
        self.users = {}

    def add_mail(self, mail, dapp_logs):
        if mail and dapp_logs:
            if not self.users.get(mail):
                self.users[mail] = {}

            self.users[mail].update(dapp_logs)

    def send_mail(self):
        # copy users, reset the param (it allows to get more block while emails are sent)
        user_emails = self.users.copy()
        self.users = {}

        try:
            complete_url = settings.SERVER_HOST
            admin_url = reverse('api:admin')  # /api/alert/admin/

            if complete_url.endswith('/'):
                complete_url += admin_url[1:]
            else:
                complete_url += admin_url

            complete_url += '?code='

            for mail, dapp_logs in user_emails.iteritems():
                # TODO support batch mail, reuse connection
                send_email('emails/alerts.html', {'etherscan_url': settings.ETHERSCAN_URL, 'dapps': dapp_logs, 'unsubscribe_url': complete_url}, mail)
                del user_emails[mail]
        except Exception:
            for mail, dapp_logs in user_emails.iteritems():
                if not self.users.get(mail):
                    self.users[mail] = {}
                self.users[mail].update(dapp_logs)