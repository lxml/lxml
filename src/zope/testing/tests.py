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
"""XXX short summary goes here.

$Id: tests.py,v 1.1 2004/05/28 18:08:59 faassen Exp $
"""
import unittest
from zope.testing.doctestunit import DocTestSuite


def test_suite():
    # XXX disable this as we get some weird logging messages in output
    pass
    #return unittest.TestSuite((
    #    DocTestSuite('zope.testing.loggingsupport'),
    #    ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

