#!/usr/bin/python3

import argparse
import datetime
import regex
from xml.dom import minidom

import util

def amount(amount_string):
    # e.g. 12345/100
    match = amount_string.split('/')
    return float(match[0]) / float(match[1])

def main():
    parser = argparse.ArgumentParser(description='Balance assertions for GnuCash')
    parser.add_argument('gnucash_file')
    parser.add_argument('assertion_regex')
    parser.add_argument('-d', type=int, default=2, help='number of decimal places for comparison')
    args = parser.parse_args()

    doc = minidom.parseString(util.read(args.gnucash_file))

    assert doc.getElementsByTagName('gnc:book')[0].attributes['version'].value == '2.0.0'

    accounts = doc.getElementsByTagName('gnc:account')

    # build a mapping from account name to account id
    act_name_to_id_map = [(util.get(x, 'act:name').data, util.get(x, 'act:id').data) for x in accounts]

    class Transaction:
        def __init__(self, element):
            self.element = element

        def is_valid(self):
            if util.get(self.element, 'trn:description') is None:
                return False

            return True

        def date(self):
            assert self.is_valid()

            date_str = self.element.getElementsByTagName('trn:date-posted')[0].\
                getElementsByTagName('ts:date')[0].firstChild.data

            return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        def desc(self):
            assert self.is_valid()

            return util.get(self.element, 'trn:description').data

        def get_splits(self):
            assert self.is_valid()

            splits = self.element.getElementsByTagName('trn:split')
            return [(util.get(x, 'split:account').data, util.get(x, 'split:value').data) for x in splits]

    error_count = 0
    assertions_count = 0
    for act_name, act_id in act_name_to_id_map:
        transactions = []
        for transaction_element in doc.getElementsByTagName('gnc:transaction'):
            trn = Transaction(transaction_element)

            if trn.is_valid():
                transactions += [(x[0], x[1], trn.date(), trn.desc()) for x in trn.get_splits() if x[0] == act_id]

        # now find balance assertions in the list of transactions
        assertions = [x for x in transactions if regex.search(args.assertion_regex, x[3])]
        assertions.sort(key = lambda x : x[2])

        print("found {} assertions in account '{}' ({})".format(len(assertions), act_name, act_id))
        assertions_count += len(assertions)
        for assertion in assertions:
            assertion_amount = float(regex.search(args.assertion_regex, assertion[3]).group(0))
            assertion_date = assertion[2]
            actual_amount = round(sum([amount(x[1]) for x in transactions if x[2] <= assertion_date]), args.d)

            error = True if abs(actual_amount - assertion_amount) > 0 else False
            error_count += int(error)
            description = "    {}: checking value {} against balance of {}...{}".format(
                assertion_date,
                assertion_amount,
                actual_amount,
                "ERROR" if error else "OK")

            print(description)

    print("found {} errors in {} assertions!".format(error_count, assertions_count))

if __name__ == "__main__":
    main()
