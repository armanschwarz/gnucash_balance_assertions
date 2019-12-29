#!/usr/bin/python3

from xml.dom import minidom
import argparse
import datetime
import pandas
import regex

import util

def main():
    parser = argparse.ArgumentParser(description='Balance assertions for GnuCash')
    parser.add_argument('gnucash_file')
    parser.add_argument('--assertion_amount_regex')
    parser.add_argument('--assertion_start_regex', default=None)
    # parser.add_argument('-d', type=int, default=2, help='number of decimal places for comparison')
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
            id = util.get(split_element, 'split:id')

            self.transaction = parent_transaction
            self.account = account
            amount_match = value.split('/')

            numerator = float(amount_match[0])
            denominator = float(amount_match[1])
            self.decimal_places = amount_match[1].count('0')
            self.amount = round(numerator / denominator, self.decimal_places)

            assertion_desc_match = regex.search(
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
                assertion_start_match = regex.search(
                    '(' + args.assertion_start_regex + ')',
                    self.transaction.desc)

                if assertion_start_match:
                    assertion_start_string = assertion_start_match.group(0)
                    self.assertion_start = pandas.to_datetime(assertion_amount_string)

        def is_assertion(self):
            return self.assertion_amount is not None

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

    splits_df = pandas.DataFrame([(s.transaction.date, s.amount, s.account, s.decimal_places) for s in all_splits])
    splits_df.columns = ['Date', 'Amount', 'Account', 'DecimalPlaces']

    for act_name, act_id in act_name_to_id_map:
        # now find balance assertions in the list of transactions
        assertions = [s for s in all_splits if s.account == act_id and s.is_assertion()]

        print("found {} assertions in account '{}' ({})".format(len(assertions), act_name, act_id))
        assertions_count += len(assertions)

        for assertion in assertions:
            splits_subset = splits_df[
                (splits_df.Date <= assertion.transaction.date) &
                (splits_df.Date >= assertion.assertion_start) &
                (splits_df.Account == act_id)]

            balance = round(
                splits_subset.Amount.sum(),
                splits_subset.DecimalPlaces.max())

            error = True if abs(balance - assertion.assertion_amount) > 0 else False
            error_count += int(error)
            description = "    {}: checking value {} against balance of {} (since {})...{}".format(
                assertion.transaction.desc,
                assertion.assertion_amount,
                balance,
                assertion.assertion_start,
                "ERROR" if error else "OK")

            print(description)

    print("found {} errors in {} assertions!".format(error_count, assertions_count))

if __name__ == "__main__":
    main()
