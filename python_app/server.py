import os
import sys
import redis
import redis_circular_list
import json
import time
import threading
from datetime import timedelta
from pprint import pprint

import signal
from sys import exit

import requests
json_headers = {
	'accept': 'application/json, text/plain, */*'
}

import base64

def base64_encode( string ):
	string_bytes = string.encode( "utf-8" )
	base64_bytes = base64.b64encode( string_bytes )
	base64_string = base64_bytes.decode( "utf-8" )
	return base64_string

def base64_decode( string ):
	string_bytes = string.encode( "utf-8" )
	base64_bytes = base64.b64decode( string_bytes )
	message = base64_bytes.decode( "utf-8" )
	return message

from sanic import Sanic
from sanic.response import json as sanic_json
from sanic import response

from api.api_blueprint import api_blueprint

CACHED_MODE_TYPE = None

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
		global CACHED_MODE_TYPE
		status_message = "Watch Guard Server --> watch_state_mode()"
		# 1.) Get Current State
		redis = redis_connect()
		original_mode = redis.get( "STATE.MODE" )
		if original_mode is None:
			return False
		original_mode = str( original_mode , 'utf-8' )
		original_mode = json.loads( original_mode )
		mode = original_mode
		status_message = status_message + f' --> {mode["type"]}'

		# 2.) Call Current States' Status
		status_response = requests.get( mode["control_endpoints"]["status"] , headers=json_headers )
		status_response.raise_for_status()
		mode["status"] = status_response.json()
		if "status" not in mode["status"]:
			return False

		if CACHED_MODE_TYPE != mode["type"]:
			print( f"Mode Type Changed == was: {CACHED_MODE_TYPE} == now: {mode['type']}" )
			CACHED_MODE_TYPE = mode["type"]

		# 3.) Update Specific State Metadata
		if mode["type"] == "spotify":
			# TODO: Keep Track of Every Spotify Song Every Played
			#		just like with local media
			# Somehow , we don't know the current time here
			status_message = status_message + f' --> {mode["status"]["status"].lower()}';
		elif mode["type"] == "local_tv":
			if "file_path" in mode["status"]["status"]:
				file_path_b64 = base64_encode( mode["status"]["status"]["file_path"].split( "file://" )[ 1 ] )
				metadata_key = f'STATE.USB_STORAGE.LIBRARY.META_DATA.{file_path_b64}'
				metadata = json.loads( str( redis.get( metadata_key ) , 'utf-8' ) )
				metadata["current_time"] = mode["status"]["status"]["current_time"]
				status_message = status_message + f' --> {mode["status"]["status"]["state"]} --> time = {metadata["current_time"]}';
				redis.set( metadata_key , json.dumps( metadata ) )
		elif mode["type"] == "local_movie":
			pass
		elif mode["type"] == "local_audiobook":
			pass
		elif mode["type"] == "local_odyssey":
			pass
		elif mode["type"] == "disney_plus":
			pass
		elif mode["type"] == "twitch":
			pass
		elif mode["type"] == "netflix":
			pass
		elif mode["type"] == "hulu":
			pass
		elif mode["type"] == "amazon":
			pass
		elif mode["type"] == "youtube":
			pass

		# 4.) Save State
		print( status_message )
		redis.set( "STATE.MODE" , json.dumps( mode ) )
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
time_interval = Thread( watch_state_mode , event , 3 )
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