##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
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
"""Support for testing logging code

If you want to test that your code generates proper log output, you
can create and install a handler that collects output:

  >>> handler = InstalledHandler('foo.bar')

The handler is installed into loggers for all of the names passed. In
addition, the logger level is set to 1, which means, log
everything. If you want to log less than everything, you can provide a
level keyword argument.  The level setting effects only the named
loggers.

Then, any log output is collected in the handler:

  >>> logging.getLogger('foo.bar').exception('eek')
  >>> logging.getLogger('foo.bar').info('blah blah')

  >>> for record in handler.records:
  ...     print record.name, record.levelname
  ...     print ' ', record.message
  foo.bar ERROR
    eek
  foo.bar INFO
    blah blah

A similar effect can be gotten by just printing the handler:

  >>> print handler
  foo.bar ERROR
    eek
  foo.bar INFO
    blah blah

After checking the log output, you need to uninstall the handler:

  >>> handler.uninstall()

At which point, the handler won't get any more log output.
Let's clear the handler:

  >>> handler.clear()
  >>> handler.records
  []

And then log something:
  
  >>> logging.getLogger('foo.bar').info('blah')

and, sure enough, we still have no output:
  
  >>> handler.records
  []
  
$Id: loggingsupport.py,v 1.1 2004/05/28 18:08:58 faassen Exp $
"""

import logging

class Handler(logging.Handler):

    def __init__(self, *names, **kw):
        logging.Handler.__init__(self)
        self.names = names
        self.records = []
        self.setLoggerLevel(**kw)

    def setLoggerLevel(self, level=1):
        self.level = level
        self.oldlevels = {}

    def emit(self, record):
        self.records.append(record)

    def clear(self):
        del self.records[:]

    def install(self):
        for name in self.names:
            logger = logging.getLogger(name)
            self.oldlevels[name] = logger.level
            logger.setLevel(self.level)
            logger.addHandler(self)

    def uninstall(self):
        for name in self.names:
            logger = logging.getLogger(name)
            logger.setLevel(self.oldlevels[name])
            logger.removeHandler(self)

    def __str__(self):
        return '\n'.join(
            [("%s %s\n  %s" %
              (record.name, record.levelname,
               '\n'.join([line
                          for line in record.message.split('\n')
                          if line.strip()])
               )
              )
              for record in self.records]
              )
        

class InstalledHandler(Handler):

    def __init__(self, *names):
        Handler.__init__(self, *names)
        self.install()
    
