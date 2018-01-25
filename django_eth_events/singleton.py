from abc import ABCMeta


class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            # In Python 3.4+ is not allowed to send args to __new__ if __init__
            # is defined
            # cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance


class SingletonABCMeta(ABCMeta):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonABCMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
