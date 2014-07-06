#!/usr/bin/env python

import webapp2
import jinja2

from google.appengine.ext import ndb
from google.appengine.api import channel

from models import *

difficulties = [ GameDifficulty(rank = 0, desc = "Easy", map_size = 4),
				 GameDifficulty(rank = 1, desc = "Normal", map_size = 8),
				GameDifficulty(rank = 2, desc = "Difficult", map_size = 12)]


def createGame(difficulty):
	game = Game(diff = difficulty)
	game = createRooms(game, seed=0)
	event = Event.get_or_insert(Event.event_key_name(1), desc = "Test Event", options = [EventOption(desc = "OK"), EventOption(desc = "Cancel")])
	game.addEvent(event.key, 1)
	game.put()
	return game

def neighbours(size, room):
	result = []
	if (room >= size): # not on top row
		result.append(room - size)
	if (room % size != size-1): # not on right column
		result.append(room + 1)
	if (room < size*(size-1)): # not on bottom row
		result.append(room + size)
	if (room % size != 0): # not on left column
		result.append(room - 1)
	return result
	
def direction(room1, room2): # direction of room 2 from room 1 (used for placing doors)
	if (room2 == room1+1):
		return 1 # East
	elif (room2 == room1-1):
		return 3 # West
	elif (room2 > room1):
		return 2 # South
	else:
		return 0 # North
	
def createRooms(game, map_gen = 1, seed = -1):
	# map_gen
	# 0: depth-first
	# 1: randomized Prim's
	
	game.rooms = [Room(doors = []) for i in range(game.diff.map_size*game.diff.map_size)]
	
	if (seed < 0):
		seed = random.randint(0, len(game.rooms)-1)
	
	if (map_gen == 0):
		game.end = seed
		curr = game.end
	
		notvisited = range(len(game.rooms))
		notvisited.remove(curr)
		stack = []
	
		while (len(notvisited) > 0):
			neigh = [r for r in neighbours(game.diff.map_size, curr) if r in notvisited]
			if (len(neigh) > 0):
				stack.append(curr)
				next = random.choice(neigh)
				game.rooms[curr].doors.append(direction(curr, next))
				game.rooms[next].doors.append(direction(next, curr))
				curr = next
				notvisited.remove(curr)
			elif (len(stack) > 0):
				curr = stack.pop()
			else:
				curr = random.choice(notvisited)
				notvisited.remove(curr)
	
		game.start = curr
		game.curr = game.start
		game.visible_rooms.append(game.curr)
		
	elif (map_gen == 1):
		game.start = seed
		
		maze = set([game.start])
		frontier = set(neighbours(game.diff.map_size, game.start))
		exclude = set([])
		
		while (len(frontier) > 0):
			next = random.sample(frontier, 1)[0]
			neigh = set(neighbours(game.diff.map_size, next)) - exclude
			curr = random.sample(maze & neigh, 1)[0]
			game.rooms[curr].doors.append(direction(curr, next))
			game.rooms[next].doors.append(direction(next, curr))
			maze.add(next)
			frontier.remove(next)
			frontier.update(neigh - maze - exclude)
			if (random.random() < 2.*len(frontier)/(game.diff.map_size*game.diff.map_size)):
				try:
					exclude.add(random.sample(set(range(game.diff.map_size*game.diff.map_size)) - (maze|frontier), 1)[0])
				except:
					pass
			
		game.end = next
		game.curr = game.start
		game.visible_rooms.append(game.curr)
		
	return game
