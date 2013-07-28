#!/usr/bin/python

"""scheduler"""

from __future__ import print_function

__author__ = 'scarpent'
__license__ = 'gpl v3 or greater'
__email__ = 'scottc@movingtofreedom.org'

from schedulething import ScheduleThing


class Scheduler(object):

    def __init__(self, ledgerfile, schedulefile):
        self.ledgerfile = ledgerfile
        self.schedulefile = schedulefile

    def run(self):

        if ScheduleThing.enterDays == ScheduleThing.NO_DAYS:
            return

        self.schedulefile.sort()

        # todo: test for invalid schedule things (should blow up)

        for schedulething in self.schedulefile.things:

            if schedulething.firstThing:
                continue

            self.ledgerfile.addThings(schedulething.getScheduledEntries())

        self.schedulefile.sort()
