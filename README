
First, get the necessaries:
	$ pip install -r requirements.txt

Then kick off the monitor program (here for 2m, connecting to flossie's computer on 192.168.3.127):
	$ python cluster_not_in_log.py                                                               
	Enter band [4 6 2 70 23]: 2
	Enter log db hostname|ip: 192.168.3.127
	Enter database name [2014_09_02_2m_UKAC]:
	Running every 30 seconds, html output to log.html - ^C to cancel
	Freq         Call      Time                             Source                           
	144240.0     G8EQD/P   2:16:56.302131                   filter                           
	144241.0     G8EQD/P   2:14:56.303283                   filter                           
	144254.0     G8PNN/P   2:17:56.304429                   filter                           
	144280.0     G6CBX/P   2:19:56.305526                   filter                           
	144310.0     M0BUL/P   2:00:56.306570                   filter                           
	144348.0     G6DOD/P   2:20:56.307762                   filter                           
	144348.0     G6DOD/P   2:34:56.308834                   filter                           
	144348.0     G6DOD/P   2:30:56.309887                   filter                           
	144385.0     GM4GUF/P  2:23:56.310971                   filter   

That'll run continuously, updating every 30 seconds.  In another terminal, say:
	$ python -m SimpleHTTPServer
	Serving HTTP on 0.0.0.0 port 8000 ...

Right, all done.  Point your web-browser at the computer you're running all this on, at port 8000, e.g.:
	$ x-www-browser https:/toby.local:8000/log.html
