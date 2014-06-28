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
	game.create_rooms()
	game.put()
	return game