from collections import defaultdict, Counter
import pandas as pd
from StringIO import StringIO
import os
from math import radians, degrees, sin, cos, atan2, floor
import pylab
import upoints
from numpy import dtype
import re
import clint

def bearing (to_loc, from_loc='JO02CE'):
	from_loc, to_loc = [upoints.point.Point(
		*upoints.utils.from_grid_locator(x)) for x in [from_loc, to_loc]]
	return from_loc.bearing(to_loc)

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
	df['bearing'] = df['Loc'].apply(bearing)
	return df

def result_formatter (result):
	band_str = ",".join("%s [%s]" % (a, b) for a, b in result['bands'].items())
	result.update(band_str=band_str)
	return "%(call)s: %(locator)s - %(bearing)d, %(band_str)s" % result


def simple (logs):
	calls = [s.lower() for s in list(logs.Call.unique())]
	locators = defaultdict(str)
	bearings = defaultdict(str)
	bands = defaultdict(Counter)

	for _, r in logs[['Call', 'Loc', 'bearing', 'Band']].iterrows():
		locators[r['Call'].lower()] = r['Loc'].lower()
		bearings[r['Call'].lower()] = r['bearing']
		bands[r['Call'].lower()][r['Band']] += 1

	while True:
		partial = raw_input("> ").lower()
		if partial.isalnum():
			partial = ".*"+partial+".*"
		regex = re.compile(partial)
		results = [dict(call=s,
			locator=locators[s],
			bearing=bearings[s],
			bands=bands[s]) for s in calls if re.match(regex, s)]
		ss = [result_formatter(s) for s in results]
		print "\n".join(ss)

def score_search(logs):
	reports = pd.DataFrame(columns=['Call', 'Bands', 'Locators'])

if __name__ == "__main__":
	band = None
	if '-b' in clint.args.grouped:
		band = clint.args.grouped['-b'].last.lower()
		print "Band:", band
	logs = find_ukac_logs('logs')
	
	if '-c' not in clint.args.flags:
		simple(logs)
	else:
		score_search(logs)
