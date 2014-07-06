from google.appengine.ext import ndb
from google.appengine.api import channel

import random
import json
import math

class GameDifficulty(ndb.Model):
	rank = ndb.IntegerProperty()
	desc = ndb.StringProperty(indexed = False)
	map_size = ndb.IntegerProperty()
	
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

	
class Event(ndb.Model):
	desc = ndb.TextProperty()
	options = ndb.StructuredProperty(EventOption, repeated = True)
	
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

	
class Room(ndb.Model):
	doors = ndb.IntegerProperty(choices = [0,1,2,3], repeated = True) # 0:North, 1:East, 2:South, 3:West
	event = ndb.KeyProperty(Event)
	
	def to_dict(self):
		if (self.event):
			event = self.event.get().to_dict()
		else:
			event = None
		return {'doors': self.doors, 'event': event}

	
class Game(ndb.Model):
	last_modified = ndb.DateTimeProperty(auto_now=True, indexed = False)
	created = ndb.DateTimeProperty(auto_now_add=True, indexed = False)
	
	diff = ndb.StructuredProperty(GameDifficulty, indexed = False)
	
	rooms = ndb.LocalStructuredProperty(Room, repeated=True, indexed = False)
	visible_rooms = ndb.IntegerProperty(repeated = True, indexed = False)
	
	start = ndb.IntegerProperty(indexed = False)
	end = ndb.IntegerProperty(indexed = False)
	
	curr = ndb.IntegerProperty(indexed = False) # current room number
	dir = ndb.IntegerProperty(default = 0, choices = [0,1,2,3], indexed = False) # direction player is facing, 0:North, 1:East, 2:South, 3:West
	
	moves = ndb.IntegerProperty(default = 0, indexed = False)
	
	@property
	def gameID(self):
		return self.key.id()
		
	#@property
	#def client_id(self):
	#	return str(self.gameID)
	
	#def send_message(self, dict):
	#	channel.send_message( self.client_id, json.dumps(dict) )
			
	@property
	def angle(self):
		return self.dir*90
			
	def turn(self, angle):
		self.dir = (self.dir + int(math.copysign(1,angle)))%4; # either turn 90 degrees left or right
		self.put()
		#self.send_message( { 'message': "turn", 'dir': self.angle } )
		return json.dumps( { 'message': "turn", 'dir': self.angle } )
		
	def move(self):
		response = {}
		if (self.dir in self.rooms[self.curr].doors):
			if (self.dir == 0):
				change = - self.diff.map_size
			elif (self.dir == 1):
				change = 1
			elif (self.dir == 2):
				change = self.diff.map_size
			elif (self.dir == 3):
				change = - 1
		
			self.curr += change
			if self.curr not in self.visible_rooms:
				self.visible_rooms.append(self.curr)
			self.moves += 1
			self.put()
			#self.send_message( { 'message': "move", 'row': self.curr/self.diff.map_size, 'col': self.curr%self.diff.map_size, 'room': self.rooms[self.curr].to_dict() } )
			response.update( { 'message': "move", 'row': self.curr/self.diff.map_size, 'col': self.curr%self.diff.map_size, 'room': self.rooms[self.curr].to_dict(),  'win': False } )
				
		if (self.curr == self.end):
			response.update( { 'win': True } )
			self.recordCompletion()
			self.key.delete()
		
		return json.dumps(response)
			
	def recordCompletion(self):
		if (self.curr == self.end): # check game is finished
			GameCompletion(started = self.created, diff_rank = self.diff.rank, moves = self.moves).put()
			
	def addEvent(self, event_key, roomnum):
		self.rooms[roomnum].event = event_key
				
				