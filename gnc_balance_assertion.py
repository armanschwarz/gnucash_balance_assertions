#!/usr/bin/python3

import argparse
import datetime
import regex
from xml.dom import minidom

import util

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
    act_name_to_id_map = [(util.get(x, 'act:name'), util.get(x, 'act:id')) for x in accounts]

    class Split:
        def __init__(
            self,
            parent_transaction,
            account,
            value,
            memo):

            self.transaction = parent_transaction
            self.account = account
            amount_match = value.split('/')
            self.amount = float(amount_match[0]) / float(amount_match[1])

            assertion_desc_match = regex.search(
                args.assertion_regex,
                self.transaction.desc())

            assertion_memo_match = regex.search(
                args.assertion_regex,
                memo if memo else '')

            assert not bool(assertion_desc_match) or not bool(assertion_memo_match)

            if assertion_desc_match:
                assertion_amount_string = assertion_desc_match.group(0)
            elif assertion_memo_match:
                assertion_amount_string = assertion_memo_match.group(0)
            else:
                assertion_amount_string = None

            if assertion_amount_string:
                self.assertion_amount = float(assertion_amount_string)
            else:
                self.assertion_amount = None

        def is_assertion(self):
            return bool(self.assertion_amount)

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

            return util.get(self.element, 'trn:description')

        def get_splits(self):
            assert self.is_valid()

            elements = self.element.getElementsByTagName('trn:split')
            return [Split(self, util.get(x, 'split:account'), util.get(x, 'split:value'), util.get(x, 'split:memo')) for x in elements]

    error_count = 0
    assertions_count = 0
    for act_name, act_id in act_name_to_id_map:
        splits = []
        for transaction_element in doc.getElementsByTagName('gnc:transaction'):
            trn = Transaction(transaction_element)

            if trn.is_valid():
                splits += [s for s in trn.get_splits() if s.account == act_id]

        # now find balance assertions in the list of transactions
        assertions = [s for s in splits if s.is_assertion()]
        assertions.sort(key = lambda s : s.transaction.date())

        print("found {} assertions in account '{}' ({})".format(len(assertions), act_name, act_id))
        assertions_count += len(assertions)
        for assertion in assertions:
            actual_amount = round(
                sum([s.amount for s in splits if s.transaction.date() <= assertion.transaction.date()]),
                args.d)

            error = True if abs(actual_amount - assertion.assertion_amount) > 0 else False
            error_count += int(error)
            description = "    {}: checking value {} against balance of {}...{}".format(
                assertion.transaction.desc(),
                assertion.assertion_amount,
                actual_amount,
                "ERROR" if error else "OK")

            print(description)

    print("found {} errors in {} assertions!".format(error_count, assertions_count))

if __name__ == "__main__":
    main()
