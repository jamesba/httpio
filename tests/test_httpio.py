from __future__ import print_function
from __future__ import absolute_import

import unittest
from unittest import TestCase

from httpio import HTTPIOFile
from io import IOBase, SEEK_CUR, SEEK_END

import mock
import random
import re

from six import int2byte, PY3


# 8 MB of random data for the HTTP requests to return
DATA = b''.join(int2byte(random.randint(0, 0xFF))
                for _ in range(0, 8*1024*1024))

OTHER_DATA = b''.join(int2byte(random.randint(0, 0xFF))
                      for _ in range(0, 8*1024*1024))

ASCII_LINES = ["Line0\n",
               "Line the first\n",
               "Line Returns\n",
               "Line goes forth"]
ASCII_DATA = b''.join(line.encode('ascii') for line in ASCII_LINES)


# The expected exception from unimplemented IOBase operations
IOBaseError = OSError if PY3 else IOError


class TestHTTPIOFile(TestCase):
    def setUp(self):
        self.patchers = {}
        self.mocks = {}
        self.patchers['Session'] = mock.patch("requests.Session")

        for key in self.patchers:
            self.mocks[key] = self.patchers[key].start()

        # Set up the dummy HTTP requests interface:
        _session = self.mocks['Session'].return_value

        self.data_source = DATA

        def _head(url, **kwargs):
            return mock.MagicMock(headers={'Content-Length':
                                           len(self.data_source),
                                           'Accept-Ranges':
                                           'bytes'})

        _session.head.side_effect = _head

        def _get(url, **kwargs):
            (start, end) = (None, None)
            if 'headers' in kwargs:
                if 'Range' in kwargs['headers']:
                    m = re.match(r'bytes=(\d+)-(\d+)',
                                 kwargs['headers']['Range'])
                    if m:
                        start = int(m.group(1))
                        end = int(m.group(2)) + 1

            return mock.MagicMock(content=self.data_source[start:end])

        _session.get.side_effect = _get

    def tearDown(self):
        for key in self.patchers:
            self.mocks[key] = self.patchers[key].stop()

    def test_implements_io_base(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertIsInstance(io, IOBase)

    def test_read_after_close_fails(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            pass
        with self.assertRaises(IOBaseError):
            io.read()

    def test_closed(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(hasattr(io, 'closed'))
            self.assertFalse(io.closed)
        self.assertTrue(io.closed)

    def test_fileno(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            with self.assertRaises(IOBaseError):
                io.fileno()

    def test_flush_dumps_cache(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.read(1024), DATA[:1024])
            self.data_source = OTHER_DATA
            io.seek(0)
            self.assertEqual(io.read(1024), DATA[:1024])
            io.flush()
            io.seek(0)
            self.assertEqual(io.read(1024), OTHER_DATA[:1024])

    def test_isatty(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertFalse(io.isatty())

    def test_read_gets_data(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            data = io.read(1024)
            self.assertEqual(data, DATA[0:1024])

    def test_read_gets_data_without_buffering(self):
        with HTTPIOFile('http://www.example.com/test/') as io:
            self.assertEqual(io.read(), DATA)

    def test_readable(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(io.readable())

    def test_readinto(self):
        b = bytearray(1536)
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.readinto(b), len(b))
            self.assertEqual(bytes(b), DATA[:1536])

    def test_readline(self):
        self.data_source = ASCII_DATA
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.readline().decode('ascii'),
                             ASCII_LINES[0])

    def test_readlines(self):
        self.data_source = ASCII_DATA
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual([line.decode('ascii') for line in io.readlines()],
                             [line for line in ASCII_LINES])

    def test_tell_starts_at_zero(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.tell(), 0)

    def test_seek_and_tell_match(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertEqual(io.seek(1536), 1536)
            self.assertEqual(io.tell(), 1536)

            self.assertEqual(io.seek(10, whence=SEEK_CUR), 1546)
            self.assertEqual(io.tell(), 1546)

            self.assertEqual(io.seek(-20, whence=SEEK_CUR), 1526)
            self.assertEqual(io.tell(), 1526)

            self.assertEqual(io.seek(-20, whence=SEEK_END), len(DATA) - 20)
            self.assertEqual(io.tell(), len(DATA) - 20)

    def test_random_access(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            io.seek(1536)
            self.assertEqual(io.read(1024), DATA[1536:2560])
            io.seek(10, whence=SEEK_CUR)
            self.assertEqual(io.read(1024), DATA[2570:3594])
            io.seek(-20, whence=SEEK_CUR)
            self.assertEqual(io.read(1024), DATA[3574:4598])
            io.seek(-1044, whence=SEEK_END)
            self.assertEqual(io.read(1024), DATA[-1044:-20])

    def test_seekable(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertTrue(io.seekable())

    def test_truncate(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            with self.assertRaises(IOBaseError):
                io.truncate()

    def test_write(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            with self.assertRaises(IOBaseError):
                io.write(DATA[:1024])

    def test_writable(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            self.assertFalse(io.writable())

    def test_writelines(self):
        with HTTPIOFile('http://www.example.com/test/', 1024) as io:
            with self.assertRaises(IOBaseError):
                io.writelines([line.encode('ascii') for line in ASCII_LINES])


if __name__ == "__main__":
    unittest.main()
