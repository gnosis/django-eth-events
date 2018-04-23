import os
from distutils.util import convert_path

from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


def read_version():
    main_ns = {}
    ver_path = convert_path('django_eth_events/version.py')
    with open(ver_path) as ver_file:
        exec(ver_file.read(), main_ns)
    return main_ns['__version__']


version = read_version()

requirements = [
    "celery>=4.1.0",
    "Django>=2.0.0",
    "django-solo>=1.1.3",
    "eth-abi>=1.0.0",
    "eth-utils>=1.0.2",
    "ethereum>=1.6.1<2.0.0",
    "kombu==4.1.0",
    "web3>=4",
]

setup(
    name='django-eth-events',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    license='MIT License',
    description='A simple Django app to react to Ethereum events.',
    url='https://github.com/gnosis/django-eth-events',
    author='Gnosis',
    author_email='dev@gnosis.pm',
    keywords=['ethereum', 'gnosis'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    data_files=[("", ["LICENSE"])],
)
