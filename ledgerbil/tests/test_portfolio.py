import json
from unittest import mock

import pytest

from .. import portfolio
from .helpers import OutputFileTester


class MockSettings(object):
    PORTFOLIO_FILE = 'abcd'


def setup_module(module):
    portfolio.settings = MockSettings()


BIG_CO = 0
BONDS = 1
BONDS_2 = 2
BIG_NAME = 3


portfolio_json_data = '''\
    [
      {
        "account": "assets: 401k: big co 500 idx",
        "labels": [
          "large",
          "401k",
          "flurb"
        ],
        "years": {
          "2016": {
            "symbol": "abcdx",
            "price": 80.23,
            "shares": 12200.78,
            "contributions": 1500.79,
            "transfers": 900000,
            "note": "optional..."
          },
          "2019": {
            "symbol": "abcdx",
            "price": 83.11,
            "shares": 1700,
            "contributions": 500,
            "transfers": -100000
          },
          "2017": {
            "symbol": "abcdx",
            "price": 81.57,
            "shares": 999,
            "contributions": 11500
          }
        }
      },
      {
        "account": "assets: 401k: bonds idx",
        "labels": [
          "bonds",
          "401k",
          "flurb"
        ],
        "years": {
          "2016": {
            "symbol": "lmnop",
            "price": 119.76,
            "shares": 3750,
            "contributions": 750
          },
          "2015": {
            "symbol": "lmnop",
            "price": 20.31,
            "shares": 2000,
            "contributions": 0
          },
          "2014": {
            "symbol": "lmnop",
            "price": 20.78,
            "shares": 1800,
            "contributions": 750,
            "transfers": 15000
          }
        }
      },
      {
        "account": "assets: 401k: bonds idx 2",
        "labels": [],
        "years": {}
      },
      {
        "account": "assets: 401k: long account name that goes on...",
        "labels": ["401k", "flurb", "intl", "active", "smactive"],
        "years": {}
      }
    ]
    '''
portfolio_data = json.loads(portfolio_json_data)


@mock.patch(__name__ + '.portfolio.get_portfolio_data')
def test_get_portfolio_report_no_matches(mock_get_data):
    mock_get_data.return_value = portfolio_data
    args = portfolio.get_args(['--accounts', 'qwertyable'])
    expected = 'No accounts matched qwertyable'
    assert portfolio.get_portfolio_report(args) == expected


@mock.patch(__name__ + '.portfolio.get_portfolio_data')
def test_get_portfolio_report_history(mock_get_data):
    mock_get_data.return_value = portfolio_data
    args = portfolio.get_args(['--accounts', 'idx', '--history'])
    report = portfolio.get_portfolio_report(args)
    helper = OutputFileTester('test_portfolio_report_history')
    helper.save_out_file(report)
    helper.assert_out_equals_expected()


@mock.patch(__name__ + '.portfolio.get_portfolio_data')
def test_account_matching_all(mock_get_data):
    mock_get_data.return_value = portfolio_data
    matched, included_years = portfolio.get_matching_accounts('.*')
    expected_included_years = {'2014', '2015', '2016', '2017', '2019'}
    assert matched == portfolio_data
    assert included_years == expected_included_years


@mock.patch(__name__ + '.portfolio.get_portfolio_data')
def test_account_matching_regex(mock_get_data):
    mock_get_data.return_value = portfolio_data
    matched, included_years = portfolio.get_matching_accounts('idx$')
    expected_included_years = {'2014', '2015', '2016', '2017', '2019'}
    assert matched == portfolio_data[:BONDS + 1]
    assert included_years == expected_included_years


def test_get_portfolio_data():
    jsondata = '{"key": "value"}'
    expected = {'key': 'value'}
    with mock.patch(__name__ + '.portfolio.open',
                    mock.mock_open(read_data=jsondata)) as m:
        data = portfolio.get_portfolio_data()

    assert data == expected
    m.assert_called_once_with('abcd', 'r')


def test_get_account_history():
    history = portfolio.get_account_history(portfolio_data[BIG_CO])
    helper = OutputFileTester('test_portfolio_account_history')
    helper.save_out_file(history)
    helper.assert_out_equals_expected()


def test_get_account_history_no_labels_no_years():
    history = portfolio.get_account_history(portfolio_data[BONDS_2])
    helper = OutputFileTester('test_portfolio_account_history_empty')
    helper.save_out_file(history)
    helper.assert_out_equals_expected()


def test_get_account_history_long_name_no_years():
    history = portfolio.get_account_history(portfolio_data[BIG_NAME])
    helper = OutputFileTester('test_portfolio_account_history_empty_long')
    helper.save_out_file(history)
    helper.assert_out_equals_expected()


def test_get_account_history_one_year():
    account = {
        'account': 'assets: 401k: bonds idx',
        'labels': [],
        'years': {
            '2016': {'price': 119.76, 'shares': 3750.9, 'contributions': 750}
        }
    }
    history = portfolio.get_account_history(account)
    helper = OutputFileTester('test_portfolio_account_history_one_year')
    helper.save_out_file(history)
    helper.assert_out_equals_expected()


def test_get_yearly_combined_accounts_single_account():
    accounts = [{
        'account': 'the account name',
        'years': {
            '2014': {'price': 100, 'shares': 10,
                     'contributions': 50, 'transfers': 50},
            '2015': {'price': 110, 'shares': 20, 'contributions': 200},
        }
    }]
    expected = {
        2014: {'contributions': 50, 'transfers': 50, 'value': 1000.0},
        2015: {'contributions': 200, 'transfers': 0, 'value': 2200.0},
    }
    actual = portfolio.get_yearly_combined_accounts(accounts, 2014, 2016)
    assert actual == expected


def test_get_yearly_combined_accounts_two_accounts_same_years():
    accounts = [
        {
            'account': 'the account name',
            'years': {
                '2014': {'price': 100, 'shares': 10, 'contributions': 100},
                '2015': {'price': 110, 'shares': 20, 'contributions': 200},
            }
        },
        {
            'account': 'another account name',
            'years': {
                '2014': {'price': 300, 'shares': 50, 'contributions': 500},
                '2015': {'price': 330, 'shares': 100,
                         'contributions': 1250, 'transfers': -250},
            }
        }
    ]
    expected = {
        2014: {'contributions': 600.0, 'transfers': 0, 'value': 16000.0},
        2015: {'contributions': 1450.0, 'transfers': -250, 'value': 35200.0},
    }
    actual = portfolio.get_yearly_combined_accounts(accounts, 2014, 2016)
    assert actual == expected


def test_get_yearly_combined_accounts_single_account_missing_years():
    accounts = [{
        'account': 'the account name',
        'years': {
            '2013': {'price': 100, 'shares': 10,
                     'contributions': 50, 'transfers': 50},
            '2015': {'price': 110, 'shares': 20, 'contributions': 200},
        }
    }]
    expected = {
        2013: {'contributions': 50.0, 'transfers': 50, 'value': 1000.0},
        2014: {'contributions': 0, 'transfers': 0, 'value': 1000},
        2015: {'contributions': 200.0, 'transfers': 0, 'value': 2200.0},
        2016: {'contributions': 0, 'transfers': 0, 'value': 2200},
        2017: {'contributions': 0, 'transfers': 0, 'value': 2200},
    }
    actual = portfolio.get_yearly_combined_accounts(accounts, 2010, 2018)
    assert actual == expected


def test_get_yearly_combined_accounts_multiple_accounts_missing_years():
    accounts = [
        {
            'account': 'the account name',
            'years': {
                '2013': {'price': 100, 'shares': 10, 'contributions': 100},
                '2015': {'price': 110, 'shares': 20,
                         'contributions': 300, 'transfers': -100},
            },
        },
        {
            'account': 'another account name',
            'years': {
                '2015': {'price': 330, 'shares': 100,
                         'contributions': 500, 'transfers': 500},
                '2014': {'price': 300, 'shares': 50, 'contributions': 500},
                '2018': {'price': 250, 'shares': 110, 'contributions': 800},
            }
        }
    ]
    expected = {
        2013: {'contributions': 100, 'transfers': 0, 'value': 1000.0},
        2014: {'contributions': 500, 'transfers': 0, 'value': 16000},
        2015: {'contributions': 800, 'transfers': 400, 'value': 35200.0},
        2016: {'contributions': 0, 'transfers': 0, 'value': 35200},
        2017: {'contributions': 0, 'transfers': 0, 'value': 35200},
        2018: {'contributions': 800, 'transfers': 0, 'value': 29700},
    }
    actual = portfolio.get_yearly_combined_accounts(accounts, 2010, 2019)
    assert actual == expected


def test_get_yearly_with_gains():
    """ get_yearly_with_gains should produce a sorted list of Years"""
    totals = {
        2014: {'contributions': 1000, 'transfers': 0, 'value': 5000.0},
        2013: {'contributions': 500, 'transfers': 500, 'value': 1000.0},
        2015: {'contributions': 0, 'transfers': 0, 'value': 5000.0},
        2016: {'contributions': 3000.0, 'transfers': -1000, 'value': 4000},
    }
    expected = [
        portfolio.Year(2013, 500, 500, 1000.0, 1, 0),
        portfolio.Year(2014, 1000, 0, 5000.0, 3, 3000),
        portfolio.Year(2015, 0, 0, 5000.0, 1, 0),
        portfolio.Year(2016, 3000.0, -1000, 4000.0, 0.5, -3000.0),
    ]
    actual = portfolio.get_yearly_with_gains(totals)
    assert actual == expected


def test_get_yearly_with_gains_first_year_gain():
    """ get_yearly_with_gains should provide a gain value in first year"""
    totals = {
        2013: {'contributions': 1000, 'transfers': 0, 'value': 2000.0},
        2014: {'contributions': 500, 'transfers': 500, 'value': 5000.0},
    }
    expected = [
        portfolio.Year(2013, 1000, 0, 2000.0, 3.0, 1000.0),
        portfolio.Year(2014, 500, 500, 5000.0, 1.8, 2000.0),
    ]
    actual = portfolio.get_yearly_with_gains(totals)
    assert actual == expected


@mock.patch(__name__ + '.portfolio.get_portfolio_report', return_value='hi!')
@mock.patch(__name__ + '.portfolio.print')
def test_main(mock_print, mock_report):
    portfolio.main([])
    expected = 'hi!'
    mock_print.assert_called_once_with(expected)


@pytest.mark.parametrize('test_input, expected', [
    (['-a', '401k'], '401k'),
    (['--accounts', '(a|b|c)$'], '(a|b|c)$'),
    ([], '.*'),  # default
])
def test_args_accounts(test_input, expected):
    args = portfolio.get_args(test_input)
    assert args.accounts_regex == expected


@pytest.mark.parametrize('test_input, expected', [
    (['-H'], True),
    (['--history'], True),
    ([], False),
])
def test_args_command(test_input, expected):
    args = portfolio.get_args(test_input)
    assert args.history is expected
