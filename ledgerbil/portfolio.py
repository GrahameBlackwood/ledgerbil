import argparse
import itertools
import json
import re
from collections import defaultdict, namedtuple

from . import util
from .colorable import Colorable
from .ledgerbilexceptions import LdgPortfolioError
from .settings import Settings

settings = Settings()

Year = namedtuple('Year', 'year contributions transfers value gain gain_value')
Summary = namedtuple('Summary', 'col1 value gain_value years all y3 y5 y10')


def strip_assets_prefix(s):
    return re.sub('(?i)assets: ?', '', s)


def get_portfolio_report(args):

    matched_accounts, matched_labels, included_years = \
        get_matching_accounts(args.accounts_regex, args.labels)

    if not matched_accounts:
        return no_match(args.accounts_regex, args.labels)

    if args.history:
        report = get_history_report(matched_accounts)
    elif args.compare:
        report = get_comparison_report(
            matched_accounts,
            matched_labels
        )
    elif args.list:
        report = get_list(matched_accounts)
    else:
        if not included_years:
            return no_match(args.accounts_regex, args.labels, yearly=True)
        report = get_performance_report(matched_accounts, included_years)

    return report


def no_match(accounts_regex, labels, yearly=False):
    if yearly:
        message = f'No yearly data found for accounts "{accounts_regex}"'
    else:
        message = f'No accounts matched "{accounts_regex}"'

    if labels:
        message += f', labels "{labels}"'

    return message


def get_matching_accounts(accounts_regex, labels_string=''):
    portfolio_data = get_portfolio_data()
    included_years = set()
    labels = {
        label for label in re.split('[, ]+', labels_string) if label != ''
    }
    matched_accounts = []
    matched_labels = set()
    for account in portfolio_data:
        account_match = re.search(accounts_regex, account['account'])

        if labels:
            label_match = labels & set(account['labels'])
            matched_labels = matched_labels.union(label_match)
        else:
            label_match = account_match

        if account_match and label_match:
            # todo: validation?
            #       - year: format and sanity check on range
            #       - warn if missing years in accounts?
            included_years.update(set(account['years'].keys()))
            matched_accounts.append(account)

    return (
        sorted(matched_accounts, key=lambda k: k['account']),
        matched_labels,
        included_years
    )


def get_list(accounts):
    COL_ACCOUNT = 40  # temporary: will come from elsewhere after comp merge

    lines = ''
    for account in accounts:
        name = Colorable(
            'blue',
            strip_assets_prefix(account['account']),
            fmt=COL_ACCOUNT
        )
        labels = Colorable('white', ' '.join(sorted(account['labels'])))
        lines += f'{name}    {labels}\n'

    count = f"{len(accounts)} account{'' if len(accounts) == 1 else 's'}"

    all_labels = sorted(set(
        itertools.chain.from_iterable([a['labels'] for a in accounts])
    ))
    return '{}\n{}\n{}'.format(
        lines,
        Colorable('cyan', count),
        Colorable('cyan', ' '.join(all_labels))
    )


VALID_YEAR_KEYS = {'symbol', 'price', 'shares',
                   'contributions', 'transfers', 'note'}


def validate_json_year_keys(year):
    if not all([k in VALID_YEAR_KEYS for k in year.keys()]):
        raise LdgPortfolioError(f'Invalid key in {year.keys()}')


def get_performance_report_header(accounts, num_years):
    header = f"{num_years} year{'' if num_years == 1 else 's'}, "
    header += f"{len(accounts)} account{'' if len(accounts) == 1 else 's'}: "
    header += ', '.join([account['account'] for account in accounts[:2]])
    if len(accounts) > 2:
        header += ', ...'
    return strip_assets_prefix(header)


def get_performance_report(accounts, included_years):
    totals = get_yearly_combined_accounts(accounts, included_years)
    years = get_yearly_with_gains(totals)
    return '{header}\n\n{col_headers}\n{report}'.format(
        header=get_performance_report_header(accounts, len(years)),
        col_headers=get_performance_report_column_headers(len(years)),
        report=get_performance_report_years(years)
    )


COL_GAIN = 7
COL_CONTRIB = 9
COL_TRANSFERS = 10
COL_VALUE = 11
COL_GAIN_VALUE = 11
COL_NUM_YEARS = 2
COL_ACCOUNT = 40
COL_LABEL = 12
COL_PERCENT = 3


def get_annualized_total_return(gains, num_years):
    return (pow(util.product(gains[-num_years:]), 1 / num_years) - 1) * 100


def get_gain(gains, num_years):
    if len(gains) >= num_years:
        return util.get_colored_amount(
            get_annualized_total_return(gains, num_years),
            colwidth=COL_GAIN,
            prefix='',
            positive='white'
        )
    else:
        return ''


def get_performance_report_column_headers(num_years):
    header3 = '' if num_years < 3 else f"{'3yr %':>{COL_GAIN}}"
    header5 = '' if num_years < 5 else f"{'5yr %':>{COL_GAIN}}"
    header10 = '' if num_years < 10 else f"{'10yr %':>{COL_GAIN}}"

    return str(Colorable(
        'cyan',
        (f"year  {'contrib':>{COL_CONTRIB}}  {'transfers':>{COL_TRANSFERS}}  "
         f"{'value':>{COL_VALUE}}  {'gain %':>{COL_GAIN}}  "
         f"{'gain val':>{COL_GAIN_VALUE}}  {'all %':>{COL_GAIN}}  "
         f'{header3}  {header5}  {header10}')
    ))


def get_performance_report_years(years):
    report = ''
    contrib_total = 0
    transfers_total = 0
    gain_val_total = 0
    gains = []
    for year in years:
        gains.append(year.gain)
        if year.contributions:
            contrib = util.get_colored_amount(
                year.contributions,
                colwidth=COL_CONTRIB,
                decimals=0,
                positive='yellow'
            )
        else:
            contrib = ' ' * COL_CONTRIB

        if year.transfers and (f'{year.transfers:.0f}' not in ('0', '-0')):
            transfers = util.get_colored_amount(year.transfers,
                                                colwidth=COL_TRANSFERS,
                                                decimals=0)
        else:
            transfers = ' ' * COL_TRANSFERS

        value = util.get_plain_amount(year.value, COL_VALUE, 0)
        gain = get_gain([year.gain], 1)
        gain_value = util.get_colored_amount(year.gain_value,
                                             colwidth=COL_GAIN_VALUE,
                                             decimals=0)

        gain_all = get_gain(gains, len(gains))
        gain_3 = get_gain(gains, 3)
        gain_5 = get_gain(gains, 5)
        gain_10 = get_gain(gains, 10)

        report += (f'{year.year}  {contrib}  {transfers}  {value}  '
                   f'{gain}  {gain_value}  {gain_all}  '
                   f'{gain_3}  {gain_5}  {gain_10}\n')

        contrib_total += year.contributions
        transfers_total += year.transfers
        gain_val_total += year.gain_value

    if len(years) > 1:
        contrib_total_f = util.get_colored_amount(contrib_total,
                                                  colwidth=COL_CONTRIB,
                                                  decimals=0)
        transfers_total_f = util.get_colored_amount(transfers_total,
                                                    colwidth=COL_TRANSFERS,
                                                    decimals=0)
        gain_val_total_f = util.get_colored_amount(gain_val_total,
                                                   colwidth=COL_GAIN_VALUE,
                                                   decimals=0)
        report += (f'      {contrib_total_f}  {transfers_total_f}  '
                   f'{"":{COL_VALUE + COL_GAIN + 2}}  {gain_val_total_f}')

    return report


def get_yearly_combined_accounts(accounts, included_years):
    # Combine all the accounts into total contributions and value per year
    year_start, year_end = util.get_start_and_end_range(included_years)
    totals = defaultdict(lambda: defaultdict(float))
    for account in accounts:
        previous_value = 0
        for year in range(year_start, year_end):
            if str(year) not in account['years'].keys():
                if previous_value:
                    # todo: integration with ledger to get current info
                    totals[year]['contributions'] += 0
                    totals[year]['transfers'] += 0
                    totals[year]['value'] += previous_value
                continue

            data = account['years'][str(year)]
            validate_json_year_keys(data)

            value = data['price'] * data['shares']
            totals[year]['contributions'] += data['contributions']
            totals[year]['transfers'] += data.get('transfers', 0)
            totals[year]['value'] += value
            previous_value = value

    return totals


def get_yearly_with_gains(totals):
    years = []
    previous_year = None
    for year in sorted(totals):
        value = totals[year]['value']
        contrib = totals[year]['contributions']
        transfers = totals[year]['transfers']

        previous_value = previous_year.value if previous_year else 0
        gain = ((value - (contrib + transfers) / 2)
                / (previous_value + (contrib + transfers) / 2))
        gain_value = value - contrib - transfers - (previous_value or 0)

        assert gain > 0, f'Gain < 0 in {year}: {gain}'

        this_year = Year(year, contrib, transfers, value, gain, gain_value)
        years.append(this_year)

        previous_year = this_year

    return years


def get_history_report(matching_accounts):
    report = ''
    for account in matching_accounts:
        report += f'{get_account_history(account)}\n'

    return report


def get_account_history(account):
    labels = f"labels: {', '.join(account['labels'])}"
    history = '{account}\n{label}'.format(
        account=Colorable('purple', strip_assets_prefix(account['account'])),
        label=Colorable('white', labels, '>79') if account['labels'] else ''
    )

    years = account['years']
    if len(years):
        percent = '%' if len(years) > 1 else ''
        header = (
            f"\n    year  {'contrib':>10}  {'transfers':>10}  {'shares':>9}  "
            f"{'price':>10}  {'value':>12}  {percent:>8}\n"
        )
        history += f"{Colorable('cyan', header)}"
    else:
        return history

    year_start, year_end = util.get_start_and_end_range(years.keys())
    contrib_total = 0
    transfers_total = 0
    previous_shares = None
    previous_price = None
    previous_value = 0
    for year in range(year_start, year_end):
        year = str(year)
        transfers_f = ' ' * 10
        contrib_f = ' ' * 10
        if year in years.keys():
            validate_json_year_keys(years[year])
            contrib = years[year]['contributions']
            if contrib:
                contrib_f = Colorable('yellow', f'$ {contrib:,.0f}', '>10')
            transfers = years[year].get('transfers', 0)
            if transfers:
                transfers_f = util.get_colored_amount(transfers, 10, 0)
            shares = years[year]['shares']
            price = years[year]['price']
        else:
            # todo: integration with ledger to get current info
            contrib = 0
            contrib_f = Colorable('red', '???', '>10')
            shares = previous_shares
            price = previous_price

        shares_f = Colorable('blue', shares, '9,.0f')
        price_f = Colorable('yellow', f'$ {price:,.2f}', '>10')

        value = shares * price
        value_f = util.get_plain_amount(value, colwidth=12, decimals=0)

        gain_f = ' ' * 8
        gain = ((value - (contrib + transfers) / 2)
                / (previous_value + (contrib + transfers) / 2) - 1) * 100
        if gain != 0:
            gain_f = util.get_colored_amount(gain,
                                             colwidth=8,
                                             prefix='',
                                             positive='white')

        history += (
            f'    {year}  {contrib_f}  {transfers_f}  {shares_f}  '
            f'{price_f}  {value_f}  {gain_f}\n'
        )

        previous_shares = shares
        previous_price = price
        previous_value = value
        contrib_total += contrib
        transfers_total += transfers

    if len(years) > 1:
        contrib_total_f = util.get_colored_amount(contrib_total, 10, 0)
        transfers_total_f = util.get_colored_amount(transfers_total, 10, 0)
        history += f'          {contrib_total_f}  {transfers_total_f}\n'

    return history


def get_comparison_report_column_headers(num_years, labels=True):
    header3 = '' if num_years < 3 else f"{'3yr %':>{COL_GAIN}}"
    header5 = '' if num_years < 5 else f"{'5yr %':>{COL_GAIN}}"
    header10 = '' if num_years < 10 else f"{'10yr %':>{COL_GAIN}}"

    if labels:
        col1 = f"{'labels':{COL_LABEL}}"
    else:
        col1 = f"{'accounts':{COL_ACCOUNT}}"

    return str(Colorable(
        'cyan',
        (f"{col1}  {'value':>{COL_VALUE}}    %  {'gain val':>{COL_GAIN_VALUE}}"
         f"  yr  {'all %':>{COL_GAIN}}  {header3}  {header5}  {header10}")
    ))


def get_comparison_report(accounts, labels):
    if labels:
        for label in labels:
            pass
    else:
        for account in accounts:
            totals = get_yearly_combined_accounts(
                [account],
                set(account['years'].keys)
            )
            years = get_yearly_with_gains(totals)
            summary = get_comparison_line_item(  # noqa
                years,
                strip_assets_prefix(account['account'])
            )

    # 'Summary' -> 'col1 value gain_value years all y3 y5 y10'

    return '{header}\n\n{col_headers}\n{report}'.format(
        header='possible header',
        col_headers=get_comparison_report_column_headers(10, True),
        report='comparison stuff...'
    )


def get_comparison_line_item(years, col1):
    # gain_value = sum([year.gain_value for year in years])
    pass


def get_portfolio_data():
    with open(settings.PORTFOLIO_FILE, 'r') as portfile:
        return json.loads(portfile.read())


def get_args(args=[]):
    parser = argparse.ArgumentParser(
        prog='ledgerbil/main.py portfolio',
        formatter_class=(
            lambda prog: argparse.HelpFormatter(prog, max_help_position=36)
        )
    )
    parser.add_argument(
        '-a', '--accounts',
        type=str,
        metavar='REGEX',
        dest='accounts_regex',
        default='.*',
        help='include accounts that match this regex, default = .* (all)'
    )
    parser.add_argument(
        '-L', '--labels',
        type=str,
        default='',
        help='include accounts that match these labels along with --accounts'
    )
    parser.add_argument(
        '-c', '--compare',
        action='store_true',
        help='compare accounts or labels'
    )
    parser.add_argument(
        '-H', '--history',
        action='store_true',
        help='show account history'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='list matching account names'
    )

    return parser.parse_args(args)


def main(argv=[]):
    args = get_args(argv)
    print(get_portfolio_report(args))
