#!/usr/bin/python3

import argparse
import os
from xml.dom import minidom
import urllib
from urllib import request

import util

def main():
    parser = argparse.ArgumentParser(description='Check whether all attached files are found')
    parser.add_argument('gnucash_file')
    parser.add_argument('base_path')
    args = parser.parse_args()

    doc = minidom.parseString(util.read(args.gnucash_file))

    slot_values = doc.getElementsByTagName('slot')

    file_count = 0
    error_count = 0
    for x in slot_values:
        slot_key = x.getElementsByTagName('slot:key')[0].firstChild.data

        if slot_key == 'assoc_uri':
            file_count += 1

            rel_path = request.url2pathname(
                urllib.parse.urlparse(
                    x.getElementsByTagName('slot:value')[0].firstChild.data).path)
            full_path = os.path.join(args.base_path, rel_path)

            if not os.path.exists(full_path):
                error_count += 1
                print("Failed to find {}...".format(full_path))

    print("found {} errors in {} files!".format(error_count, file_count))

if __name__ == "__main__":
    main()
