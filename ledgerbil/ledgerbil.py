import argparse
import sys
from textwrap import dedent

from .ledgerbilexceptions import LdgReconcilerError, LdgSchedulerError
from .ledgerfile import LedgerFile
from .reconciler import Reconciler
from .schedulefile import ScheduleFile
from .scheduler import Scheduler


class Ledgerbil:

    def __init__(self, args):
        self.args = args
        self.ledgerfiles = None

    def run(self):

        if self.args.next_scheduled_date:
            return self.next_scheduled_date()

        if not self.args.file:
            return self.error('error: -f/--file is required')

        try:
            self.ledgerfiles = [
                LedgerFile(f, self.args.reconcile) for f in self.args.file
            ]
        except LdgReconcilerError as e:
            return self.error(str(e))

        if self.args.reconcile:
            return self.run_reconciler()

        if self.args.schedule:
            error = self.run_scheduler()
            if error:
                return error

        if self.args.sort:
            for ledgerfile in self.ledgerfiles:
                ledgerfile.sort()
                ledgerfile.write_file()

        return 0

    def error(self, message):
        print(message, file=sys.stderr)
        return -1

    def next_scheduled_date(self):
        if not self.args.schedule:
            return self.error('error: -s/--schedule is required')
        try:
            schedule_file = ScheduleFile(self.args.schedule)
        except LdgSchedulerError as e:
            return self.error(str(e))
        print(schedule_file.next_scheduled_date())
        return 0

    def run_scheduler(self):
        ledgerfile = self.ledgerfiles[0]
        try:
            schedule_file = ScheduleFile(self.args.schedule)
        except LdgSchedulerError as e:
            return self.error(str(e))
        scheduler = Scheduler(ledgerfile, schedule_file)
        scheduler.run()
        schedule_file.write_file()
        ledgerfile.write_file()

    def run_reconciler(self):

        if not any(lf.rec_account_matched for lf in self.ledgerfiles):
            print(f'No matching account found for "{self.args.reconcile}"')
            return 0

        try:
            reconciler = Reconciler(self.ledgerfiles)
        except LdgReconcilerError as e:
            return self.error(str(e))

        reconciler.cmdloop()
        return 0


def get_args(args):
    program = 'ledgerbil/main.py'
    description = dedent('''\
        ledgerbil works with ledger cli files. It supports a vague subset
        of ledger as used and tested by its author.

        It is biased, if not welded, to dollars as the default commodity,
        but the author would happily aspire to more flexibility with the
        help of motivated contributors or users. (Similarly it assumes
        commas as the thousands separator but certainly this shouldn't be
        insurmountable to modify for a more international community.)

        Some features work on ledger files independently of the ledger cli
        program itself, while others use ledger to report on ledger data
        in ways not currently supported by ledger. (Or at least, in ways
        not understood by the author.)

        See settings.py.example for supported config options.
    ''')
    scripts_description = dedent(f'''\
        other commands (run with -h to see command help):
            {program}
                grid                    ledger reports in year/month tables
                investments (or inv)    nicer view of shares and dollars
                pass                    passthrough to ledger
                portfolio (or port)     standalone investment tracker
                prices                  download mutual fund prices
        ''')

    parser = argparse.ArgumentParser(
        prog=program,
        description=description,
        epilog=scripts_description,
        formatter_class=(lambda prog: argparse.RawTextHelpFormatter(
            prog,
            max_help_position=40,
            width=100
        ))
    )
    parser.add_argument(
        '-f', '--file',
        type=str,
        action='append',
        default=[],
        help='ledger file(s) to be processed'
    )
    parser.add_argument(
        '-S', '--sort',
        action='store_true',
        help='sort the file(s) by transaction date (can be used with\n'
             '--schedule and will sort after scheduler entries are added)'
    )
    parser.add_argument(
        '-r', '--reconcile',
        type=str,
        metavar='ACCT',
        help='interactively reconcile the specified account regex\n'
             '(scheduler/sort have no effect if also specified)'
    )
    parser.add_argument(
        '-s', '--schedule',
        type=str,
        metavar='FILE',
        help='scheduled transactions file, to be added to -f ledger file\n'
             '(if multiple ledger files specified, will use the first)'
    )
    parser.add_argument(
        '-n', '--next-scheduled-date',
        action='store_true',
        help='show the date of the next scheduled transaction'
    )

    if not args:
        parser.print_help()

    return parser.parse_args(args)


def main(argv=None):
    args = get_args(argv or [])
    ledgerbil = Ledgerbil(args)

    return ledgerbil.run()
