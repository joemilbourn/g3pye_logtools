#!/usr/bin/env python

from datetime import datetime, timedelta
from dateutil.parser import parse as du_parse
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from collections import Counter
import buzhug
import getpass
import Hamlib
import HistoryConsole 
import locate
import os
import re
import readline
import rlcompleter
import sys
import urllib2
import xmlrpclib
import interactive

config = {
		'root': '~/.qso',
		'db': 'qso.db',
		'call': 'M0ZRN',
		'location': 'JO02AC',
		'guess': True,
		}

schema = [
	('callsign', str),
	('frequency', float),
	('time', datetime),
	('local_report', int),
	('remote_report', int),
	('location', str),
	('notes', str),
	('mode', str),
	('my_call', str),
	('my_loc', str),
	('QSL', str), # contains S if QSL sent direct, s via bureau likewise r/R
]

field_names = {
    '__id__': '',
	'callsign': 'Call',
	'frequency': 'Freq',
	'time': 'Time (UTC)',
	'mode': 'Mode',
	'local_report': 'RST S',
	'remote_report': 'RST R',
	'location': 'QTH',
	'notes': 'Notes',
	'QSL': 'QSL',
}


band_table = {
	#name : (start_hz, stop_hz)
	'160':(1.81e6, 2.0e6),
	'80': (3.5e6, 3.8e6),
	'60': (5.2e6, 5.5e6),
	'40': (7.0e6, 7.2e6),
	'30': (10.1e6, 10.50e6),
	'20': (14.0e6, 14.35e6),
	'17': (18.068e6, 18.168e6),
	'15': (21e6, 21.45e6),
	'12': (24.89e6, 24.99e6),
	'10': (28e6, 29.7e6),
	'6':  (50e6, 52e6),
	'4':  (70e6, 70.5e6),
	'2':  (144e6, 146e6),
}

channels_60m = {
	'FA': 5258.5e3,
	'FB': 5278.5e3,
	'FC': 5288.5e3,
	'FK': 5366.5e3,
	'FL': 5371.5e3,
	'FE': 5398.5e3,
	'FM': 5403.5e3,
}

order = ('callsign', 'frequency', 'time', 'mode', 'local_report', 
		 'remote_report', 'location', 'notes', 'my_call', 'my_loc')

mode_spots = {
	"14070": "PSK31",
	"18100": "PSK31",
}

class Fldigi:
	def __init__ (self):
		self.server = \
				xmlrpclib.ServerProxy("http://localhost:7362/RPC2")

	def alive (self):
		try:
			return self.server.fldigi.name() == 'fldigi'
		except Exception:
			return False

	def mode (self):
		return self.server.modem.get_name()

	def call (self):
		return self.server.log.get_call()

	def frequency (self):
		return self.server.log.get_frequency()

	def time (self):
		t = self.server.log.get_time_on()
		return t[0:2] + ":" + t[2:4]

	def locator (self):
		return self.server.log.get_locator()

	def name (self):
		n = self.server.log.get_name()
		qtht = self.server.log.get_qth()
		if n != '':
			if qtht != '':
				qtht = ", in "+ qtht.capitalize()
			return "OM " + n.capitalize() +qtht
		else: return ''

	def rst_out (self):
		return self.server.log.get_rst_out()

	def rst_in (self):
		return self.server.log.get_rst_in()

	def as_dict (self):
		if self.alive():
			d = {"callsign": self.call(),
			"frequency": self.frequency(),
			"time": self.time(),
			"notes": self.name(),
			"mode": self.mode(),
			"local_report": self.rst_out(),
			"remote_report": self.rst_in(),
			"location": self.locator()}
		else:
			 d = {}
		return dict((k,d[k]) for k in d.keys() if d[k] != '')

class HamlibRig:
	def __init__ (self, rig=Hamlib.RIG_MODEL_RPC):
		Hamlib.rig_set_debug (Hamlib.RIG_DEBUG_NONE)
		self.rig = Hamlib.Rig(Hamlib.RIG_MODEL_RPC)
		self.rig.open()
		self.aliveb = self.rig.error_status == 0
	
	def __del__ (self):
		self.rig.close()

	def mode (self):
		""" Return the mode as a string, one of 
		    SSB, AM, CW, DIG, FM."""
		modes = {
				'SSB': [Hamlib.RIG_MODE_LSB, Hamlib.RIG_MODE_USB],
				'AM': [Hamlib.RIG_MODE_AM, Hamlib.RIG_MODE_AMS],
				'CW': [Hamlib.RIG_MODE_CW, Hamlib.RIG_MODE_CWR],
				'DIG': [Hamlib.RIG_MODE_PKTFM, Hamlib.RIG_MODE_PKTLSB,
					Hamlib.RIG_MODE_PKTUSB, Hamlib.RIG_MODE_RTTY,
					Hamlib.RIG_MODE_RTTYR, Hamlib.RIG_MODE_FAX],
				'FM': [ Hamlib.RIG_MODE_FM, Hamlib.RIG_MODE_WFM],
				}
		
		mode = self.rig.get_mode()[0]
		mode_str = ""
		for m in modes.keys():
			if mode in modes[m]:
				mode_str = m
				break
		return mode_str

	def freq (self):
		""" Return the frequency in kHz"""
		return self.rig.get_freq()/1000.0

	def alive (self):
		return self.aliveb
	def as_dict (self):
		return {'frequency': str(self.freq()),
				'mode': str(self.mode())}

def guess ():
	""" Try and pre-populate as many fields as possible.

	    Gets data from fldigi via xmlrpc and connects to 
		hamlib.  Recent data from fldigi overrides data from hamlib.
    """
	def use_fldigi(f, decay=20):
		""" If fldigi is alive, and the contact was logged less
		than 20 minutes ago. """
		
		if not f.alive(): 
			return False

		time = datetime.utcnow()
		try:
			timetmp = datetime.strptime(f.time(), "%H:%M")
		except ValueError:
			#No time from fldigi...
			return False

		time = time.replace(hour=timetmp.hour,\
				minute=timetmp.minute)
		if time + timedelta(minutes=decay)\
				> datetime.utcnow() and f.alive():
			return True
		else:
			return False
	
	if config['guess'] == False:
		return {}

	f = Fldigi()
	h = HamlibRig()
	if use_fldigi(f):
		return f.as_dict()
	elif h.alive():
		return h.as_dict()
	else:
		return {}

def band (freq):
	""" Return the band in which X falls, or none.  If X is not a number looks
	for X.frequency."""
	
	if not isinstance(freq, float):
		try: return band(freq.frequency)
		except: return None

	for k in band_table.keys():
		b = band_table[k]
		if freq <= b[1] and freq >= b[0]:
			return k
	else:
		return None

def adif (record):
	if type(record) is list:
		return [adif(r) for r in record]

	output = "<CALL:%d>%s<QSO_DATE:8:D>%s<TIME_ON:4>%s<BAND:%d>%s<MODE:%d>%s" + \
			 "<RST_SENT:2>%s<RST_RCVD:2>%s<EOR>"

	output = output % (
				len(record.callsign), record.callsign.upper(),
				record.time.strftime("%Y%m%d"),
				record.time.strftime("%H%M"),
				len(band(record.frequency)+"M"),
				band(record.frequency)+"M",
				len(record.mode),
				record.mode,
				record.local_report,
				record.remote_report)

	return output

def make_config (config):
	if not os.path.exists(os.path.expanduser(config['root'])):
		os.mkdir(os.path.expanduser(config['root']))

def clear_db (config):
	if os.path.exists(os.path.join(
		os.path.expanduser(config['root']),
		config['db'])):
		os.rmdir(os.path.expanduser(config['root']))

class DB:
	def __init__(self, config):
		self.config = config
		self.path = self._build_path()
		self.ptr = self._load()

	def _build_path (self):
		return os.path.expanduser(
				os.path.join(self.config['root'], 
					         self.config['db']))

	def _load (self):
		try:
			return buzhug.Base(self.path).open()
		except IOError:
			return self._create()

	def _create (self):
		ptr = buzhug.Base(self.path).create(*schema)
		return ptr

	def _close(self):
		self.ptr.close()

	def __len__(self):
		return self.ptr.__len__()

	def __getitem__ (self, *args):
		return self.ptr.__getitem__(args)

	def normalise_entry (self, **entry):
		def f_frequency (string):
			if string in channels_60m.keys():
				return channels_60m[string]
			elif string.endswith('M'):
				return float(string[:-1])*1e6
			elif string.endswith('k'):
				return float(string[:-1])*1e3
			elif string.endswith('kHz'):
				return float(string[:-3])*1e3
			elif string.endswith('MHz'):
				return float(string[:-3])*1e6
			elif string.endswith('m'):
				return band_table[string[:-1]][0]
			else:
				return float(string) * 1e3

		def f_time (string):
			return du_parse(string)

		def f_int (string):
			try:
				return int(string)
			except TypeError:
				return None

		defaults = {
				'frequency': f_frequency,
				'time': f_time,
				'local_report': f_int,
				'remote_report': f_int,
			}

		for key in [s[0] for s in schema]:
			if key not in entry:
				entry[key] = None

		for key in entry:
			n_func = defaults.get(key, lambda x: x)
			try:
				entry[key] = n_func(entry[key])
			except Exception,e:
				print "Couldn't normalise key %s: %s" % (key,e)

		return entry

	def insert (self, **kw):
		self.ptr.insert(**(self.normalise_entry(**kw)))

	def update (self, entry, **kw):
		self.ptr.update(entry, **(self.normalise_entry(**kw)))

	def dump (self, filter_fun=lambda x: True):
		for r in filter(filter_fun, self.ptr):
			print self.formatted(r)
		kw = self.normalise_entry(**kw)
		return self.ptr.update(entry, **kw)

def formatted (entry, bandFmt=True):
	def call_format (call):
		if call is None: 
			return ""
		if call.find(" ") == -1:
			return call.upper()
		else:
			return call.title()

	def freq_format (freq):
		if freq is None: return ""
		if bandFmt:
			for band in band_table.keys():
				if freq >= band_table[band][0] and freq <= band_table[band][1]:
					return band +"m"
		if freq > 30e6:
			return str(freq/1e6) + "MHz"
		else:
			return str(int(freq/1e3)) + "kHz"

	def str_format (string):
		if string is None:
			return ""
		else:
			return str(string)


	def time_format (time):
		if time is None: return ""
		return time.strftime("%Y/%m/%d %H:%M")


	format_fun = {
		'__id__'            : str_format,
		'callsign'      : call_format,
		'frequency'     : freq_format,
		'time'          : time_format,
		'mode'          : str_format,
		'local_report'  : str_format,
		'remote_report' : str_format,
		'location'      : str_format,
		'notes'         : str_format,
		'my_loc'        : str_format,
		'my_call'       : call_format,
		'QSL'           : str_format,}

	formatted = dict([(k, format_fun.get(k)(entry.__getattr__(k)))
			for k in format_fun.keys()])
	return formatted

def results_table (results, fields=None):
	try:
		rows, cols = map(int, os.popen('stty size', 'r').read().split())
	except:
		rows, cols = (80, 25)
	sys.stdout.flush()
	if fields is None:
		fields = ['__id__', 'callsign', 'frequency', 'time', 'mode',
				  'local_report', 'remote_report',
				  'location', 'notes']

	#results = sorted(map(lambda x: formatted(x), results), key=lambda x: x['time'])
	results = map(lambda x: formatted(x), results)
	widths = dict([
		(k, max([len(r[k]) for r in results] + [len(field_names[k])])) 
		for k in fields])

	headers = " ".join(field_names[field].ljust(widths[field]) for field in fields)
	print headers[:cols]
	print "="*cols

	for result in results:
		print " ".join(result[field].ljust(widths[field]) 
				for field in fields)[:cols]

def g(pmpt, txt=""):
	if txt != "":
		readline.set_startup_hook(lambda: readline.insert_text(txt))
	try:
		new_value = raw_input(pmpt+": ")
	finally:
		readline.set_startup_hook(None)
	return new_value

def cmd_add (db, *args):
	result = {'my_loc': config['location'],
			'my_call': config['call'],
			'QSL': '',}
	defaults = {
		'location': \
			lambda result: locate.locator(result['callsign']),
		'time': \
			lambda result: datetime.utcnow().strftime("%H:%M"),
		'mode': \
			lambda result: mode_spots.get(result['frequency'], "SSB")
		}

	defaults.update(guess())

	args = list(args)
	for k in [s[0] for s in schema if s[0] not in result.keys()]:
		txt = ""
		if len(args) >= 1:
			txt = args.pop(0)
		else:
			try: 
				txt = defaults.get(k, lambda result: "")(result)
			except TypeError:
				txt = defaults.get(k, "no "+k)
		pmpt = field_names.get(k, k.replace("_", " ").title())
		result[k] = g(pmpt, txt)
		if result[k] == '': result[k] = None

	db.insert(**result)

def cmd_previous (db, *args):
	args = list(args)
	previous = [r for r in db.ptr 
			if r.callsign != None and r.callsign.lower() == 
			args[0].lower()]
	previous.sort(key=lambda x: x.time)

	if len(previous) > 0:
		s = "s"
		if len(previous) == 1: s = ""
		print "%d previous QSO%s, last on %s." % (
				len(previous), s, previous[-1].time.strftime("%c"))

def cmd_ammend (db, *args):
	if len(args) == 1:
		n = int(args[0])
	else:
		n = max(r.__id__ for r in db.ptr)
	entry = db.ptr[n]
	result = formatted(entry, False)
	del result['__id__']
	for k in [s[0] for s in schema]:
		pmpt = field_names.get(k, k.replace("_", " ").title())
		result[k] = g(pmpt, result[k])
		if result[k] == '': result[k] = None
	db.update(entry, **result)

def cmd_print (db, *args):
	if len(args) >= 1:
		num_r = int(list(args).pop())
	else:
		num_r = 15
	results_table([db.ptr[i] for i in range(len(db.ptr)-num_r,len(db.ptr))])

def cmd_export (db, *args):
	args = list(args)
	if len(args) != 0:
		condition = lambda item: item.time >= du_parse(args[0])
	else:
		condition = lambda item: True
	print "\n".join(adif(result) for result in db.ptr if condition(result))

def cmd_dump (db, *args):
	print "#"+",".join(order)
	for r in db.ptr:
		print ",".join(str(r.__getattr__(rr)) for rr in order)

def cmd_clear (db, *args):
	clear_db(config)

def cmd_help (nn, *args):
	s = "usage: %s [OPTIONS] COMMAND\n"+\
	    "\n"+\
		"Options:\n"+\
		" -c CALL  Change the originating callsign for this invovation.\n"+\
		" -l LOC   Change the originating location for this invovation.\n"+\
		" -d       Disable automatic field population from hamlib and fldigi.\n"+\
		" -p LOC   Change originating locator to LOC for this invocation and append /P to call.\n"+\
		" Options must be given before commands.\n\n"+\
		"Commands:\n"+\
		" add      Add an entry\n"+\
		" ammend   Change the last entry\n"+\
		" clear    Remove the database\n"+\
		" config   Print the current configuration\n"+\
		" dump     Dump the database contents as a csv\n"+\
		" eqsl     Upload new QSOs to eqsl.cc\n"+\
		" export   Print adif formatted log entries\n"+\
		" previous Show previous QSOs with the given callsign\n"+\
		" print    Print the database contents\n"+\
		" rescue   Re-build the database from a specified CSV file (see dump)\n"+\
		" search   Search for a callsign in the database\n" +\
		" shell    Run a python shell with access to the database\n"+\
		"\n"+\
		"Joe Milbourn <joe.milbourn@gmail.com>, 2010.\n"
	print s % sys.argv[0]

def cmd_config (db, *args):
	print "Current config:"
	for k in config.keys():
		print "    %s: %s" % (k, config[k])
	print "Database size: %d entries." % len(db)

def search(db, *args):
	def cs_match (cs1, cs2):
		def long_part (cs):
			if cs.find("/") == -1:
				return cs
			else:
				parts = cs.split("/")
				lp = [len(p) for p in parts]
				return parts[lp.index(max(lp))]

		cs1 = cs1.lower().strip()
		cs2 = cs2.lower().strip()
		
		if cs1 == cs2 and cs1 != None:
			return True
		elif long_part(cs1) == long_part(cs2):
			return True
		else:
			return False
	
	def cs_loose_match (cs, term):
		return term.lower().strip() in cs.lower().strip()
	
	if len(args) == 0:
		call = Fldigi().call()
	else:
		call = args[0]

	results = ([db.ptr[i] for i in range(len(db.ptr)) 
		                     if cs_match(db.ptr[i].callsign, call)])

	if len(results) == 0:
		results = ([db.ptr[i] for i in range(len(db.ptr)) 
								 if cs_loose_match(db.ptr[i].callsign, call)])
	return results

def cmd_search (db, *args):
	results = search(db, *args)
	results_table(results)

def cmd_shell (db, *args):
	vars = globals()
	locs = locals()
	for k in locs.keys():
		if not k in vars.keys():
			vars[k] = locs[k]
	del vars['vars']
	del vars['args']
	HistoryConsole.interact("QSO Shell: db is the log database.", raw_input, vars)

def init ():
	make_config(config)
	return DB(config)

def cmd_rescue (db, csv_file):
	if len(db.ptr) != 0:
		print "Database is not empty - will not recover."
		sys.exit(1)
	for line in file(csv_file, "r").readlines():
		if line.startswith('#'):
			continue
		ll = [ll.strip() for ll in line.split(",")]
		results = dict(zip(order, ll))
		results['time'] = du_parse(results['time'])
		results['local_report'] = int(results['local_report'])
		results['remote_report'] = int(results['remote_report'])
		results['frequency'] = float(results['frequency'])
		results['my_call'] = results['my_call']
		results['my_loc'] = results['my_loc']

		db.insert(**results)

def update_qsl (db, item, newstate):
	item = db.ptr[item.__id__]
	if item.QSL is None:
		state = []
	else:
		state = list(item.QSL)
	for i in newstate:
		if i in state:
			state.remove(i)
		else:
			state.append(i)
	state = "".join(state)
	result = formatted(item, False)
	result['QSL'] = state
	del result['__id__']
	try:
		db.update(item, **result)
	except Exception, e:
		print results_table([item])
		raise e

def cmd_qsl (db, *args):
	if len(args) == 0:
		return
	
	if args[0].isdigit():
		item = db.ptr[int(args[0])]
	else:
		items = search(db, args[0])
		if len(items) == 0:
			print "No QSOs found."
			sys.exit(1)
		if len(items) != 1:
			print "Specify a QSO (by id):"
			print results_table(items)
			sys.exit(1)
		item = items[0]
	if len(args) != 1:
		update_qsl(db, item, args[1])

	fields = ['__id__', 'QSL', 'callsign', 'frequency', 'time', 'mode',
			'local_report', 'location', 'notes']
	results_table([item], fields)

def eqsl_auth (user=None, password=None):
	if user is None:
		user = config['call']
	if password is None:
		password = getpass.getpass(
				"eQSL password for %s: " % user)
	return (user, password)

def eqsl_upload (adif_data, user=None, password=None):
	URL = "http://www.eqsl.cc/qslcard/ImportADIF.cfm"
	register_openers()
	if user is None or password is None:
		user, password = eqsl_auth(user, password)
	data, headers = multipart_encode({
		'EQSL_USER': user,
		'EQSL_PSWD': password,
		'ADIFDATA': adif_data,
		})
	request = urllib2.Request(URL, data, headers)
	resp = urllib2.urlopen(request).read()
	return resp, (user, password)

def eqsl_parse_response (resp):
	""" Parse the eqsl response data, return the number of bad records
	and a reason if available."""

	expr = re.compile("Result: (\d+) out of (\d+) records added<BR>")
	rexpr = re.compile("Bad (\w+): ([^<]+)<BR>")

	m = expr.search(resp)
	if not m:
		return -1
	else:
		r = rexpr.search(resp)
		reason = None
		if r:
			reason = r.group(1,2)
		bad = int(m.group(2)) - int(m.group(1))
		return (bad, reason)

def cmd_eqsl (db, *args):
	""" Upload all items with no 'e' in the QSL field to eqsl. """
	#results = [r for r in db.ptr if r.QSL is None 
		#	or 'e' not in r.QSL]
	results = db.ptr.select_for_update(None, "'e' not in QSL")
	if len(results) == 0: 
		return

	print "Selected %d QSOs for upload." % len(results)
	
	eq_uploaded = 0
	auth = (None, None)
	for result in results:
		print "uploading" ,  result.__id__
		eqsl_resp, auth = eqsl_upload(adif(result), *auth)
		eqsl_result = eqsl_parse_response(eqsl_resp)
		if eqsl_result == -1:
			print eqsl_resp
			print "Problem during upload:\n"
			print "\n These results have not been marked as uploaded."
		elif eqsl_result[0] != 0:
			print "QSO %d didn't upload, bad %s: %s." % \
					(result.__id__, 
							eqsl_result[1][0], eqsl_result[1][1])
			if eqsl_result[1][1] == 'Duplicate':
				update_qsl(db, result, 'e')
		else:
			eq_uploaded += 1
			update_qsl(db, result, 'e')
	print "%d of %d qsos uploaded." % (eq_uploaded, len(results))

def cmd_contest (db, *args):
	pass

def cmd_stats (db, *args):
	band_counter = Counter()
	call_counter = Counter()
	mode_counter = Counter()

	for r in db.ptr:
		rdict = formatted(r)
		band_counter[rdict['frequency']] += 1
		call_counter[r.callsign] += 1
		mode_counter[rdict['mode']] += 1

	for band, count in band_counter.items():
		print "\t%4s: %s" %(band, count)

	for call, count in call_counter.most_common(5):
		print "\t%10s: %s" % (call, count)
	for mode, count in mode_counter.most_common(5):
		print "\t%6s: %s" % (mode, count)

def cmd_interactive (db, *args):
	interactive.main()

if __name__ == "__main__":
	db = init()

	if len(sys.argv) == 1:
		cmd_help(None)
		db._close()
		sys.exit()
		
	args = sys.argv[1:]

	portable_p = False
	while args[0] in ['-c', '-l', '-d', '-h', '-p']:
		if args[0] == '-c':
			config['call'] = args[1]
			args = args[2:]
		elif args[0] == '-l':
			config['location'] = args[1]
			args = args[2:]
		elif args[0] == '-d':
			config['guess'] = False
			args = args[1:]
		elif args[0] == '-h':
			cmd_help(db)
			db._close()
			sys.exit()
		elif args[0] == '-p':
			portable_p = True
			config['location'] = args[1]
			args = args[2:]

	if portable_p:
		config['call'] = config['call']+"/P"

	{
	 'add': cmd_add,
	 'ammend': cmd_ammend,
	 'clear': cmd_clear,
	 'config': cmd_config,
	 'dump': cmd_dump,
	 'print': cmd_print,
	 'search': cmd_search,
	 'shell': cmd_shell,
	 'previous': cmd_previous,
	 'export': cmd_export,
	 'rescue': cmd_rescue,
	 'qsl': cmd_qsl,
	 'eqsl': cmd_eqsl,
	 'contest': cmd_contest,
	 'stats': cmd_stats,
	 'interactive': cmd_interactive,
	 }.get(args[0], cmd_help)(db, *args[1:])
	db._close()
