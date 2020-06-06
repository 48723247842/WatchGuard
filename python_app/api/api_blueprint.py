from sanic import Blueprint
from sanic.response import json as json_result
from sanic import response

import json
import time
import redis
#import requests

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

json_headers = {
	'accept': 'application/json, text/plain, */*'
}

api_blueprint = Blueprint( 'api_blueprint' , url_prefix='/api' )

@api_blueprint.route( '/' )
def commands_root( request ):
	return response.text( "you are at the /button url\n" )


# mode = {
# 	"button": 1 ,
# 	"type": "spotify" ,
# 	"name": "Playing Spotify Curated Playlist" ,
# 	"uri": uri ,
# 	"state": False ,
# 	"status_object": result["status_response"] ,
# 	"control_endpoints": {
# 		"pause": "http://127.0.0.1:11101/api/pause" ,
# 		"resume": "http://127.0.0.1:11101/api/resume" ,
# 		"play": "http://127.0.0.1:11101/api/play" ,
# 		"stop": "http://127.0.0.1:11101/api/stop" ,
# 		"previous": "http://127.0.0.1:11101/api/previous" ,
# 		"next": "http://127.0.0.1:11101/api/next" ,
# 		"status": "http://127.0.0.1:11101/api/get/playback/status"
# 	}
# }

@api_blueprint.route( "/1" , methods=[ "GET" ] )
@api_blueprint.route( "/spotify/playlists/currated" , methods=[ "GET" ] )
def spotify_playlists_currated( request ):
	result = { "message": "failed" }
	try:

		redis_connection = redis_connect()
		mode = redis_connection.get( "STATE.MODE" )
		if mode is None:
			raise Exception( "No STATE.MODE Key" )
		mode = json.loads( mode )
		if mode["type"] == "IDLE":
			result["message"] = "success"
			result["mode"] = mode
			json_result( result )

		status_response = requests.get( mode["control_endpoints"]["status"] , headers=json_headers , params=play_params )
		status_response.raise_for_status()
		mode["status_object"] = status_response.json()

		if mode["status_object"]["status"].lower() == "playing":
			mode["state"] = "playing"
			result["message"] = "success"
			result["mode"] = mode
			redis_connection.set( "STATE.MODE" , json.dumps( mode ) )
		else:
			raise Exception( "Could Not Get Spotify To Start Playing" )

	except Exception as e:
		print( e )
		result["error"] = str( e )
	return json_result( result )