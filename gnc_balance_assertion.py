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
            split_element):

            account = util.get(split_element, 'split:account')
            value = util.get(split_element, 'split:value')
            memo = util.get(split_element, 'split:memo')
            id = util.get(split_element, 'split:id')

            self.transaction = parent_transaction
            self.account = account
            amount_match = value.split('/')
            self.amount = float(amount_match[0]) / float(amount_match[1])

            assertion_desc_match = regex.search(
                '(' + args.assertion_regex + ')',
                self.transaction.desc)

            assertion_memo_match = regex.search(
                '(' + args.assertion_regex + ')',
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
            assert util.get(element, 'trn:description') is not None

            date_str = element.getElementsByTagName('trn:date-posted')[0].\
                getElementsByTagName('ts:date')[0].firstChild.data

            self.date = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            self.desc = util.get(element, 'trn:description')

            split_elements = element.getElementsByTagName('trn:split')
            self.splits = [Split(self, x) for x in split_elements]

    error_count = 0
    assertions_count = 0

    all_splits = []
    for transaction_element in doc.getElementsByTagName('gnc:transaction'):
        trn = Transaction(transaction_element)
        all_splits += trn.splits

    comp = lambda s : s.transaction.date
    all_splits.sort(key=comp)

    for act_name, act_id in act_name_to_id_map:
        splits = [s for s in all_splits if s.account == act_id]

        # now find balance assertions in the list of transactions
        assertions = [s for s in splits if s.is_assertion()]

        print("found {} assertions in account '{}' ({})".format(len(assertions), act_name, act_id))
        assertions_count += len(assertions)

        balance = 0
        i = 0

        for assertion in assertions:

            for s in splits[i:]:

                if s.transaction.date <= assertion.transaction.date:
                    balance = round(balance + s.amount, args.d)
                    i += 1
                else:
                    break

            error = True if abs(balance - assertion.assertion_amount) > 0 else False
            error_count += int(error)
            description = "    {}: checking value {} against balance of {}...{}".format(
                assertion.transaction.desc,
                assertion.assertion_amount,
                balance,
                "ERROR" if error else "OK")

            print(description)

    print("found {} errors in {} assertions!".format(error_count, assertions_count))

if __name__ == "__main__":
    main()
