#!/usr/bin/python3

import gzip

def read(filename):
    '''
    Read a gnucash file, which could be gzipped, or not
    '''
    try:
        return gzip.open(filename, 'r').read()
    except OSError:
        return open(filename, 'r').read()

def get(element, name):
    try:
        return element.getElementsByTagName(name)[0].firstChild.data
    except IndexError:
        return None
