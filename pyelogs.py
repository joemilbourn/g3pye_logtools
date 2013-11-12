from collections import defaultdict
import pandas as pd
from StringIO import StringIO
import os
from math import radians, degrees, sin, cos, atan2, floor
import pylab
import upoints
from numpy import dtype

class LogFile:
	def __init__ (self, path):
		self.path = path
		self.qsos = None
		self.load()

	def load (self):
		sections = defaultdict(str)
		section = None

		with file(self.path) as f:
			for line in f.readlines():
				if line[0] == "[":
					section = line[1:line.find(';')]
				else:
					sections[section] += line

		if 'REG1TEST' not in sections.keys():
			raise Exception('Missing preamble in file %s' % self.path)

		self.parse_preamble(sections['REG1TEST'])
		
		if 'QSORecords' in sections.keys():
			self.parse_qsos(sections['QSORecords'])

	def parse_preamble(self, preamble_str):
		self.preamble = {}
		for line in preamble_str.split('\n'):
			if line == "": continue
			k, v = line.strip().split("=")
			self.preamble[k] = v

	def parse_qsos (self, records_str):
		self.qsos = pd.read_csv(StringIO(records_str),
				sep=';', header=None,
				names = ['Date', 'Time', 'Call', 'N.1', 'TxRpt', 'TxSer',
					'RxRpt', 'RxSer', 'N.2', 'Loc', 'Points', 'N.4', 'N.5', 'N.6','N.7'])
		self.qsos['Band'] = self.preamble.get('PBand', None)

def find_ukac_logs (log_dir):
	logs = []
	for root, dirs, files in os.walk(log_dir):
		for f in files:
			if f.endswith('.txt') and f.find('PreContest') == -1:
				logs += [LogFile(os.path.join(root, f))]

	def is_ukac_p (log):
		return all([log.preamble['PCall'] == 'G3PYE/P',
			log.preamble['PSect'] == 'UKAC Restricted',
			log.preamble['PWWLo'] == 'JO02CE'])

	print "Found %d logs" % len(logs)
	logs = filter(is_ukac_p, logs)
	print "Found %d UKAC logs" % len(logs)
	df = pd.concat(l.qsos for l in logs)
	return df

if __name__ == "__main__":
	logs = find_ukac_logs('logs')
