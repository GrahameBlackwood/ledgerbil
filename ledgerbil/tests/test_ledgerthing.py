from datetime import date
from unittest import TestCase

import pytest

from ..ledgerbilexceptions import LdgReconcilerError
from ..ledgerthing import (
    REC_CLEARED, REC_PENDING, REC_UNCLEARED, UNSPECIFIED_PAYEE, LedgerThing
)
from .helpers import Redirector


def test_repr():
    lines = [
        '2018/01/08 blah',
        '    e: xyz',
        '    l: abc         $-10',
    ]
    thing = LedgerThing(lines)
    assert repr(thing) == f'LedgerThing({lines}, reconcile_account=None)'
    assert isinstance(eval(repr(thing)), LedgerThing)


def test_str():
    lines = [
        '2018/01/08 blah',
        '    e: xyz',
        '    l: abc         $-10',
    ]
    thing = LedgerThing(lines)
    assert str(thing) == '\n'.join(lines)


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
            '2016/02/04 (123)someone',
            date(2016, 2, 4), '123', 'someone'
        )
        # todo: this is invalid in ledger; see if we can exclude?
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

        # todo: add tests for requiring two spaces after payee;
        #       test payee names with spaces


class GetLines(Redirector):

    def test_get_lines(self):
        """lines can be entered and retrieved as is"""
        lines = ('abc\n', 'xyz\n')
        thing = LedgerThing(list(lines))
        self.assertEqual(lines, tuple(thing.get_lines()))

    def test_get_lines_dates(self):
        # same date
        lines = ('2016/10/24 blah', '  e: blurg')
        thing = LedgerThing(list(lines))
        self.assertEqual(lines, tuple(thing.get_lines()))
        # change date
        thing.thing_date = date(1998, 3, 8)
        self.assertEqual(
            ['1998/03/08 blah', '  e: blurg'],
            thing.get_lines()
        )

    def test_get_lines_reconciled_status_no_change(self):
        # uncleared
        lines = ('2016/10/24 glob', '  e: blurg', '    a: smurg   $-25')
        thing = LedgerThing(list(lines), reconcile_account='smurg')
        self.assertEqual(lines, tuple(thing.get_lines()))
        # pending
        lines = ('2016/10/24 glob', '  ! e: blurg', '  a: smurg   $-25')
        thing = LedgerThing(list(lines), reconcile_account='blurg')
        self.assertEqual(lines, tuple(thing.get_lines()))
        # cleared
        lines = ('2016/10/24 glob', '  * e: blurg', '  a: smurg   $-25')
        thing = LedgerThing(list(lines), reconcile_account='blurg')
        self.assertEqual(lines, tuple(thing.get_lines()))

    def test_get_lines_indent_change(self):
        # status doesn't change, but indent does due to standard
        # uncleared
        lines = (
            '2016/10/24 glob',
            '  ; might as well test comment handling, too',
            '  e: blurg',
            '  a: smurg   $-25',
        )
        thing = LedgerThing(list(lines), reconcile_account='smurg')
        expected = (
            '2016/10/24 glob',
            '  ; might as well test comment handling, too',
            '  e: blurg',
            '    a: smurg   $-25',
        )
        self.assertEqual(expected, tuple(thing.get_lines()))
        # pending
        lines = ('2016/10/24 glob', ' !e: blurg', '  a: smurg   $-25')
        thing = LedgerThing(list(lines), 'blurg')
        self.assertEqual(
            ('2016/10/24 glob', '  ! e: blurg', '  a: smurg   $-25'),
            tuple(thing.get_lines())
        )
        # cleared
        lines = ('2016/10/24 glob', ' *e: blurg', '  a: smurg   $-25')
        thing = LedgerThing(list(lines), 'blurg')
        self.assertEqual(
            ('2016/10/24 glob', '  * e: blurg', '  a: smurg   $-25'),
            tuple(thing.get_lines())
        )

    def test_get_lines_status_changes(self):
        # uncleared -> pending
        lines = ('2016/10/24 abc', '  e: xyz', '     a: smurg   $-25')
        thing = LedgerThing(list(lines), reconcile_account='smurg')
        thing.rec_status = REC_PENDING
        self.assertEqual(
            ('2016/10/24 abc', '  e: xyz', '  ! a: smurg   $-25'),
            tuple(thing.get_lines())
        )
        # pending -> cleared
        thing.rec_status = REC_CLEARED
        self.assertEqual(
            ('2016/10/24 abc', '  e: xyz', '  * a: smurg   $-25'),
            tuple(thing.get_lines())
        )
        # cleared -> uncleared
        thing.rec_status = REC_UNCLEARED
        self.assertEqual(
            ('2016/10/24 abc', '  e: xyz', '    a: smurg   $-25'),
            tuple(thing.get_lines())
        )

    def test_get_lines_status_change_multiple_lines(self):
        lines = (
            '2016/10/24 glob',
            '  ; might as well test comment handling, too',
            '                 e: blurg   $50',
            ' a: smurg',
            '    a: smurg   $-25',
        )
        thing = LedgerThing(list(lines), reconcile_account='smurg')
        thing.rec_status = REC_PENDING
        expected = (
            '2016/10/24 glob',
            '  ; might as well test comment handling, too',
            '                 e: blurg   $50',
            '  ! a: smurg',
            '  ! a: smurg   $-25',
        )
        self.assertEqual(
            expected,
            tuple(thing.get_lines())
        )
        self.assertEqual('', self.redirect.getvalue().rstrip())

    def test_get_lines_reconcile_account_is_regex(self):
        # uncleared -> pending
        lines = ('2016/10/24 abc', '  e: xyz', '     a: smurg   $-25')
        thing = LedgerThing(list(lines), reconcile_account='sm.[a-z]g')
        thing.rec_status = REC_PENDING
        self.assertEqual(
            ('2016/10/24 abc', '  e: xyz', '  ! a: smurg   $-25'),
            tuple(thing.get_lines())
        )
        thing.rec_status = REC_CLEARED
        self.assertEqual(
            ('2016/10/24 abc', '  e: xyz', '  * a: smurg   $-25'),
            tuple(thing.get_lines())
        )
        thing.rec_status = REC_UNCLEARED
        self.assertEqual(
            ('2016/10/24 abc', '  e: xyz', '    a: smurg   $-25'),
            tuple(thing.get_lines())
        )


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
        # todo: this is invalid in ledger; see if we can exclude
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

    def verify_reconcile_vars(self,
                              lines,
                              account='not given GyibM3nob1kwJ',
                              expected_match=None,
                              expected_amount=0.0,
                              expected_status=None):

        if account == 'not given GyibM3nob1kwJ':
            t = LedgerThing(lines)
            account = None
        else:
            t = LedgerThing(lines, account)

        if account is None:
            self.assertIsNone(t.rec_account)
        else:
            self.assertEqual(account, t.rec_account)

        self.assertEqual(expected_match, t.rec_account_matched)
        self.assertEqual(expected_amount, t.rec_amount)
        self.assertEqual(expected_status, t.rec_status)

    def test_reconcile_not_a_transaction(self):
        # not reconciling
        self.verify_reconcile_vars(['; some comment'])
        self.verify_reconcile_vars(['; some comment'], None)
        # reconciling
        self.verify_reconcile_vars(['; some comment'], 'checking', )

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
            expected_match='a: checking',
            expected_amount=-25
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '    a: checking   $50  ; this one has a comment',
            ],
            account='check',
            expected_match='a: checking',
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
            expected_match='a: checking',
            expected_amount=-25
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '    a: checking          ; this one has a comment',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=50
        )

    def test_two_spaces_ends_account(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: blah',
                '    a: check checking  $25',
                '    a: check checking  $25',
            ],
            account='check',
            expected_match='a: check checking',
            expected_amount=50
        )

    def test_one_space_does_not_end_account(self):
        with self.assertRaises(LdgReconcilerError) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    a: checking up $20',
                    '    a: checking up  $20',
                ],
                'checking'
            )
        expected = ('More than one matching account:\n'
                    '    a: checking up\n    a: checking up $20')
        assert str(e.exception) == expected

    def test_comma_in_amount(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $1000',
                '    a: checking   $-1,000',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-1000
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
            expected_match='a: checking',
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
            expected_match='a: checking',
            expected_amount=-25,
            expected_status=REC_PENDING
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  * a: checking   $-25',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-25,
            expected_status=REC_CLEARED
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  ! a: checking   $-25        ; with comment',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-25,
            expected_status=REC_PENDING
        )

    def test_status_with_math(self):

        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $25',
                '  ! a: checking',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-25,
            expected_status=REC_PENDING
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    i: zerg       $-50',
                '  * a: checking          ; this one has a comment',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=50,
            expected_status=REC_CLEARED
        )

    def test_multiple_statuses_raises_exception(self):
        with self.assertRaises(LdgReconcilerError) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    i: zerg            $-40',
                    '  * a: checking up     $20      ; has comment',
                    '  ! a: checking up     $20',
                ],
                'checking'
            )
        self.assertEqual(
            'Unhandled multiple statuses: 2016/10/23 blah',
            str(e.exception)
        )
        self.assertEqual('', self.redirect.getvalue().rstrip())
        self.reset_redirect()
        with self.assertRaises(LdgReconcilerError) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    i: zerg            $-40',
                    '    a: checking up     $20      ; has comment',
                    '  ! a: checking up     $20',
                ],
                'checking'
            )
        self.assertEqual(
            'Unhandled multiple statuses: 2016/10/23 blah',
            str(e.exception)
        )

    def test_multiple_matches_raises_exception(self):
        with self.assertRaises(LdgReconcilerError) as e:
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
        expected = ('More than one matching account:\n'
                    '    a: checking down\n    a: checking up')
        assert str(e.exception) == expected
        self.reset_redirect()
        with self.assertRaises(LdgReconcilerError) as e:
            LedgerThing(
                [
                    '2016/10/23 blah',
                    '    i: zerg            $-50',
                    '    a: checking up     $20      ; has comment',
                    '    a: checking down   $20',
                ],
                'checking'
            )
        assert str(e.exception) == expected

    def test_multiple_matches_and_statuses_raises_exception(self):
        with self.assertRaises(LdgReconcilerError) as e:
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
        expected = ('More than one matching account:\n'
                    '    a: checking down\n    a: checking up')
        assert str(e.exception) == expected

    def test_regex_for_account_match(self):
        thing = LedgerThing(
            [
                '2016/10/23 blah',
                '    i: zerg            $-50',
                '    a: checking up     $20      ; has comment',
                '    a: checking        $20',
                '    a: checking out    $10',
            ],
            'checking$'
        )
        assert thing.rec_account_matched == 'a: checking'
        assert thing.rec_amount == 20

    def test_multiple_lines_for_same_account(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $35',
                '    a: checking',
                '    a: checking   $-25'
            ],
            account='a: checking',
            expected_match='a: checking',
            expected_amount=-35
        )
        self.assertEqual('', self.redirect.getvalue().rstrip())
        # matching statuses should be okay
        self.reset_redirect()
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      $35',
                '  ! a: checking',
                '  ! a: checking   $-25'
            ],
            account='a: checking',
            expected_match='a: checking',
            expected_amount=-35,
            expected_status=REC_PENDING
        )
        self.assertEqual('', self.redirect.getvalue().rstrip())

    def test_more_transactions_and_math(self):
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      ($25 * 1.07275)',
                '    e: glerb      $15.67',
                '    a: checking                       ; todo',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-42.48875
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blah',
                '    e: blurg      ( $25*1.07275 )   ; comment',
                '    e: glerb      ($15 * (1 + 8))',
                '    a: checking                       ; todo',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-161.81875
        )
        self.verify_reconcile_vars(
            [
                '2016/10/23 blahgage',
                '    e: interest      $50',
                '    l: mortgage r4   ($79.99 + $50)',
                '    a: checking',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=-179.99
        )

    def test_share_multiplication_with_math(self):
        self.verify_reconcile_vars(
            [
                '2018/06/07 money',
                '    a: investment: blerg      -10.5 xyz @ $1.25',
                '    a: investment: cash',
            ],
            account='cash',
            expected_match='a: investment: cash',
            expected_amount=13.125
        )
        self.verify_reconcile_vars(
            [
                '2018/06/07 money',
                '    a: investment: blerg      1,000 xyz @ $1.25',
                '    a: investment: cash',
            ],
            account='cash',
            expected_match='a: investment: cash',
            expected_amount=-1250
        )

    def test_entry_comments(self):
        self.verify_reconcile_vars(
            [
                '2016/11/24 blah',
                '    i: blurg',
                '    a: checking  $10  ; comment',
                '    a: checking  $10 ; comment',
                '    a: checking  $10; comment',
                '    a: checking  ($5 * 2)  ; comment',
                '    a: checking  ($5 * 2) ; comment',
                '    a: checking  ($5 * 2); comment',
            ],
            account='check',
            expected_match='a: checking',
            expected_amount=60
        )

    def test_statuses(self):
        thing = LedgerThing(
            [
                '2016/10/23 blah',
                '    e: blurg      $10',
                '    e: glerb      $10',
                '    a: checking',
            ],
            'checking'
        )
        self.assertFalse(thing.is_pending())
        self.assertFalse(thing.is_cleared())
        thing.set_pending()
        self.assertTrue(thing.is_pending())
        self.assertFalse(thing.is_cleared())
        thing.set_cleared()
        self.assertFalse(thing.is_pending())
        self.assertTrue(thing.is_cleared())
        thing.set_uncleared()
        self.assertFalse(thing.is_pending())
        self.assertFalse(thing.is_cleared())


def test_mixed_shares_and_non_shares_raises_exception():
    """should fail if shares encountered last"""
    lines = [
        '2018/01/08 blah',
        '    a: xyz',
        '    a: xyz  1.234 abc @ $10',
    ]
    with pytest.raises(LdgReconcilerError) as excinfo:
        LedgerThing(lines, reconcile_account='xyz')
    expected = 'Unhandled shares with non-shares:\n{}'.format('\n'.join(lines))
    assert str(excinfo.value) == expected


def test_mixed_shares_and_non_shares_raises_exception_too():
    """should fail if non-shares encountered last"""
    lines = [
        '2018/01/08 blah',
        '    a: xyz  1.234 abc @ $10',
        '    a: xyz',
    ]
    with pytest.raises(LdgReconcilerError) as excinfo:
        LedgerThing(lines, reconcile_account='xyz')
    expected = 'Unhandled shares with non-shares:\n{}'.format('\n'.join(lines))
    assert str(excinfo.value) == expected


def test_shares():
    lines = [
        '2018/01/08 blah',
        '    a: xyz  1.234 abc @ $10',
        '    a: abc',
    ]
    thing = LedgerThing(lines, reconcile_account='xyz')
    assert thing.rec_is_shares is True
    assert thing.rec_amount == 1.234


def test_more_shares():
    lines = [
        '2018/01/08 blah',
        '    a: xyz  1.234 abc @ $10',
        '    a: xyz  -0.234 abc',
        '    a: abc',
    ]
    thing = LedgerThing(lines, reconcile_account='xyz')
    assert thing.rec_is_shares is True
    assert thing.rec_amount == 1


def test_even_more_shares():
    lines = [
        '2018/01/08 blah',
        '    a: xyz  1.000 abc@ $10',
        '    a: xyz  2.000 abc @$10',
        '    a: xyz  4.000 abc@$10',
        '    a: abc',
    ]
    thing = LedgerThing(lines, reconcile_account='xyz')
    assert thing.rec_is_shares is True
    assert thing.rec_amount == 7


def test_mixed_symbols_raises_exception():
    lines = [
        '2018/01/08 blah',
        '    a: xyz  1.234 abc @ $10',
        '    a: xyz  4.321 abc @ $10',
        '    a: xyz  5.678 qqq @ $15',
    ]
    with pytest.raises(LdgReconcilerError) as excinfo:
        LedgerThing(lines, reconcile_account='xyz')
    expected = "Unhandled multiple symbols: {symbols}\n{lines}".format(
        symbols=['abc', 'qqq'],
        lines='\n'.join(lines)
    )
    assert str(excinfo.value) == expected


def test_lines_is_different_than_get_lines_when_status_changes():
    lines = [
        '2018/01/08 blah',
        '    e: xyz',
        '    l: abc         $-10',
    ]
    lines_with_status = [
        '2018/01/08 blah',
        '    e: xyz',
        '  ! l: abc         $-10',
    ]
    thing = LedgerThing(lines, reconcile_account='abc')
    thing.rec_status = REC_PENDING
    assert thing.lines == lines
    assert thing.get_lines() == lines_with_status
    assert thing.lines != thing.get_lines()
