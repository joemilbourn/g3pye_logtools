
from datetime import datetime, timedelta
from collections import namedtuple
from bs4 import BeautifulSoup
import requests 
import logging
from spot import SpotFilter, SpotMerge
from flossie import Log
from dxlite import Dxlite
from kst_json import KST
import sys
logger = logging.getLogger(__name__)

if __name__ == "__main__":
	logging.basicConfig(level=logging.ERROR)
        if '-h' in sys.argv:
            print "usage: %s <band> <dbname>"
            sys.exit(0)

        band = None
        if len(sys.argv) >= 2:
            band = int(sys.argv[1])
        while not band:
            try:
                band = int(raw_input('Enter band [4 6 2 70 23]: '))
            except ValueError:
                band = None
        
        db_name = None
        if len(sys.argv) >= 3:
            db_name = sys.argv[2]
        if not db_name:
            unit = 'm'
            if band in [70, 23]: unit = 'cm'
            db_name_pred = datetime.now().strftime('%Y_%m_%d_%%d%%s_UKAC') % (band, unit)
            db_name = raw_input('Enter database name [%s]:' % db_name_pred)
            if db_name == "":
                db_name = db_name_pred

	d = Dxlite(band)
	l = Log(band, db_name)
	k = KST()
	f = SpotFilter(SpotMerge(d, k), l)
	f.update()
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

        print f.print_lines()
