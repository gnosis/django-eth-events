import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


requirements = [
    "celery==4.1.0",
    "Django==1.11",
    "django-solo==1.1.3",
    "eth-abi==0.5.0",
    "eth-utils==0.7.4",
    "ethereum==1.6.1",
    "kombu==4.1.0",
    "six==1.11.0",
    "web3[tester]==3.16.4",
]

setup(
    name='django-eth-events',
    version='1.0.34',
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
