##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""logging handler for tests that check logging output."""

import logging

class Handler(logging.Handler):
    """Handler for use with unittest.TestCase objects.

    The handler takes a TestCase instance as a constructor argument.
    It can be registered with one or more loggers and collects log
    records they generate.

    The assertLogsMessage() and failIfLogsMessage() methods can be
    used to check the logger output and causes the test to fail as
    appropriate.
    """

    def __init__(self, testcase, propagate=False):
        logging.Handler.__init__(self)
        self.records = []
        # loggers stores (logger, propagate) tuples
        self.loggers = []
        self.closed = False
        self.propagate = propagate
        self.testcase = testcase

    def close(self):
        """Remove handler from any loggers it was added to."""
        if self.closed:
            return
        for logger, propagate in self.loggers:
            logger.removeHandler(self)
            logger.propagate = propagate
        self.closed = True

    def add(self, name):
        """Add handler to logger named name."""
        logger = logging.getLogger(name)
        old_prop = logger.propagate
        logger.addHandler(self)
        if self.propagate:
            logger.propagate = 1
        else:
            logger.propagate = 0
        self.loggers.append((logger, old_prop))

    def emit(self, record):
        self.records.append(record)

    def assertLogsMessage(self, msg, level=None):
        for r in self.records:
            if r.getMessage() == msg:
                if level is not None and r.levelno == level:
                    return
        msg = "No log message contained %r" % msg
        if level is not None:
            msg += " at level %d" % level
        self.testcase.fail(msg)

    def failIfLogsMessage(self, msg):
        for r in self.records:
            if r.getMessage() == msg:
                self.testcase.fail("Found log message %r" % msg)
