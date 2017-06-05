import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


requirements = [
    'six',
    'bitcoin==1.1.42',
    'celery==3.1.25',
    'django==1.10.5',
    'django-authtools==1.5.0',
    'django-celery==3.2.1',
    'django-model-utils==2.6.1',
    'django-solo==1.1.2',
    'ethereum==1.6.0',
    'ethereum-abi-utils==0.4.0',
    'ethereum-utils==0.2.0',
    'factory-boy==2.5.2',
    'web3==3.7.1',
    'kombu==3.0.37'
]

setup(
    name='django-ether-logs',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
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
