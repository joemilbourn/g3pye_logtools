from datetime import datetime, timedelta
from collections import namedtuple
from bs4 import BeautifulSoup
import requests 
import logging
from spot import SpotSource, Spot, SpotFromFile, SpotFilter
from flossie import Log
logger = logging.getLogger(__name__)

class Dxlite (SpotSource):
	def __init__ (self, band, update_interval=120, ttl=60*3):
		self.interval = update_interval
		self.ttl = ttl
		self.band = band 
		self.name = "dxlite"
		self.filters = ['M', 'G', 'GM', 'MM', 'GD', 'GI']
		SpotSource.__init__(self)

	def update (self):
		logger.debug('%s: updating.', self.name)

		if datetime.now() < self.last + timedelta(seconds=self.interval):
			logger.debug('%s: aborting update - before update interval', self.name)
			return None

		self.fetch()
	
	def fetch (self):
		url = "http://dxlite.g7vjr.org/"
		
		payload = {'band': self.band, 
	#				'filter':filter_prefix, 
					'full':1,
					'xml':1}

		dxlite_data = requests.get(url, params=payload)
		logger.debug('%s: url: %s', self.name, dxlite_data.url)
		logger.debug('%s: dxlite returned %s', self.name,  dxlite_data)
		if dxlite_data.error is not None:
			logger.error('dxlite returned error %s', self.name, dxlite_data.error)
		else:
			self.parse(dxlite_data.content)

	def fetcha (self, filters):
		logger.warning('%s: using fake fetch.', self.name)
		import cPickle
		self.parse(cPickle.load(file('test_dxlite_response.pkl')))

	def parse (self, xml_data):
		for spot in BeautifulSoup(xml_data).find_all('spot'):
			if any(spot.dx.text.startswith(f) for f in self.filters):
				self.add_spot (frequency=float(spot.frequency.text),
								time=datetime.strptime(spot.time.text,
									'%Y-%m-%d %H:%M:%S'),
								call=spot.dx.text)
			else:
				logger.debug('%s: dropped spot of %s', self.name, spot.dx.text)

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	d = Dxlite(23)
	l = Log(23)
	l.update()
	d.update()
	f = SpotFilter(d, l)
	f.print_lines()
