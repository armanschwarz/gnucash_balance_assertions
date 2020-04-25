# GnuCash Tools

## Balance Assertions
For help:

```
./gnc_balance_assertion.py --help
```

To run assertions for a GnuCash file located at `/path/to/account.gnucash`, and where assertions are written as transaction descriptions of the form `Balance Assertion: 123.45`, you would run the following:
```
./gnc_balance_assertion.py path/to/account.gnucash --assertion_amount_regex "(?<=Balance Assertion: )[\-]*\d*\.\d*"
```

If you also want to reconcile accumulated amounts since a specific date, you might want balance assertions that look like this: Balance Assertion: 123.45 (since 2019-07-01):

```
./gnc_balance_assertion.py path/to/account.gnucash --assertion_amount_regex "(?<=Balance Assertion: )[\-]*\d*\.\d*" --assertion_start_regex "(?<=\(since: )\d\d\d\d-\d\d-\d\d(?=\))"
```

Note that any date format can be used as long as it is natively recognised by [pandas.to_datetime()](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.to_datetime.html)
