from datetime import datetime, timedelta
from collections import namedtuple
from bs4 import BeautifulSoup
import requests 
import logging
from spot import SpotFilter, SpotMerge
from flossie import Log
from dxlite import Dxlite
import time
import sys
logger = logging.getLogger(__name__)

if __name__ == "__main__":
	logging.basicConfig(level=logging.ERROR)
        if '-h' in sys.argv:
            print "usage: %s <band> <logdb hostname|ip> <dbname>"
            sys.exit(0)

        band = None
        if len(sys.argv) >= 2:
            band = int(sys.argv[1])
        while not band:
            try:
                band = int(raw_input('Enter band [4 6 2 70 23]: '))
            except ValueError:
                band = None
        
        ip = None
        if len(sys.argv) >= 3:
            ip = sys.srgv[2]
        if not ip:
            ip = raw_input('Enter log db hostname|ip: ')

        db_name = None
        if len(sys.argv) >= 4:
            db_name = sys.argv[3]
        if not db_name:
            unit = 'm'
            if band in [70, 23]: unit = 'cm'
            db_name_pred = datetime.now().strftime('%Y_%m_%d_%%d%%s_UKAC') % (band, unit)
            db_name = raw_input('Enter database name [%s]:' % db_name_pred)
            if db_name == "":
                db_name = db_name_pred

        interval = 30
        print "Running every %d seconds, html output to log.html - ^C to cancel" % interval
        while True:
            d = Dxlite(band)
            l = Log(band, ip, db_name)
            f = SpotFilter(d, l)
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
            time.sleep(30)
