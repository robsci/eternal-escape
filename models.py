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
		return finished - started
	
class Room(ndb.Model):
	doors = ndb.IntegerProperty(choices = [0,1,2,3], repeated = True) # 0:North, 1:East, 2:South, 3:West
	
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
		
	@property
	def client_id(self):
		return str(self.gameID)
	
	def send_message(self, dict):
		channel.send_message( self.client_id, json.dumps(dict) )

	def create_rooms(self):
		self.rooms = [Room(doors = []) for i in range(self.diff.map_size*self.diff.map_size)]
		
		self.end = random.randint(0, len(self.rooms)-1)
		curr = self.end
		
		notvisited = range(len(self.rooms))
		notvisited.remove(curr)
		stack = []
		
		while (len(notvisited) > 0):
			neigh = [r for r in self.neighbours(curr) if r in notvisited]
			if (len(neigh) > 0):
				stack.append(curr)
				next = random.choice(neigh)
				self.rooms[curr].doors.append(self.direction(curr, next))
				self.rooms[next].doors.append(self.direction(next, curr))
				curr = next
				notvisited.remove(curr)
			elif (len(stack) > 0):
				curr = stack.pop()
			else:
				curr = random.choice(notvisited)
				notvisited.remove(curr)
		
		self.start = curr
		self.curr = self.start
		self.visible_rooms.append(self.curr)
		
	def neighbours(self, room):
		result = []
		if (room >= self.diff.map_size): # not on top row
			result.append(room - self.diff.map_size)
		if (room % self.diff.map_size != self.diff.map_size-1): # not on right column
			result.append(room + 1)
		if (room < self.diff.map_size*(self.diff.map_size-1)): # not on bottom row
			result.append(room + self.diff.map_size)
		if (room % self.diff.map_size != 0): # not on left column
			result.append(room - 1)
		return result
		
	def direction(self, room1, room2): # direction of room 2 from room 1 (used for placing doors)
		if (room2 == room1+1):
			return 1 # East
		elif (room2 == room1-1):
			return 3 # West
		elif (room2 > room1):
			return 2 # South
		else:
			return 0 # North
			
	@property
	def angle(self):
		return self.dir*90
			
	def turn(self, angle):
		self.dir = (self.dir + int(math.copysign(1,angle)))%4; # either turn 90 degrees left or right
		self.put()
		self.send_message( { 'message': "turn", 'dir': self.angle } )
		
	def move(self):
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
			self.send_message( { 'message': "move", 'row': self.curr/self.diff.map_size, 'col': self.curr%self.diff.map_size, 'doors': self.rooms[self.curr].doors } )
				
		if (self.curr == self.end):
			self.send_message( { 'message': "win" } )
			self.recordCompletion()
			self.key.delete()
			
	def recordCompletion(self):
		if (self.curr == self.end): # check game is finished
			GameCompletion(started = self.created, diff_rank = self.diff.rank, moves = self.moves).put()
				
				