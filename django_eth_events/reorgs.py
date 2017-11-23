class NoBackup(Exception):
    def __init__(self, message, errors):
        super(NoBackup, self).__init__(message)

        # Now for your custom code...
        self.errors = errors


def check_reorg():
    pass