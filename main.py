#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2

from google.appengine.ext import ndb
from google.appengine.api import channel
from webapp2_extras import sessions
import logging

from models import *
import game

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
	autoescape=True)
	
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'random-secret-key-boofle',
}

class BaseHandler(webapp2.RequestHandler):
	def dispatch(self):
		# Get a session store for this request.
		self.session_store = sessions.get_store(request=self.request)
		self.gameIDstr = self.session.get('gameID')

		try:
			self.template_values = {}
			if self.gameIDstr:
				game_instance = ndb.Key('Game', int(self.gameIDstr)).get()
				if game_instance:
					self.template_values.update( {'game': game_instance} )
				else:
					del self.session['gameID']
			
			webapp2.RequestHandler.dispatch(self)
			
		finally:
			# Save all sessions.
			self.session_store.save_sessions(self.response)

	@webapp2.cached_property
	def session(self):
		# Returns a session using the default cookie key.
		return self.session_store.get_session()

class MainHandler(BaseHandler):
    def get(self):
		#template_values = { 'difficulties': game.difficulties }	
		self.template_values.update({'difficulties': game.difficulties})
		template = jinja_environment.get_template('index.html')
		self.response.out.write(template.render(self.template_values))
		
class CreateGame(BaseHandler):
	def get(self):
		diff_str = self.request.get('diff')
		
		if diff_str: # requested new difficulty => start new game
			if self.session.get('gameID'): # need to delete old game
				logging.info("Deleting game ID %s", self.session['gameID'])
				ndb.Key('Game', int(self.session['gameID'])).delete()
			
			if int(diff_str) in [diff.rank for diff in game.difficulties]:
				game_diff = game.difficulties[int(diff_str)]
			else:
				game_diff = game.difficulties[0]
				
			game_instance = game.createGame(game_diff)
			self.session['gameID'] = game_instance.gameID
			self.template_values.update({ 'game': game_instance })
			
		else: # trying to continue game
			if self.session.get('gameID'):
				game_instance = self.template_values['game']
				
		try:
			token = channel.create_channel( game_instance.client_id )

			self.template_values.update({'token': token})

			template = jinja_environment.get_template( 'play.html' )	
			self.response.out.write(template.render(self.template_values))
		except:
			self.redirect("/")
		
class GameHandler(webapp2.RequestHandler):
	def post(self):
		gameID = self.request.get('gameid')
		request = self.request.get('request')
		if gameID and request:
			game_instance = ndb.Key('Game', int(gameID)).get()
			if game_instance:
				if (request == 'turn'):
					angle = int(self.request.get('angle'))
					game_instance.turn(angle)
				elif (request == 'move'):
					game_instance.move()
				else:
					pass # request doesn't exist
			else:
				pass # game doesn't exist
		else:
			pass # bad request

app = webapp2.WSGIApplication([
    ('/', MainHandler),
	('/play', CreateGame),
	('/post', GameHandler)
], debug=True,config=config)
