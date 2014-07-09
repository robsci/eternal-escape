from google.appengine.ext import ndb
from google.appengine.api import channel

import random
import json
import math

class GameDifficulty(ndb.Model):
	#rank = ndb.IntegerProperty(indexed = False)
	desc = ndb.StringProperty(indexed = False)
	map_size = ndb.IntegerProperty(indexed = False)
		
	@staticmethod
	def diff_key_name(rank):
		return 'd'+str(rank)
	
	@staticmethod
	def diff_key(rank):
		return ndb.Key('GameDifficulty', GameDifficulty.diff_key_name(rank))
		
	@staticmethod
	def rank_from_key(diff_key):
		return int(diff_key.id()[1:])
		
	@property
	def rank(self):
		return GameDifficulty.rank_from_key(self.key)
	
	
class GameCompletion(ndb.Model):
	started = ndb.DateTimeProperty()
	finished = ndb.DateTimeProperty(auto_now_add=True)
	
	diff_rank = ndb.IntegerProperty()
	moves = ndb.IntegerProperty()
	
	@property
	def time(self):
		return (self.finished - self.started)
		
	@classmethod
	def recent(cls):
		return cls.query().order(-cls.finished)


class EventOption(ndb.Model):
	desc = ndb.TextProperty()
	
	def choose(self, game):
		game.event_locked = False
		game.put()
		return { 'message': "event-response", 'response': "good choice" }

	
class Event(ndb.Model):
	desc = ndb.TextProperty(indexed = False)
	options = ndb.StructuredProperty(EventOption, repeated = True)
	next = ndb.KeyProperty("Event", indexed = False)
	
	@staticmethod
	def event_key_name(eventID):
		return 'e'+str(eventID)
	
	@staticmethod
	def event_key(eventID):
		return ndb.Key('Event', Event.event_key_name(eventID))
		
	@staticmethod
	def eventID(event_key):
		return event_key.id()[1:]
		
	def to_dict(self):
		return {'desc': self.desc, 'options': [opt.desc for opt in self.options]}
		
	def event_reply(self, reply, game):
		if (reply >= len(self.options) or reply < 0):
			return { 'message': "error", 'error': "bad event reply" }
		else:
			return self.options[reply].choose(game)


class Room(ndb.Model):
	doors = ndb.IntegerProperty(choices = [0,1,2,3], repeated = True) # 0:North, 1:East, 2:South, 3:West
	event = ndb.KeyProperty(Event, indexed = False)
	
	def to_dict(self):
		if (self.event):
			event = self.event.get().to_dict()
		else:
			event = None
		return {'doors': self.doors, 'event': event}
		
	def require_response(self):
		ans = False
		if (self.event):
			event = self.event.get()
			if (event and event.options):
				ans = True
		return ans
		
	def event_reply(self, reply, game):
		response = { 'message': "error", 'error': "no event" }
		if (self.event):
			event = self.event.get()
			if event:
				response = event.event_reply(reply, game)
		return response
		
	def next_event_key(self):
		key = Event.event_key(0)
		if (self.event):
			event = self.event.get()
			if (event and event.next):
				key = event.next
		return key

	
class Game(ndb.Model):
	last_modified = ndb.DateTimeProperty(auto_now=True, indexed = False)
	created = ndb.DateTimeProperty(auto_now_add=True, indexed = False)
	
	diff_rank = ndb.IntegerProperty(default = 0, indexed = False)
	
	rooms = ndb.LocalStructuredProperty(Room, repeated=True, indexed = False)
	visible_rooms = ndb.IntegerProperty(repeated = True, indexed = False)
	event_locked = ndb.BooleanProperty(default = False, indexed = False)
	
	start = ndb.IntegerProperty(indexed = False)
	end = ndb.IntegerProperty(indexed = False)
	
	curr = ndb.IntegerProperty(indexed = False) # current room number
	dir = ndb.IntegerProperty(default = 0, choices = [0,1,2,3], indexed = False) # direction player is facing, 0:North, 1:East, 2:South, 3:West
	
	moves = ndb.IntegerProperty(default = 0, indexed = False)
	
	@property
	def gameID(self):
		return self.key.id()
		
	@property
	def diff(self):
		return GameDifficulty.diff_key(self.diff_rank).get()
		
	#@property
	#def client_id(self):
	#	return str(self.gameID)
	
	#def send_message(self, dict):
	#	channel.send_message( self.client_id, json.dumps(dict) )
	
	@property
	def row_length(self):
		return self.diff.map_size
		
	@property
	def grid_size(self):
		return self.row_length**2
			
	@property
	def angle(self):
		return self.dir*90
			
	def turn(self, angle):
		response = {}
		if (not self.event_locked):
			self.dir = (self.dir + int(math.copysign(1,angle)))%4; # either turn 90 degrees left or right
			self.put()
			response.update( { 'message': "turn", 'dir': self.angle } )
			#self.send_message( { 'message': "turn", 'dir': self.angle } )
		return json.dumps(response)
		
	def move(self):
		response = {}
		if (not self.event_locked):
			map_size = self.diff.map_size
			if (self.dir in self.rooms[self.curr].doors):
				if (self.dir == 0):
					change = - map_size
				elif (self.dir == 1):
					change = 1
				elif (self.dir == 2):
					change = map_size
				elif (self.dir == 3):
					change = - 1
			
				self.rooms[self.curr].event = self.rooms[self.curr].next_event_key()
				if self.curr in self.visible_rooms:
					self.visible_rooms.remove(self.curr)
				self.curr += change
				if self.curr not in self.visible_rooms:
					self.visible_rooms.append(self.curr)
				self.moves += 1
				if self.rooms[self.curr].require_response():
					self.event_locked = True
				self.put()
				#self.send_message( { 'message': "move", 'row': self.curr/map_size, 'col': self.curr%map_size, 'room': self.rooms[self.curr].to_dict() } )
				response.update( { 'message': "move", 'row': self.curr/map_size, 'col': self.curr%map_size, 'room': self.rooms[self.curr].to_dict(),  'win': False } )
					
			if (self.curr == self.end):
				response.update( { 'win': True } )
				self.recordCompletion()
				self.key.delete()
			
		return json.dumps(response)
		
	def event_reply(self, reply):
		response = self.rooms[self.curr].event_reply(reply, self)
		return json.dumps(response)
			
	def recordCompletion(self):
		if (self.curr == self.end): # check game is finished
			GameCompletion(started = self.created, diff_rank = self.diff_rank, moves = self.moves).put()
			
	def addEvent(self, event_key, roomnum):
		self.rooms[roomnum].event = event_key
				
				