#!/usr/bin/env python

import time
import telnetlib
import re
import datetime
import json

class KST():
	def __init__(self, user, password, band):
		self.host = "www.on4kst.info"
		self.port = 23000
		self.user = user
		self.password = password
		self.band = band
		self.socket = self.connect()
                self.qsos = []

                self.get_users()

	def connect (self, tout=10):
		t = telnetlib.Telnet(self.host, self.port)
		tmax = time.time() + tout
		t.read_until('Login:', tout)
		t.write(self.user + '\n')
		t.read_until('Password:', tout)
		t.write(self.password + '\n')
		t.read_until('Your choice           :', tout)
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
        
        def get_users (self):
            self.socket.write('/show users\n')
            users_text = self.socket.read_until('Microwave chat', 10)
            for line in users_text.split('\n'):
                if line.find(self.user.upper()) != -1:
                    continue
                if len(line.strip()) == 0:
                    continue
                line = line.replace("\t", " ")
                call = line[:line.find(" ")]
                qso = dict(timestamp=time.strftime('%Y-%m-%d %H:%M:%S'), call=call, freq=None,
                                band='23cm', source='kst')
                if qso['call'].upper()[0] in '2MG':
                    self.qsos.append(qso)


	def parse_line (self, line):
		line_match = re.compile(r'^(\d{4})Z ([^ ]*) ([^>]*)> (.*)$')
		m = line_match.match(line)
		if m:
			time, call, extra, msg = m.groups()
			hours, minutes = [int(i) for i in [time[:2], time[2:]]]
			now = datetime.datetime.now()
			time = datetime.datetime(now.year, now.month, now.day, hours, minutes, 00)
			freq = None
			if all(c in '.1234567890mkhz' for c in extra.lower()):
				freq=extra
                        qso = dict(timestamp=time.strftime('%Y-%m-%d %H:%M:%S'), call=call, freq=freq,
					band='23cm', source='kst')
                        if qso['call'].upper()[0] in '2MG':
                            print qso
                            self.qsos.append(qso)

        def flush (self, fn='kst.json'):
            with file(fn, 'w') as f:
                f.write(json.dumps(self.qsos))

if __name__ == "__main__":
	k = KST('m0zrn', 'joe123', '3')
	k.socket.write('/show msg 10\n')
	for l in k.readlines():
		k.parse_line(l)
                k.flush()

