from datetime import datetime, timedelta
from collections import namedtuple
from bs4 import BeautifulSoup
import requests 
import logging
from spot import SpotSource, Spot, SpotFromFile, SpotFilter
from flossie import Log
import sys
import json
logger = logging.getLogger(__name__)

class KST (SpotSource):
	def __init__ (self, update_interval=120, ttl=60*3):
		self.interval = update_interval
		self.ttl = ttl
		self.name = "kst"
		SpotSource.__init__(self)

	def update (self):
		logger.debug('%s: updating.', self.name)
		qsos = json.load(file('kst.json'))
		seen = []
		for qso in reversed(qsos):
			if qso['call'] not in seen:
				seen.append(qso['call'])
				self.add_spot (frequency=qso['freq'],
									time=datetime.strptime(qso['timestamp'],
										'%Y-%m-%d %H:%M:%S'),
									spotter='kst',
									call=qso['call'])

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	d = KST()
	d.update()

	print d.repr_html()
