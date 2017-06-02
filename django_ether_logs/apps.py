from __future__ import unicode_literals

from django.apps import AppConfig
from django.conf import settings


class EtherLogsConfig(AppConfig):
    name = 'django_ether_logs'

    def ready(self):
        super(EtherLogsConfig, self).ready()
        self.__load_config()

    def __load_config(self):
        """Loads the base config and merges it with the Django app configuration"""
        filez = self.__load_file('django_ether_logs.settings.base')
        variables = [x for x in dir(filez) if x.isupper() and 'DJ_' in x]
        default_config = {}
        # set default config values
        for var in variables:
            if not hasattr(settings, var) and var == 'DJ_ADDITIONAL_APPS':
                inst_apps = getattr(settings, 'INSTALLED_APPS')
                setattr(settings, 'INSTALLED_APPS', inst_apps + filez.__dict__[var])
            elif not hasattr(settings, var):
                setattr(settings, var[3::], filez.__dict__[var])

    def __load_file(self, import_name, silent=False):
        """Imports an object based on a string.  This is useful if you want to
        use import paths as endpoints or something similar.  An import path can
        be specified either in dotted notation (``xml.sax.saxutils.escape``)
        or with a colon as object delimiter (``xml.sax.saxutils:escape``).
        If `silent` is True the return value will be `None` if the import fails.
        :param import_name: the dotted name for the object to import.
        :param silent: if set to `True` import errors are ignored and
                       `None` is returned instead.
        :return: imported object
        """
        # force the import name to automatically convert to strings
        # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        import_name = str(import_name).replace(':', '.')
        try:
            try:
                __import__(import_name)
            except ImportError:
                if '.' not in import_name:
                    raise
            else:
                return sys.modules[import_name]
            module_name, obj_name = import_name.rsplit('.', 1)
            try:
                module = __import__(module_name, None, None, [obj_name])
            except ImportError:
                # support importing modules not yet set up by the parent module
                # (or package for that matter)
                module = self.__load_file(module_name)
            try:
                return getattr(module, obj_name)
            except AttributeError as e:
                raise ImportError(e)
        except ImportError as e:
            if not silent:
                raise Exception(sys.exc_info()[1])

