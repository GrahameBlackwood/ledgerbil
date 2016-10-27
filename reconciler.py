#!/usr/bin/env python

from __future__ import division
from __future__ import print_function

import cmd

from datetime import date

import util

__author__ = 'Scott Carpenter'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class Reconciler(cmd.Cmd, object):

    UNKNOWN_SYNTAX = '*** Unknown syntax: '
    NO_HELP = '*** No help on '

    def __init__(self, ledgerfile):
        cmd.Cmd.__init__(self)
        self.aliases = {
            'EOF': self.do_quit,
            'l': self.do_list,
            'll': self.do_list,
            'm': self.do_mark,
            'u': self.do_unmark,
            'q': self.do_quit,
        }

        self.ledgerfile = ledgerfile
        self.to_date = date.today()
        self.ending_balance = None
        self.open_transactions = []
        self.current_listing = {}
        self.total_cleared = 0
        self.total_pending = 0

        for thing in self.ledgerfile.get_things():
            if thing.rec_account_matches:
                if thing.is_cleared():
                    self.total_cleared += thing.rec_amount
                    continue

                if thing.is_pending():
                    self.total_pending += thing.rec_amount

                self.open_transactions.append(thing)

    intro = ''
    prompt = '> '

    def emptyline(self):
        pass  # pragma: no cover

    def default(self, line):
        command, arg, line = self.parseline(line)

        if command == 'EOF':
            print()

        if command in self.aliases:
            return self.aliases[command](arg)
        else:
            print(self.UNKNOWN_SYNTAX + line)

    def do_help(self, arg):
        """Get help for a command; Syntax: help <COMMAND>"""
        if arg in self.aliases:
            arg = self.aliases[arg].__name__[3:]
        cmd.Cmd.do_help(self, arg)

    def do_aliases(self, arg):
        """Print aliases"""
        for alias in sorted(
                self.aliases.keys(),
                key=lambda x: x.lower()
        ):
            print('{alias:5}{command}'.format(
                alias=alias,
                command=self.aliases[alias].__name__[3:]
            ))

    def do_quit(self, arg):
        """Exit the program"""
        return True

    def do_list(self, args):
        """List entries for selected account

        - Shows uncleared and pending transactions. (Pending = "!".)
        """
        self.list_transactions()

    def do_account(self, args):
        """Print the account being reconciled"""
        print(self.ledgerfile.rec_account_matches[0])

    def do_mark(self, args):
        """Mark a transaction as pending (!)

        Syntax: mark <#>

        - The numbered line of a transaction, or multiple numbers
          separated by spaces
        """
        self.mark_or_unmark(args, mark=True)

    def do_unmark(self, args):
        """Remove pending mark (!) from transaction

        Syntax: unmark <#>

        - The numbered line of a transaction, or multiple numbers
          separated by spaces
        """
        self.mark_or_unmark(args, mark=False)

    def do_start(self, args):
        """Start balancing an account, or adjust statement date and
           ending balance

        Syntax: start [date YYYY-MM-DD] [balance]
        """
        pass

    def mark_or_unmark(self, args, mark=True):
        args = util.parse_args(args)
        if not args:
            print('*** Transaction number(s) required')
            return

        at_least_one_success = False
        messages = ''
        for num in args:
            if num not in self.current_listing:
                messages += 'Transaction not found: {}\n'.format(num)
                continue

            thing = self.current_listing[num]

            if mark and thing.is_pending():
                messages += 'Already marked pending: ' + num + '\n'
                continue
            elif not mark and not thing.is_pending():
                messages += "Not marked; can't unmark: " + num + '\n'
                continue

            if mark:
                self.current_listing[num].set_pending()
                self.total_pending += thing.rec_amount
            else:
                thing.set_uncleared()
                self.total_pending -= thing.rec_amount

            self.ledgerfile.write_file()
            at_least_one_success = True

        if at_least_one_success:
            self.list_transactions()

        if messages:
            print(messages, end='')

    def list_transactions(self):
        self.current_listing = {}
        count = 0
        for thing in self.open_transactions:
            if thing.thing_date > self.to_date \
                    and not thing.is_pending():
                continue

            count += 1
            self.current_listing[str(count)] = thing
            print(
                '{number:-4}. {date} {amount} {status:1} {payee} '
                '{code:>7}'.format(
                    number=count,
                    date=thing.get_date_string(),
                    code=thing.transaction_code,
                    payee=get_colored_payee(thing.payee),
                    amount=get_colored_amount(thing.rec_amount),
                    status=thing.rec_status
                )
            )
        self.print_total('cleared', self.total_cleared)
        self.print_total('pending', self.total_pending)

    @staticmethod
    def print_total(label, total):
        print('{label:9}{total}'.format(
            label=label,
            total=get_colored_amount(total)
        ))


def get_colored_amount(amount):
    if amount < 0:
        color = '\033[0;31m'  # red
    else:
        color = '\033[0;32m'  # green

    amount_formatted = '${:.2f}'.format(amount)

    return '{start}{amount:>10}{end}'.format(
        start=color,
        amount=amount_formatted,
        end='\033[0m'
    )


def get_colored_payee(text):
    # cyan
    return '{start}{payee:40}{end}'.format(
        start='\033[0;36m',
        payee=text,
        end='\033[0m'
    )
