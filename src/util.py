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
        first_child = element.getElementsByTagName(name)[0].firstChild
    except IndexError:
        return None

    if first_child is None:
        return None

    return first_child.data
