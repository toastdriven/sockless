#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup


setup(
    name='sockless',
    version='0.9.1',
    description='A nicer API around sockets.',
    author='Daniel Lindsley',
    author_email='daniel@toastdriven.com',
    url='http://github.com/toastdriven/sockless/',
    long_description=open('README.rst', 'r').read(),
    py_modules=[
        'sockless',
    ],
    tests_require=[
        'mock',
    ],
    license='BSD',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        # 'Programming Language :: Python :: 3',
        'Topic :: Internet',
        'Topic :: System :: Networking',
    ],
)
