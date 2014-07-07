#!/usr/bin/env python

import webapp2
import jinja2

from google.appengine.ext import ndb
from google.appengine.api import channel

from models import *
		
def initialisation():
	# run this to initialise datastore entries
	# difficulties first
	diffs = [
		GameDifficulty(key = GameDifficulty.diff_key(0), desc = "Easy", map_size = 4),
		GameDifficulty(key = GameDifficulty.diff_key(1), desc = "Normal", map_size = 8),
		GameDifficulty(key = GameDifficulty.diff_key(2), desc = "Difficult", map_size = 12)
	]
	
	ndb.put_multi_async(diffs)
	
	# now events

	
def difficulties():
	num_diffs = 3
	diff_keys = [GameDifficulty.diff_key(rank) for rank in range(num_diffs)]
	diff_futures = ndb.get_multi_async(diff_keys)
	return [future.get_result() for future in diff_futures]


def createGame(rank):
	game = Game(diff_rank = rank)
	game = createRooms(game)
	game = populateEvents(game)
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
	
	game.rooms = [Room(doors = []) for i in range(game.grid_size)]
	
	if (seed < 0):
		seed = random.randint(0, len(game.rooms)-1)
	
	if (map_gen == 0):
		game.end = seed
		curr = game.end
	
		notvisited = range(len(game.rooms))
		notvisited.remove(curr)
		stack = []
	
		while (len(notvisited) > 0):
			neigh = [r for r in neighbours(game.row_length, curr) if r in notvisited]
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
		frontier = set(neighbours(game.row_length, game.start))
		exclude = set([])
		
		while (len(frontier) > 0):
			next = random.sample(frontier, 1)[0]
			neigh = set(neighbours(game.row_length, next)) - exclude
			curr = random.sample(maze & neigh, 1)[0]
			game.rooms[curr].doors.append(direction(curr, next))
			game.rooms[next].doors.append(direction(next, curr))
			maze.add(next)
			frontier.remove(next)
			frontier.update(neigh - maze - exclude)
			if (random.random() < 2.*len(frontier)/(game.grid_size)):
				try:
					exclude.add(random.sample(set(range(game.grid_size)) - (maze|frontier), 1)[0])
				except:
					pass
			
		game.end = next
		game.curr = game.start
		game.visible_rooms.append(game.curr)
		
	return game
	
def populateEvents(game):
	revisit_event = Event.get_or_insert(Event.event_key_name(0), desc = "This looks familiar")
	game.addEvent(revisit_event.key, game.start)
	#test_event = Event.get_or_insert(Event.event_key_name(1), desc = "Test Event", options = [EventOption(desc = "OK"), EventOption(desc = "Cancel")])
	#game.addEvent(test_event.key, 1)
	return game
