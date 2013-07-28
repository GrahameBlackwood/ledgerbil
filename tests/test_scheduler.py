#!/usr/bin/python

"""unit test for scheduler.py"""

__author__ = 'scarpent'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'

from unittest import TestCase
from os import remove
from datetime import date
from dateutil.relativedelta import relativedelta

from scheduler import Scheduler
from schedulefile import ScheduleFile
from ledgerfile import LedgerFile
from ledgerthing import LedgerThing

from filetester import FileTester


class SchedulerRun(TestCase):

    def testRun(self):
        schedulefiledata = FileTester.readFile(FileTester.testschedulefile)
        lastmonth = date.today() - relativedelta(months=1)
        testdate = date(lastmonth.year, lastmonth.month, 15)
        schedulefiledata = schedulefiledata.replace(
            'TEST_DATE',
            LedgerThing.getDateString(testdate)
        )
        tempschedulefile = FileTester.writeToTempFile(
            FileTester.testschedulefile,
            schedulefiledata
        )

        schedulefile = ScheduleFile(tempschedulefile)

        templedgerfile = FileTester.createTempFile('')
        ledgerfile = LedgerFile(templedgerfile)

        scheduler = Scheduler(ledgerfile, schedulefile)
        scheduler.run()

        ledgerfile.writeFile()
        schedulefile.writeFile()

        schedulefile_actual = FileTester.readFile(tempschedulefile)

        schedulefileafterdata = FileTester.readFile(
            FileTester.testschedulefileafter
        )
        schedulefile_expected = schedulefileafterdata.replace(
            'FIRST_DATE',
            LedgerThing.getDateString(testdate + relativedelta(months=2))
        ).replace(
            'SECOND_DATE',
            LedgerThing.getDateString(testdate + relativedelta(months=3))
        ).replace(
            'THIRD_DATE',
            LedgerThing.getDateString(testdate + relativedelta(months=6))
        )

        remove(templedgerfile)
        remove(tempschedulefile)

        # todo: check ledger file also?

        self.assertEqual(
            schedulefile_expected,
            schedulefile_actual
        )
