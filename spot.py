from collections import namedtuple
from datetime import datetime, timedelta
import logging
import os
import cPickle

logger = logging.getLogger(__name__)

class Spot(namedtuple('Spot', 'call freq time source')):
	__slots__ = ()

class SpotSource:
	def __init__ (self):
		self.spots = set()
		self.last = datetime.now() - timedelta(self.ttl)
		logger.debug('Created new SpotSource %s' %self.name)

	def add_spot (self, frequency=None, time=None, call=None):
		s = Spot(call, frequency, time, self.name)
		ttl = timedelta(seconds=self.ttl)
		if time < datetime.now() + ttl:
			self.spots.add(s)
		else:
			logger.debug('%s: dropped spot of %s at %s: too old.',
					self.name, call, time.strftime('%Y/%m/%d %H:%M'))
		self.last = datetime.now()

	def update (self):
		logger.error('No update method for SpotSource %s', name)

	def print_lines (self):
		from clint.textui import columns, puts, colored
		widths = [12, 9, 32, 32]
		headers = ['Freq', 'Call', 'Age', 'Source']
		puts(columns(*map(list, zip(map(colored.red, headers), widths))))
		for spot in sorted(self.spots, key=lambda x: x.freq):
			puts(columns(*map(list, zip([str(spot.freq), spot.call, str(datetime.now()-spot.time), str(self.name)], widths))))

class SpotFromFile (SpotSource):
	def __init__ (self, filename):
		self.ttl = 0
		self.name = 'file'
		SpotSource.__init__(self)
		self.filename = os.path.expanduser(filename)

		if not os.path.exists(self.filename):
			logger.debug('%s: Created empty spots for %s', self.name, self.filename)
			self.spots = []
		else:
			logger.debug('%s: Loaded spots from %s', self.name, self.filename)
			self.spots = cPickle.load(file(self.filename))
		self.last = datetime.now()

	def load_from (self, spot_source):
		logger.debug('%s: Loaded spots from %s', self.name, other.name)
		self.spots = spot_source.spots
		self.last = spot_source.last

	def save (self):
		logger.debug('%s: Saved spots to %s', self.name, self.filename)
		cPickle.dump(self.spots, file(self.filename, 'w'))

class SpotFilter(SpotSource):
	def __init__ (self, spots, excl):
		""" takes spots from spots unless they're call is in excl """
		self.ttl = 0
		self.name = 'filter'
		SpotSource.__init__(self)
		self.spot_source = spots
		self.other = excl
		self.update()

	def update (self):
		excl_calls = [s.call for s in self.other.spots]
		for spot in self.spot_source.spots:
			if spot.call not in excl_calls:
				self.add_spot(spot.freq, spot.time, spot.call)
			else:
				logger.debug('%s: filtered spot of %s', self.name, spot.call)

class SpotPool:
	def __init__ (self, update_interval):
		self.last = 0
		self.pool = set()
		self.update_interval = update_interval
		self.sources = []

	def add_source(self, source):
		self.sources.append(source)

	def update (self):
		for source in self.sources:
			source.update()

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	s = SpotFromFile('dxlite.spots')
	s.print_lines()
