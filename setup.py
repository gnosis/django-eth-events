import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


requirements = [
    "six==1.10.0",
    "bitcoin==1.1.42",
    "celery==4.1.0",
    "Django==1.11",
    "django-solo==1.1.2",
    "ethereum==1.6.1",
    "ethereum-abi-utils==0.4.0",
    "ethereum-utils==0.2.0",
    "kombu==4.1.0",
    "web3[tester]==3.7.1"
]

setup(
    name='django-eth-events',
    version='1.0.14',
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
