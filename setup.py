import os

from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


requirements = [
    "celery==4.1.0",
    "Django==2.0.3",
    "django-solo==1.1.3",
    "eth-abi==1.0.0",
    "eth-utils==1.0.1",
    "ethereum==1.6.1",
    "kombu==4.1.0",
    "web3==4.0.0b11",
]

setup(
    name='django-eth-events',
    version='2.0.7',
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
