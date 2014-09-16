#!/usr/bin/env python

import time
import telnetlib
import re
import datetime
from spot import SpotSource

class KST(SpotSource):
    def __init__(self, user, password, band):
        self.interval = 120
        self.ttl = self.interval * 3
        self.band = 23
        self.name = 'kst'
        SpotSource.__init__ (self)

        self.host = "www.on4kst.info"
        self.port = 23000
        self.user = user
        self.password = password
        self.band = '3'
        
    def connect (self, tout=10):
        t = telnetlib.Telnet(self.host, self.port)
        tmax = time.time() + tout * 5
        t.read_until('Login:', tout)
        t.write(self.user + '\n')
        t.read_until('Password:', tout)
        t.write(self.password + '\n')
        t.read_until('Your choice       :', tout)
        t.write(self.band + '\n')
        t.read_until('Microwave chat>', tout)
        if time.time() > tmax:
            t = None
            print "Timed out connecting to kst."
        return t

    def readlines (self):
        buf = ""
        while True:
            eol = buf.find('\n')
            if eol != -1:
                yield buf[:eol]
                buf = buf[eol+1:]
            buf += self.socket.read_some()
    
    def update (self):
        self.socket = self.connect()
        self.socket.write('/show users\n')
        users_text = self.socket.read_until('Microwave chat', 10)
        for line in users_text.split('\n'):
            if line.find(self.user.upper()) != -1:
                continue
            if len(line.strip()) == 0:
                continue
            line = line.replace("\t", " ")
            call = line[:line.find(" ")]
            self.add_spot (call=call,
                    frequency=1296.0,
                    spotter=None)

if __name__ == "__main__":
    k = KST('m0zrn', 'joe123', '3')
    k.update()
    k.print_lines()
