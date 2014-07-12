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
		GameDifficulty(key = GameDifficulty.diff_key(0), desc = "Easy", map_size = 4, starting_items = []),
		GameDifficulty(key = GameDifficulty.diff_key(1), desc = "Normal", map_size = 8, starting_items = []),
		GameDifficulty(key = GameDifficulty.diff_key(2), desc = "Difficult", map_size = 12, starting_items = [])
	]
	
	ndb.put_multi_async(diffs)
	
	# now events
	events = [
		Event(key = Event.event_key(0), desc = "This looks familiar"),
		Event(key = Event.event_key(1), desc = "I recognise this place"),
		Event(key = Event.event_key(2), desc = "Am I going in circles?"),
		Event(key = Event.event_key(3), desc = "Back here again!"),
		Event(key = Event.event_key(4), desc = "There seems to be some kind of scroll on the ground.", next = Event.event_key(4), options = [
			EventOption(desc = "Leave it where it is", response = "It'll probably still be here if you come back"),
			EventOption(desc = "Pick it up", response = "It's a map!<br />Now you can record where you have been", new_items = [0], break_event_chain = True)
		])
	]
	
	ndb.put_multi_async(events)

#initialisation()
	
def difficulties():
	num_diffs = 3
	diff_keys = [GameDifficulty.diff_key(rank) for rank in range(num_diffs)]
	diff_futures = ndb.get_multi_async(diff_keys)
	return [future.get_result() for future in diff_futures]


def createGame(rank):
	game = Game(diff_rank = rank)
	game.items = game.diff.starting_items
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
	
	#game.visible_rooms = range(len(game.rooms))
	return game
	
def randomWalk(game, start, num):
	curr = start
	while num > 0:
		door = random.choice(game.rooms[curr].doors)
		if (door == 0):
			curr -= game.row_length
		elif (door == 1):
			curr += 1
		elif (door == 2):
			curr += game.row_length
		elif (door == 3):
			curr -= 1
		num -= 1
	if curr == game.end:
		return randomWalk(game, curr, 1)
	else:
		return curr
	
def populateEvents(game):
	game.addEvent(4, randomWalk(game,game.start,5))
	return game
