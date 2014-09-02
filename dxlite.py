from datetime import datetime, timedelta
from collections import namedtuple
from bs4 import BeautifulSoup
import requests 
import logging
from spot import SpotSource, Spot, SpotFromFile, SpotFilter
from flossie import Log
import sys
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
		dxlite_data.raise_for_status()
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
								spotter=spot.spotter.text,
								call=spot.dx.text)
			else:
				logger.debug('%s: dropped spot of %s', self.name, spot.dx.text)

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	band=2
	d = Dxlite(band)
	l = Log(band, '2014_08_05_2m_UKAC')
	l.update()
	d.update()
	f = SpotFilter(d, l)
	output = """<html><head>
	<meta http-equiv="refresh" content="15" > 
	<title>Calls on cluster, not in log</title></head>
	<body>
	<h1> Calls on cluster, not in log </h1>
	<pre>
	"""
	output += f.repr_html()
	output += """<p>Last updated %s</p></body></html>""" % datetime.now()
	file('log.html', 'w').write(output)

	print d.repr_html()
