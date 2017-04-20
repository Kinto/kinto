##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Data Chunk Receiver
"""

from waitress.utilities import find_double_newline

from waitress.utilities import BadRequest

class FixedStreamReceiver(object):

    # See IStreamConsumer
    completed = False
    error = None

    def __init__(self, cl, buf):
        self.remain = cl
        self.buf = buf

    def __len__(self):
        return self.buf.__len__()
    
    def received(self, data):
        'See IStreamConsumer'
        rm = self.remain
        if rm < 1:
            self.completed = True # Avoid any chance of spinning
            return 0
        datalen = len(data)
        if rm <= datalen:
            self.buf.append(data[:rm])
            self.remain = 0
            self.completed = True
            return rm
        else:
            self.buf.append(data)
            self.remain -= datalen
            return datalen

    def getfile(self):
        return self.buf.getfile()

    def getbuf(self):
        return self.buf

class ChunkedReceiver(object):

    chunk_remainder = 0
    control_line = b''
    all_chunks_received = False
    trailer = b''
    completed = False
    error = None

    # max_control_line = 1024
    # max_trailer = 65536

    def __init__(self, buf):
        self.buf = buf

    def __len__(self):
        return self.buf.__len__()

    def received(self, s):
        # Returns the number of bytes consumed.
        if self.completed:
            return 0
        orig_size = len(s)
        while s:
            rm = self.chunk_remainder
            if rm > 0:
                # Receive the remainder of a chunk.
                to_write = s[:rm]
                self.buf.append(to_write)
                written = len(to_write)
                s = s[written:]
                self.chunk_remainder -= written
            elif not self.all_chunks_received:
                # Receive a control line.
                s = self.control_line + s
                pos = s.find(b'\n')
                if pos < 0:
                    # Control line not finished.
                    self.control_line = s
                    s = ''
                else:
                    # Control line finished.
                    line = s[:pos]
                    s = s[pos + 1:]
                    self.control_line = b''
                    line = line.strip()
                    if line:
                        # Begin a new chunk.
                        semi = line.find(b';')
                        if semi >= 0:
                            # discard extension info.
                            line = line[:semi]
                        try:
                            sz = int(line.strip(), 16) # hexadecimal
                        except ValueError: # garbage in input
                            self.error = BadRequest(
                                'garbage in chunked encoding input')
                            sz = 0
                        if sz > 0:
                            # Start a new chunk.
                            self.chunk_remainder = sz
                        else:
                            # Finished chunks.
                            self.all_chunks_received = True
                    # else expect a control line.
            else:
                # Receive the trailer.
                trailer = self.trailer + s
                if trailer.startswith(b'\r\n'):
                    # No trailer.
                    self.completed = True
                    return orig_size - (len(trailer) - 2)
                elif trailer.startswith(b'\n'):
                    # No trailer.
                    self.completed = True
                    return orig_size - (len(trailer) - 1)
                pos = find_double_newline(trailer)
                if pos < 0:
                    # Trailer not finished.
                    self.trailer = trailer
                    s = b''
                else:
                    # Finished the trailer.
                    self.completed = True
                    self.trailer = trailer[:pos]
                    return orig_size - (len(trailer) - pos)
        return orig_size

    def getfile(self):
        return self.buf.getfile()

    def getbuf(self):
        return self.buf
