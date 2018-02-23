class NetworkReorgException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class UnknownBlockReorgException(Exception):
    pass


class NoBackupException(Exception):
    def __init__(self, message, errors):
        super(NoBackupException, self).__init__(message)

        # Now for your custom code...
        self.errors = errors


class Web3ConnectionError(Exception):
    pass


class UnknownBlock(Exception):
    pass


class UnknownTransaction(Exception):
    pass