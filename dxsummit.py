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
		self.name = "dsxummit"
		self.filters = ['M', 'G', 'GM', 'MM', 'GD', 'GI']
		SpotSource.__init__(self)

	def update (self):
		logger.debug('%s: updating.', self.name)

		if datetime.now() < self.last + timedelta(seconds=self.interval):
			logger.debug('%s: aborting update - before update interval', self.name)
			return None

		self.fetch()
	
	def fetch (self):
		url = "http://www.dxsummit.fi/CustomFilter.aspx"
		
		bs = {23: '1200'}

		payload = {'customRange': bs[self.band],
				'customCount': 100}

		data = requests.get(url, params=payload)
		logger.debug('%s: url: %s', self.name, data.url)
		logger.debug('%s: dsxummit returned %s', self.name,  data)
		if data.error is not None:
			logger.error('dsxummit returned error %s', self.name, data.error)
		else:
			self.parse(data.content)

	def parse (self, xml_data):
		soup = BeautifulSoup(xml_data)
		lines = soup.find_all('pre')[0].text.split("\n")[1:50]
		for i, line in enumerate(lines):
			fields = dict(zip(
				['spot', 'freq', 'dx', 'comment', 'time', 'country'],
				[l for l in line.strip().split("\t") if len(l) > 0]))
			print i, fields
			self.add_spot
		return
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
	d.update()
	d.print_lines()
