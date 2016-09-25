#!/usr/bin/python

"""objects in ledger file: transactions, etc"""

from __future__ import print_function

import re

from copy import copy
from datetime import date
from dateutil.relativedelta import relativedelta
from calendar import monthrange

from ledgerthing import LedgerThing
from ledgerbilexceptions import *


__author__ = 'scarpent'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'


class ScheduleThing(LedgerThing):

    doFileConfig = True

    NO_DAYS = 0
    enterDays = NO_DAYS

    entryBoundaryDate = None

    LINE_FILE_CONFIG = 0
    LINE_DATE = 0
    LINE_SCHEDULE = 1
    INTERVAL_WEEK = 'weekly'
    INTERVAL_MONTH = 'monthly'
    # todo: one time schedule
    EOM = 'eom'
    EOM30 = 'eom30'
    SEPARATOR = ';'
    THING_CONFIG_LABEL = 'schedule'

    def __init__(self, lines):
        self.firstThing = False
        self.isScheduleThing = False
        self.intervalUom = ''    # month or week
        self.days = []           # e.g. 5, 15, eom, eom30
        self.interval = 1        # e.g. 1 = every month, 2 = every other

        super(ScheduleThing, self).__init__(lines)

        if ScheduleThing.doFileConfig:
            self._handleFileConfig(
                lines[ScheduleThing.LINE_FILE_CONFIG]
            )
            self.firstThing = True
            ScheduleThing.doFileConfig = False
            return

        self._handleThingConfig(lines[ScheduleThing.LINE_SCHEDULE])

    # file level config looks like this:
    # ;; scheduler ; enter N days
    # enter is optional
    def _handleFileConfig(self, line):

        configRegex = r'''(?x)                  # verbose mode
            ^                                   # line start
            \s*;;\s*scheduler\s*                # required
            (?:                                 # non-capturing
                ;\s*enter\s+(\d+)\s+days?\s*    # days ahead to enter trans
            )?                                  # optional
            (?:\s*;.*)?                         # optional ending semi-colon
            $                                   # line end     \ and comment
            '''

        # capturing groups
        ENTER_DAYS = 1

        match = re.match(configRegex, line)
        if not match:
            raise LdgScheduleFileConfigError(
                'Invalid schedule file config:\n%s\nExpected:\n'
                ';; scheduler ; enter N days'
                % line
            )

        if match.group(ENTER_DAYS):
            ScheduleThing.enterDays = int(match.group(ENTER_DAYS))

            if ScheduleThing.enterDays < 1:
                ScheduleThing.enterDays = ScheduleThing.NO_DAYS

        ScheduleThing.entryBoundaryDate = (
            date.today() + relativedelta(days=ScheduleThing.enterDays)
        )

        print('\nSchedule file (enter days = {days}):\n'.format(
            days=ScheduleThing.enterDays
        ))

    def _handleThingConfig(self, line):
        """
        @type line: string
        """

        CFG_LABEL = 0
        INTERVAL_UOM = 1
        DAYS = 2
        INTERVAL = 3

        # ';; schedule ; monthly ; 12th 21st eom; 3 ; auto'
        #        -->
        # ['', '', 'schedule', 'monthly', '12th 21st eom', '3', 'auto']
        configitems = [x.strip() for x in line.split(ScheduleThing.SEPARATOR)]

        if len(configitems) < 4:
            raise LdgScheduleThingParametersError(
                'Invalid schedule thing config:\n%s\nNot enough parameters'
                % line
            )

        del configitems[0:2]  # remove empty strings from opening ;;

        # now: ['schedule', 'monthly', '12th 21st eom', '3', 'auto']

        if configitems[CFG_LABEL].lower() != ScheduleThing.THING_CONFIG_LABEL:
            raise LdgScheduleThingLabelError(
                'Invalid schedule thing config:\n%s\n"%s" label not found '
                'in expected place.\n'
                % (line, ScheduleThing.THING_CONFIG_LABEL),
            )

        intervalUomRegex = (
            '(weekly|monthly|bimonthly|quarterly|biannual|yearly)'
        )

        match = re.match(intervalUomRegex, configitems[INTERVAL_UOM])
        if not match:
            raise LdgScheduleUnrecognizedIntervalUom(
                'Invalid schedule thing config:\n%s\nInterval UOM "%s"'
                'not recognized. Supported UOMs: weekly, monthly,'
                'bimonthly, quarterly, biannual, yearly.'
                % (line, configitems[INTERVAL_UOM])
            )

        intervaluom = match.group(1).lower()

        # schedule must have minimum two items; now let's make sure optional
        # fields are referenceable

        for x in range(len(configitems), 4):
            configitems.append('')

        if not configitems[DAYS].strip():
            configitems[DAYS] = str(self.thingDate.day)

        match = re.match('''[^\d]*(\d+).*''', configitems[INTERVAL])
        interval = 1
        if match:
            interval = int(match.group(1))

        if intervaluom == 'bimonthly':
            interval *= 2
        elif intervaluom == 'quarterly':
            interval *= 3
        elif intervaluom == 'biannual':
            interval *= 6
        elif intervaluom == 'yearly':
            interval *= 12

        if intervaluom != ScheduleThing.INTERVAL_WEEK:
            intervaluom = ScheduleThing.INTERVAL_MONTH

        self.interval = interval
        self.intervalUom = intervaluom

        # todo: for monthly: the day date; for weekly: the day name
        # todo: parse that as day names, but for now, use ints
        # (if day < 1, consider an inactive thing)
        dayString = configitems[DAYS].lower()
        self.days = []
        daysRegex = '(\d+|eom(?:\d\d?)?)'
        for match in re.finditer(daysRegex, dayString):
            # convert to ints where possible so will sort out correctly
            try:
                theday = int(match.groups()[0])
            except ValueError:
                theday = match.groups()[0]

            self.days.append(theday)

        self.days.sort()
        # todo: look for more than one eom and raise error?
        # todo: validation if a date is picked that is too
        #       large for some months (maybe force eom for 28-31???

        # todo: take out schedule line and put it into var
        # override thing getter to put it back in (standard raw lines
        # will have it, but for adding to ledger, no)

    def getScheduledEntries(self):

        entries = []

        if self.thingDate > ScheduleThing.entryBoundaryDate:
            return entries

        entries.append(self._getEntryThing())

        while True:
            self.thingDate = self._getNextDate(self.thingDate)

            if self.thingDate > ScheduleThing.entryBoundaryDate:
                break

            entries.append(self._getEntryThing())

        return entries

    def _getEntryThing(self):
        """
        @rtype: LedgerThing
        """
        entryLines = copy(self.lines)
        del entryLines[ScheduleThing.LINE_SCHEDULE]
        entryLines[ScheduleThing.LINE_DATE] = re.sub(
            self.DATE_REGEX,
            self.getDateString(self.thingDate),
            entryLines[ScheduleThing.LINE_DATE]
        )
        print(
            '\n%s\n%s\n' % (
                entryLines[ScheduleThing.LINE_DATE],
                self.lines[ScheduleThing.LINE_SCHEDULE]
            )
        )
        return LedgerThing(entryLines)

    def _getNextDate(self, previousdate):
        """
        @type previousdate: date
        @rtype: date
        """
        if self.intervalUom == ScheduleThing.INTERVAL_MONTH:

            # first see if any scheduled days remaining in same month
            for scheduleday in self.days:
                scheduleday = self._getMonthDay(scheduleday, previousdate)
                # compare with greater so we don't keep matching the same
                if scheduleday > previousdate.day:
                    return self._getSafeDate(previousdate, scheduleday)

            # advance to next month (by specified interval)

            nextdate = previousdate + relativedelta(months=self.interval)

            return self._getSafeDate(
                nextdate,
                self._getMonthDay(self.days[0], nextdate)
            )

        if self.intervalUom == ScheduleThing.INTERVAL_WEEK:
            # todo: handle day of week stuff, for now this will work
            # fine for basic once a week or once every N weeks stuff
            return previousdate + relativedelta(weeks=self.interval)

    # handle situations like 8/31 -> 9/31 (back up to 9/30)
    def _getSafeDate(self, thedate, theday):
        try:
            return date(thedate.year, thedate.month, theday)
        except ValueError:
            # day is out of range for month, so we'll get the last day of month
            # (may be unlikely now that we check lastDayOfMonth in _getMonthDay)
            return date(
                thedate.year,
                thedate.month,
                monthrange(thedate.year, thedate.month)[1]
            )

    # knows how to handle "eom"
    def _getMonthDay(self, scheduleday, currentdate):
        """
        @type scheduleday: str
        @type currentdate: date
        @rtype: int
        """

        lastDayOfMonth = monthrange(currentdate.year, currentdate.month)[1]

        # todo: create a monthly test case with days = 15, 30, and run it through February
        #       was seeing a bug where 30 would continually be greater than the safe date of 28
        #       and we'd get stuck repeating 2/28 for the entry (normally would be using
        #       eom now for end of month stuff, but should still be able to handle...
        if str(scheduleday).isdigit():
            if int(scheduleday) > lastDayOfMonth:
                return lastDayOfMonth
            else:
                return int(scheduleday)

        # todo, maybe: option to move date if a weekend

        if scheduleday == self.EOM:
            return lastDayOfMonth

        if scheduleday == '%s%s' % (self.EOM, '30'):
            if lastDayOfMonth >= 30:
                return 30
            else:
                return lastDayOfMonth  # february

    def _getWeekDay(self):
        return -1
