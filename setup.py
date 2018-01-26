import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

requirements = []

with open('requirements.txt', 'r') as f:
    requirements = [x for x in f.read().split('\n') if x != '']

setup(
    name='django-eth-events',
    version='1.0.28',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    description='A simple Django app to react to Ethereum events.',
    url='https://github.com/gnosis/django-eth-events',
    author='Gnosis',
    author_email='dev@gnosis.pm',
    keywords=['ethereum', 'gnosis'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
