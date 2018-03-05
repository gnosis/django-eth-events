class UnknownBlockReorgException(Exception):
    pass


class NoBackupException(Exception):
    def __init__(self, message, errors):
        super(NoBackupException, self).__init__(message)

        # Now for your custom code...
        self.errors = errors


class Web3ConnectionException(Exception):
    pass


class UnknownBlock(Exception):
    pass


class UnknownTransaction(Exception):
    pass
