import os
import redis
import json
import time
import threading
from datetime import timedelta
from pprint import pprint

import signal
from sys import exit

from sanic import Sanic
from sanic.response import json as sanic_json
from sanic import response

from api.api_blueprint import api_blueprint

# https://github.com/huge-success/sanic/tree/master/examples
# https://github.com/huge-success/sanic/blob/master/examples/try_everything.py

# https://sanic.readthedocs.io/en/latest/sanic/blueprints.html

def redis_connect():
	try:
		redis_connection = redis.StrictRedis(
			host="127.0.0.1" ,
			port="6379" ,
			db=1 ,
			#password=ConfigDataBase.self[ 'redis' ][ 'password' ]
			)
		return redis_connection
	except Exception as e:
		return False

def watch_state_mode():
	try:
		print( "\nWatch Guard Server --> watch_state_mode()" )
		redis = redis_connect()
		mode = redis.get( "STATE.MODE" )
		if mode is None:
			return False
		mode = str( mode , 'utf-8' )
		mode = json.loads( mode )
		pprint( mode )
	except Exception as e:
		print( e )
		return False

class Thread( threading.Thread ):
	def __init__( self , callback ,event , interval ):
		self.callback = callback
		self.event = event
		self.interval = interval
		super( Thread , self ).__init__()
	def run( self ):
		while not self.event.wait( self.interval ):
			self.callback()
event = threading.Event()
time_interval = Thread( watch_state_mode , event , 2 )
time_interval.daemon = True
time_interval.start()

def signal_handler( signal , frame ):
	print( f"Watch Guard server.py Closed , Signal = {str( signal )}" )
	time_interval.join()
	sys.exit( 0 )

signal.signal( signal.SIGABRT , signal_handler )
signal.signal( signal.SIGFPE , signal_handler )
signal.signal( signal.SIGILL , signal_handler )
signal.signal( signal.SIGSEGV , signal_handler )
signal.signal( signal.SIGTERM , signal_handler )
signal.signal( signal.SIGINT , signal_handler )

app = Sanic( name="Watch Guard Server" )

@app.route( "/" )
def hello( request ):
	return response.text( "You Found the Watch Guard Server!\n" )

@app.route( "/ping" )
def ping( request ):
	return response.text( "pong\n" )

app.blueprint( api_blueprint )



def get_config( redis_connection ):
	try:
		try:
			config = redis_connection.get( "CONFIG.WATCH_GUARD_SERVER" )
			config = json.loads( config )
			return config
		except Exception as e:
			try:
				config_path = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ) , "config.json" )
				with open( config_path ) as f:
					config = json.load( f )
				redis_connection.set( "CONFIG.WATCH_GUARD_SERVER" , json.dumps( config ) )
				return config
			except Exception as e:
				config = {
					"port": 10001 ,
				}
				redis_connection.set( "CONFIG.WATCH_GUARD_SERVER" , json.dumps( config ) )
				return config
	except Exception as e:
		print( "Could't Get Config for Watch Guard Server" )
		print( e )
		return False

def run_server():
	try:
		redis_connection = redis_connect()
		if redis_connection == False:
			return False
		config = get_config( redis_connection )
		if config == False:
			return False


		host = '0.0.0.0'
		port = config[ 'port' ]
		app.run( host=host , port=port )

	except Exception as e:
		print( "Couldn't Start Watch Guard Server" )
		print( e )
		return False


def try_run_block( options ):
	for i in range( options[ 'number_of_tries' ] ):
		attempt = options[ 'function_reference' ]()
		if attempt is not False:
			return attempt
		print( f"Couldn't Run '{ options[ 'task_name' ] }', Sleeping for { str( options[ 'sleep_inbetween_seconds' ] ) } Seconds" )
		time.sleep( options[ 'sleep_inbetween_seconds' ] )
	if options[ 'reboot_on_failure' ] == True:
		os.system( "reboot -f" )

try_run_block({
	"task_name": "Watch Guard Server" ,
	"number_of_tries": 5 ,
	"sleep_inbetween_seconds": 5 ,
	"function_reference": run_server ,
	"reboot_on_failure": True
	})