#!/usr/bin/python

"""unit test for ledgerthing.py"""

from unittest import TestCase

from datetime import date

from helpers import Redirector
from ledgerbilexceptions import LdgReconcilerMoreThanOneMatchingAccount
from ledgerthing import LedgerThing
from ledgerthing import REC_STATUS_ERROR_MESSAGE
from ledgerthing import UNSPECIFIED_PAYEE


__author__ = 'Scott Carpenter'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'


class Constructor(TestCase):

    def test_non_transaction_date(self):
        """non-transactions initially have date = None"""
        thing = LedgerThing(['blah', 'blah blah blah'])
        self.assertIsNone(thing.thing_date)

    def test_transaction_date(self):
        thing = LedgerThing(['2013/05/18 blah', '    ; something...'])
        self.assertEqual(thing.thing_date, date(2013, 5, 18))

    def verify_top_line(self, line, the_date, code, payee):
        thing = LedgerThing([line])
        self.assertEqual(thing.thing_date, the_date)
        self.assertEqual(code, thing.transaction_code)
        self.assertEqual(payee, thing.payee)

    def test_top_line(self):
        self.verify_top_line(
            '2016/10/20',
            date(2016, 10, 20), '', UNSPECIFIED_PAYEE
        )
        self.verify_top_line(
            '2016/10/20 someone',
            date(2016, 10, 20), '', 'someone'
        )
        self.verify_top_line(
            '2016/10/20 someone           ; some comment',
            date(2016, 10, 20), '', 'someone'
        )
        self.verify_top_line(
            '2016/02/04 (123)',
            date(2016, 2, 4), '123', UNSPECIFIED_PAYEE
        )
        self.verify_top_line(
            '2016/02/04 (123) someone',
            date(2016, 2, 4), '123', 'someone'
        )
        self.verify_top_line(
            '2001/04/11 (abc)                 ; yah',
            date(2001, 4, 11), 'abc', UNSPECIFIED_PAYEE
        )
        self.verify_top_line(
            '2001/04/11 (abc) someone        ; yah',
            date(2001, 4, 11), 'abc', 'someone'
        )
        self.verify_top_line(
            '2001/04/11 () someone        ; yah',
            date(2001, 4, 11), '', 'someone'
        )
        self.verify_top_line('2001/04/11(abc)', None, '', None)
        self.verify_top_line('2001/04/11someone', None, '', None)


class GetLines(TestCase):

    def test_get_lines(self):
        """lines can be entered and retrieved as is"""
        lines = ['abc\n', 'xyz\n']
        thing = LedgerThing(lines)
        self.assertEqual(lines, thing.get_lines())


class IsNewThing(TestCase):

    def test_is_new_thing(self):
        self.assertTrue(LedgerThing.is_new_thing('2013/04/15 ab store'))

    def test_is_not_thing(self):
        self.assertFalse(LedgerThing.is_new_thing(''))


class IsTransactionStart(TestCase):

    def test_valid_transaction_start(self):
        """date recognized as the start of a transaction"""
        self.assertTrue(
            LedgerThing.is_transaction_start('2013/04/14 abc store')
        )

    def test_valid_transaction_start_with_tabs(self):
        """date recognized as the start of a transaction"""
        self.assertTrue(
            LedgerThing.is_transaction_start('2013/04/14\t\tabc store')
        )

    def test_leading_white_space(self):
        """leading whitespace should return false"""
        self.assertFalse(
            LedgerThing.is_transaction_start('    2013/04/14 abc store')
        )

    def test_date_only(self):
        self.assertTrue(LedgerThing.is_transaction_start('2013/04/14 '))
        self.assertTrue(LedgerThing.is_transaction_start('2013/04/14'))

    def test_empty_line(self):
        self.assertFalse(LedgerThing.is_transaction_start(''))

    def test_newline(self):
        line = '\n'
        self.assertFalse(
            LedgerThing.is_transaction_start(line)
        )

    def test_whitespace(self):
        self.assertFalse(
            LedgerThing.is_transaction_start('            \t    ')
        )

    def test_invalid_date(self):
        self.assertFalse(
            LedgerThing.is_transaction_start('2013/02/30 abc store')
        )

    def test_invalid_date_formats(self):
        self.assertFalse(
            LedgerThing.is_transaction_start('2013/5/12 abc store')
        )
        self.assertFalse(
            LedgerThing.is_transaction_start('2013/06/1 abc store')
        )

    def test_transaction_code(self):
        self.assertTrue(
            LedgerThing.is_transaction_start('2016/10/20 (123) store')
        )
        self.assertTrue(
            LedgerThing.is_transaction_start('2016/10/20 (abc)store')
        )
        self.assertTrue(
            LedgerThing.is_transaction_start('2016/10/20 (123)')
        )
        self.assertTrue(
            LedgerThing.is_transaction_start('2016/10/20 (123)   ; xyz')
        )
        self.assertFalse(
            LedgerThing.is_transaction_start('2016/10/20(123)')
        )
        self.assertFalse(
            LedgerThing.is_transaction_start('2016/10/20someone')
        )


class ReconcilerParsing(Redirector):

    def verify_reconcile_vars(
            self,
            lines,
            account='not given GyibM3nob1kwJ',
            expected_matches=(),
            expected_amount=0,
            expected_status=''
    ):
        if account == 'not given GyibM3nob1kwJ':
            t = LedgerThing(lines)
            account = None
        else:
            t = LedgerThing(lines, account)

        if account is None:
            self.assertIsNone(t.rec_account)
        else:
            self.assertEqual(account, t.rec_account)

        self.assertEqual(
            len(expected_matches),
            len(t.rec_account_matches)
        )
        self.assertEqual(expected_matches, tuple(t.rec_account_matches))
        self.assertEqual(expected_status, t.rec_status)
        self.assertEqual(expected_amount, t.rec_amount)

    def test_reconcile_not_a_transaction(self):
        # not reconciling
        self.verify_reconcile_vars(['; some comment'])
        # noinspection PyTypeChecker
        self.verify_reconcile_vars(['; some comment'], None)
        # reconciling
        self.verify_reconcile_vars(['; some comment'], 'checking',)

    def test_one_line_transaction(self):
        # appears to be valid in ledger but not really a transaction
        self.verify_reconcile_vars(['2016/10/23 blah'])
        # this one doesn't do that much but does exercise "no lines"
        # check at top of _parse_transaction_lines, which shouldn't
        # happen with valid data
        self.verify_reconcile_vars(['2016/10/23 blah'], 'checking')

    def test_simple_transactions(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '    a: checking   $-25',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=-25
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '    a: checking   $50  ; this one has a comment',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=50
        )
        # not a matching account
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '    a: checking   $50  ; this one has a comment',
            ],
            account='credit card'
        )

    def test_simple_transactions_with_math(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '    a: checking',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=-25
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '    a: checking          ; this one has a comment',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=50
        )

    def test_comments_and_empty_lines_and_non_matching(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    ; comment line',
                '    e: blurg      $25',
                '    a: checking   $-25',
                '',
                '; these are',
                '#   all comments',
                '%     when at',
                '|       the beginning',
                '*         of a line',
                '',
                'account assets: checking up'
            ],
            account='a: checking',
            expected_matches=('a: checking',),
            expected_amount=-25
        )

    def test_status(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  ! a: checking   $-25',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=-25,
            expected_status=LedgerThing.REC_PENDING
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  * a: checking   $-25',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=-25,
            expected_status=LedgerThing.REC_CLEARED
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  ! a: checking   $-25        ; with comment',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=-25,
            expected_status=LedgerThing.REC_PENDING
        )

    def test_status_with_math(self):

        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  ! a: checking',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=-25,
            expected_status=LedgerThing.REC_PENDING
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '  * a: checking          ; this one has a comment',
            ],
            account='check',
            expected_matches=('a: checking',),
            expected_amount=50,
            expected_status=LedgerThing.REC_CLEARED
        )

    def test_multiple_statuses(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg            $-40',
                '  * a: checking up     $20      ; has comment',
                '  ! a: checking up     $20',
            ],
            account='checking',
            expected_matches=('a: checking up',),
            expected_amount=40,
            expected_status=LedgerThing.REC_CLEARED
            )
        self.assertEqual(
            REC_STATUS_ERROR_MESSAGE.format(
                status=LedgerThing.REC_CLEARED,
                date='2016/10/23',
                payee='blah'
            ),
            self.redirect.getvalue().rstrip()
        )
        self.reset_redirect()
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg            $-40',
                '    a: checking up     $20      ; has comment',
                '  * a: checking up     $20',
            ],
            account='checking',
            expected_matches=('a: checking up',),
            expected_amount=40,
            expected_status=''
        )

    def test_multiple_matches(self):
        with self.assertRaises(
                LdgReconcilerMoreThanOneMatchingAccount
        ) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    i: zerg            $-50',
                    '    a: checking up     $20      ; has comment',
                    '    a: checking down   $20',
                    '    a: checking out    $10',
                ],
                'checking'
            )
        self.assertEqual(
            str([
                'a: checking up',
                'a: checking down',
                'a: checking out'
            ]),
            str(e.exception)
        )
        self.assertEqual('', self.redirect.getvalue().rstrip())
        self.reset_redirect()
        with self.assertRaises(
                LdgReconcilerMoreThanOneMatchingAccount
        ) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    i: zerg            $-50',
                    '    a: checking up     $20      ; has comment',
                    '    a: checking down   $20',
                ],
                'checking'
            )
        self.assertEqual(
            str(['a: checking up', 'a: checking down']),
            str(e.exception)
        )
        self.assertEqual('', self.redirect.getvalue().rstrip())

    def test_multiple_matches_and_statuses(self):
        with self.assertRaises(
                LdgReconcilerMoreThanOneMatchingAccount
        ) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    i: zerg            $-50',
                    '  * a: checking up     $20      ; has comment',
                    '  ! a: checking down   $20',
                    '    a: checking out    $10',
                ],
                'checking'
            )
        self.assertEqual(
            str([
                'a: checking up',
                'a: checking down',
                'a: checking out'
            ]),
            str(e.exception)
        )
        # we don't print the error message for multiple statuses when
        # there are multiple matches; it's all blowing up anyway, and
        # a good chance it's because of the multiple matches that we
        # have multiple statuses
        self.assertEqual('', self.redirect.getvalue().rstrip())

