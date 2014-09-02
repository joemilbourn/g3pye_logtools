#from sqlalchemy.ext.sqlsoup import SqlSoup
from sqlsoup import SQLSoup as SqlSoup
from datetime import datetime, timedelta
from collections import namedtuple
import logging
from spot import SpotSource, Spot, SpotFromFile

logger = logging.getLogger(__name__)

class Log (SpotSource):
	def __init__ (self, band, db, update_interval=30, ttl=60*3):
		self.interval = update_interval
		self.ttl = ttl
		self.band = band 
		self.name = "log"
		#self.db = SqlSoup('mysql://root:g3pye@192.168.3.99/ukac20130226')
		self.db = SqlSoup('mysql://root:g3pye@flossie01/%s' %db)
		#self.db = SqlSoup('mysql://root:g3pye@192.168.0.104/%s' %db)
		SpotSource.__init__(self)

	def update (self):
		logger.debug('%s: updating.', self.name)

		if datetime.now() < self.last + timedelta(seconds=self.interval):
			logger.debug('%s: aborting update - before update interval', self.name)
			return None

		rp = self.db.execute('select callsign from log')
		for callsign, in rp.fetchall():
			self.add_spot(frequency=None,
					time=datetime.now(),
					call=callsign)

if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	d = Log(2, '2014_08_05_2m_UKAC')
	d.update()
	d.print_lines()
