import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-ether-logs',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    # license='BSD License',  # example license
    description='A simple Django app to react to ethereum logs.',
    # long_description=README,
    url='https://github.com/gnosis/dj-ether-logs',
    author='Gnosis',
    author_email='dev@gnosis.pm',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers'
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
