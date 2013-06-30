#!/usr/bin/python

"""unit test for schedulething.py"""

__author__ = 'scarpent'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'

import unittest

from datetime import datetime

from schedulething import ScheduleThing
from ledgerthing import LedgerThing


scheduleLinesTest = [
    '2013/06/29 lightning energy',
    '    ;; schedule ; monthly ; 12th ; ; auto',
    '    e: bills: electricity',
    '    a: checking up                          $-75'
]

class GetNextDate(unittest.TestCase):

    scheduleLineFileConfig = [';; scheduler ; enter 7 days ; preview 30 days']
    ScheduleThing.doFileConfig = True
    scheduleThingFileConfig = ScheduleThing(scheduleLineFileConfig)

    def testGetNextDate(self):

        scheduleLines = [
            '2013/06/05 lightning energy',
            '    ;; schedule ; monthly ; 12th ; ; auto',
            '    e: bills: electricity,'
            '    a: checking up                          $-75'
        ]

        scheduleThing = ScheduleThing(scheduleLines)
        expectedNextDate = LedgerThing.getDate('2013/06/12')

        self.assertEqual(
            expectedNextDate,
            scheduleThing._getNextDate(scheduleThing.thingDate)
        )

class GetWeekDay(unittest.TestCase):

    ScheduleThing.doFileConfig = False
    scheduleThing = ScheduleThing(scheduleLinesTest)

    def testGetWeekDay(self):
        self.assertEqual(-1, self.scheduleThing._getWeekDay())


class GetMonthDay(unittest.TestCase):

    ScheduleThing.doFileConfig = False
    scheduleThing = ScheduleThing(scheduleLinesTest)

    def testGetMonthDayNormal(self):
        """normal day is returned as the same day number"""
        testdate = datetime.strptime('2013/06/16', '%Y/%m/%d')
        self.assertEqual(5, self.scheduleThing._getMonthDay('5', testdate))

    def testGetMonthDayJuneEom(self):
        """eom for a 30-day month is 30"""
        testdate = datetime.strptime('2013/06/16', '%Y/%m/%d')
        self.assertEqual(
            30,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM, testdate)
        )

    def testGetMonthDayJulyEom(self):
        """eom for a 31-day month is 31"""
        testdate = datetime.strptime('2013/07/01', '%Y/%m/%d')
        self.assertEqual(
            31,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM, testdate)
        )

    def testGetMonthDayFebruaryEom(self):
        """eom for a non-leap year february is 28"""
        testdate = datetime.strptime('2013/02/05', '%Y/%m/%d')
        self.assertEqual(
            28,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM, testdate)
        )

    def testGetMonthDayLeapFebruaryEom(self):
        """eom for a leap year february is 29"""
        testdate = datetime.strptime('2012/02/05', '%Y/%m/%d')
        self.assertEqual(
            29,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM, testdate)
        )

    def testGetMonthDayJuneEom30(self):
        """eom30 for a 30-day month is 30"""
        testdate = datetime.strptime('2013/06/16', '%Y/%m/%d')
        self.assertEqual(
            30,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM30, testdate)
        )

    def testGetMonthDayJulyEom30(self):
        """eom30 for a 31-day month is 30"""
        testdate = datetime.strptime('2013/07/01', '%Y/%m/%d')
        self.assertEqual(
            30,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM30, testdate)
        )

    def testGetMonthDayFebruaryEom30(self):
        """eom30 for a non-leap year february is 28"""
        testdate = datetime.strptime('2013/02/05', '%Y/%m/%d')
        self.assertEqual(
            28,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM30, testdate)
        )

    def testGetMonthDayLeapFebruaryEom30(self):
        """eom for a leap year february is 29"""
        testdate = datetime.strptime('2012/02/05', '%Y/%m/%d')
        self.assertEqual(
            29,
            self.scheduleThing._getMonthDay(ScheduleThing.EOM30, testdate)
        )