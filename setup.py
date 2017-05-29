import os
from setuptools import find_packages, setup

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='dj-ether-logs',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    #license='BSD License',  # example license
    description='A simple Django app to react to ethereum logs.',
    #long_description=README,
    url='https://github.com/gnosis/dj-ether-logs',
    author='Gnosis',
    author_email='dev@gnosis.pm',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        #'Framework :: Django :: X.Y',  # replace "X.Y" as appropriate
        'Intended Audience :: Developers',
        #'License :: OSI Approved :: BSD License',  # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        #'Programming Language :: Python :: 3',
        #'Programming Language :: Python :: 3.4',
        #'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)

