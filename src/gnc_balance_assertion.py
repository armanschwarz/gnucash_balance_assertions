#!/usr/bin/env python3

from xml.dom import minidom
import argparse
import datetime
import pandas
import re

import util

def main():
    parser = argparse.ArgumentParser(description='Balance assertions for GnuCash')
    parser.add_argument('gnucash_file')
    parser.add_argument('--assertion_amount_regex')
    parser.add_argument('--assertion_start_regex', default=None)
    # parser.add_argument('-d', type=int, default=2, help='number of decimal places for comparison')
    args = parser.parse_args()

    print("parsing {}...".format(args.gnucash_file))
    doc = minidom.parseString(util.read(args.gnucash_file))

    assert doc.getElementsByTagName('gnc:book')[0].attributes['version'].value == '2.0.0'

    accounts = doc.getElementsByTagName('gnc:account')

    # build a mapping from account id to name and parent
    act_map = {util.get(x, 'act:id') : (util.get(x, 'act:name'), util.get(x, 'act:parent')) for x in accounts}

    class Split:
        def __init__(
            self,
            parent_transaction,
            split_element):

            account = util.get(split_element, 'split:account')
            value = util.get(split_element, 'split:value')
            id = util.get(split_element, 'split:id')

            self.transaction = parent_transaction
            self.account = account
            amount_match = value.split('/')

            numerator = float(amount_match[0])
            denominator = float(amount_match[1])
            self.decimal_places = amount_match[1].count('0')
            self.amount = round(numerator / denominator, self.decimal_places)

            assertion_desc_match = re.search(
                '(' + args.assertion_amount_regex + ')',
                self.transaction.desc)

            if assertion_desc_match:
                assertion_amount_string = assertion_desc_match.group(0)
                self.assertion_amount = float(assertion_amount_string)
            else:
                self.assertion_amount = None
                return # don't bother with the rest

            self.assertion_start = pandas.to_datetime('1900-01-01')

            if args.assertion_start_regex is not None:
                assertion_start_match = re.search(
                    '(' + args.assertion_start_regex + ')',
                    self.transaction.desc)

                if assertion_start_match:
                    assertion_start_string = assertion_start_match.group(0)
                    self.assertion_start = pandas.to_datetime(assertion_start_string)

        def is_assertion(self):
            return self.assertion_amount is not None

    class Transaction:
        def __init__(self, element):
            date_str = element.getElementsByTagName('trn:date-posted')[0].\
                getElementsByTagName('ts:date')[0].firstChild.data

            self.date = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z').replace(tzinfo=None)
            self.desc = util.get(element, 'trn:description')
            if self.desc is None:
                self.desc = ''

            split_elements = element.getElementsByTagName('trn:split')
            self.splits = [Split(self, x) for x in split_elements]

    error_count = 0
    assertions_count = 0

    all_splits = []
    for transaction_element in doc.getElementsByTagName('gnc:transaction'):
        trn = Transaction(transaction_element)
        all_splits += trn.splits

    splits_df = pandas.DataFrame([(s.transaction.date, s.amount, s.account, s.decimal_places) for s in all_splits])
    splits_df.columns = ['Date', 'Amount', 'Account', 'DecimalPlaces']

    def get_long_name(act_id):
        name = act_map[act_id][0]
        parent = act_map[act_id][1]

        while parent is not None:
            name = act_map[parent][0] + ':' + name
            parent = act_map[parent][1]

        return name

    for act_id, (act_name, act_parent) in act_map.items():
        # now find balance assertions in the list of transactions
        assertions = [s for s in all_splits if s.account == act_id and s.is_assertion()]

        error_messages = []

        for assertion in assertions:
            splits_subset = splits_df[
                (splits_df.Date <= assertion.transaction.date) &
                (splits_df.Date >= assertion.assertion_start) &
                (splits_df.Account == act_id)]

            balance = round(
                splits_subset.Amount.sum(),
                splits_subset.DecimalPlaces.max())

            if abs(balance - assertion.assertion_amount) > 0:
                error_count += 1
                description = "\tERROR: Assertion of {} against balance of {} ({} - {})".format(
                    assertion.assertion_amount,
                    balance,
                    assertion.assertion_start.date(),
                    assertion.transaction.date.date())

                error_messages.append(description)

        if len(assertions):
            print("Found {} assertions and {} errors in: {}".format(
                len(assertions),
                len(error_messages),
                get_long_name(act_id)))

            for msg in error_messages:
                print(msg)

            assertions_count += len(assertions)

    print("found {} errors in {} assertions!".format(error_count, assertions_count))

if __name__ == "__main__":
    main()
