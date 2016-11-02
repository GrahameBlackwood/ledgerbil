"""unit test for ledgerbil.py"""

from helpers import Redirector
from arghandler import ArgHandler


__author__ = 'Scott Carpenter'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'


filename = 'dummy.ldg'


class Arguments(Redirector):

    def test_file_option(self):
        args = ArgHandler.get_args(['-f', filename])
        self.assertTrue(args.file)
        args = ArgHandler.get_args(['--file', filename])
        self.assertTrue(args.file)

    def test_file_option_and_filename_both_required(self):
        """should cause argparse error if file opt specified w/o file"""
        expected = 'error: argument -f/--file: expected one argument'
        try:
            ArgHandler.get_args(['--file'])
        except SystemExit:
            pass

        self.redirecterr.seek(0)
        actual = self.redirecterr.read()
        self.assertTrue(expected in actual)

    def test_sort_option(self):
        args = ArgHandler.get_args(['-f', filename, '-s'])
        self.assertTrue(args.sort)
        args = ArgHandler.get_args(['--file', filename, '--sort'])
        self.assertTrue(args.sort)

    def test_no_sorting_option(self):
        """should not set parse args 'sort' var"""
        args = ArgHandler.get_args(['--file', filename])
        self.assertFalse(args.sort)

    def test_schedule_file_option(self):
        args = ArgHandler.get_args(['-f', filename, '-S', filename])
        self.assertTrue(args.schedule_file)
        args = ArgHandler.get_args([
            '--file', filename,
            '--schedule-file', filename,
        ])
        self.assertTrue(args.schedule_file)

    def test_schedule_filename_required_with_schedule_option(self):
        """argparse error if sched file opt specified w/o file"""
        expected = (
            'error: argument -S/--schedule-file: expected one argument'
        )
        try:
            ArgHandler.get_args(['--file', filename, '--schedule-file'])
        except SystemExit:
            pass

        self.redirecterr.seek(0)
        actual = self.redirecterr.read()
        self.assertTrue(expected in actual)
