##############################################################################
#
# Copyright (c) 2012 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################


class DummyFile(object):
    def __init__(self):
        self._lines = []
    def write(self, text):
        self._lines.append(text)
    def writelines(self, lines):
        self._lines.extend(lines)


class DummyLogger(object):
    def __init__(self):
        self._clear()
    def _clear(self):
        self._log = []
    def log(self, level, msg, *args, **kw):
        if args:
            self._log.append((level, msg % args))
        elif kw:
            self._log.append((level, msg % kw))
        else:
            self._log.append((level, msg))
    def debug(self, msg, *args, **kw):
        self.log('debug', msg, *args, **kw)
    def error(self, msg, *args, **kw):
        self.log('error', msg, *args, **kw)
    def critical(self, msg, *args, **kw):
        self.log('critical', msg, *args, **kw)


class Monkey(object):
    # context-manager for replacing module names in the scope of a test.
    def __init__(self, module, **kw):
        self.module = module
        self.to_restore = dict([(key, getattr(module, key)) for key in kw])
        for key, value in kw.items():
            setattr(module, key, value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, value in self.to_restore.items():
            setattr(self.module, key, value)

def assertRaisesEx(e_type, checked, *args, **kw):
    try:
        checked(*args, **kw)
    except e_type as e:
        return e
    raise AssertionError("Didn't raise: %s" % e_type.__name__)
