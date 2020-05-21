#!/usr/bin/env python3

# Project Homepage: https://github.com/ThePiGuy/Python-Vi-ArrowKeys

import keyboard as kb # install with "pip install keyboard"
import pystray as tray # install with "pip install pystray"
from PIL import Image # install with "pip install wheel pillow"

import sys, string

gstate = {						# global state of the system
	"down": set(),				# set of characters currently pressed (set bc there will only ever be a single instance of each)
	"lastInfo": "",				# stores an information string printed to the user, for caching
	"lastInfoCount": 0,			# comment
	"viTriggeredYet": False,	# whether VI mode has been triggered while d has been pressed (decides where or not to type a 'd' on 'd UP')
	"dSentYet": False,			# whether the 'd' character has been send yet (gets reset on 'd DOWN', and sent when 'd' is typed from either 'UP', 'cards', or 'world' section

	"icon": None,				# system tray icon
	"enabled": True,			# system tray enabled
	"shiftDown": False,			# whether or not shift is being pressed. Numlock fix makes checking this slightly weirder.
	"stickyShift": False			# whether sticky shift is engaged
}

config = {
	"printDebug": True,			# deployment: False
	"enableSysTray": True,		# deployment: True
	"enableQuickExit": False,	# deployment: False 	# press 'end' key to exit the program (useful for debug only)

	"maps": {					# VI Mappings
		'h': "left",
		'j': "down",
		'k': "up",
		'l': "right"
	}
}



config['specials'] = list(config['maps'].keys()) + ['d'] # list of all special characters to remap

# List of keys to listen for and apply the system to (prevents issues when they're typed before or after a 'd')
config['hookKeys'] = list(string.punctuation) + list(string.ascii_lowercase) + ['space', 'end', 'enter', 'backspace', 'shift'] + list(string.digits)

def hookCallback(event):
	"""
	Called for every key down/up event. This is where the remapping magic happens.
	Everything after this method is just pretty system tray stuff.

	@param event a keyboard.KeyboardEvent object

	Samples of event parameter (with event.to_json()):
		{"event_type": "down", "scan_code": 30, "name": "a", "time": 1588229823.0407975, "is_keypad": false}
		{"event_type": "up", "scan_code": 30, "name": "a", "time": 1588229823.1415234, "is_keypad": false}
	Each attribute/key can be accessed directly with dot notation (ex: event.event_type).
	"""

	nameL = event.name.lower()
	scancode = event.scan_code
	d_is_down = 'd' in gstate['down'] 



	# SECTION 1: Set hotkey for exiting the program
	if (nameL == "end") and config['enableQuickExit']:
		sys.exit()


	# SECTION 2: Record whether this key was pressed (lower case)
	down_event = False
	if event.event_type == "up":
		gstate['down'].discard(nameL) # use discard to avoid error if not in set
		down_event = False
	elif event.event_type == "down":
		gstate['down'].add(nameL)
		down_event = True
	else:
		printf("Unknown event type: " + event.event_type)
	

	# SECTION 2.5: Numlock hack fix for shift-arrow selection
	#if scancode in (42,54):
	if "shift" in nameL:
		if down_event:
			shiftDown()
			#gstate['stickyShift'] = d_is_down	# if shift is pressed while d is down, engage sticky shift
		elif not gstate['stickyShift']:			# delay releasing shift if sticky shift is engaged
			shiftUp()

	if nameL in ('up', 'down', 'left', 'right') or event.is_keypad:
		gstate['viTriggeredYet'] = True

	
	# SECTION 3: Pass through normal keys (will require keys down check later)
	if not isDown('d') or nameL not in config['specials']:
		# if d is not pressed and this isn't for a d
		if down_event:
			# Do 'cards' fix
			if isDown('d') and not gstate['dSentYet']:
				# don't send a 'd' if a hotkey follows before the d is released)
				if (nameL not in ("shift", "left shift", "right shift", "up", "down", "left", "right") and not event.is_keypad):
					kb.press('d')
					# Fix "Discord" bug.  Release shift before typing the next character
					shiftUp()
					gstate['down'].discard("shift")
					gstate['down'].discard("left shift")
					gstate['down'].discard("right shift")
					gstate['dSentYet'] = True
			kb.press(scancode)
		else:
			kb.release(scancode)


	# SECTION 4: Pass through 'd' based on UP event
	if (nameL == 'd'):
		if down_event:
			# alternatively we could reset viTriggeredYet=False here
			gstate['dSentYet'] = False						# reset to not sent yet
			gstate['stickyShift'] = gstate['shiftDown']		# engage sticky shift if a d is pressed while shift is down
		else:
			if (not gstate['viTriggeredYet']) and (not gstate['dSentYet']):
				kb.send('d')
				shiftUp()
				gstate['dSentYet'] = True
			gstate['viTriggeredYet'] = False # reset to false


	# SECTION 5: Fix "worl/world" bug
	if any([isDown(k) for k in config['maps'].keys()]) and (nameL == 'd' and down_event):
		# If any of the VI keys are currently pressed down, and 'd' is being PRESSED
		kb.send('d') # this might only be a .press, actually; doesn't matter though
		#printf("\nDid 'world' bug fix.")
		gstate['dSentYet'] = True


	# SECTION 6: Perform VI arrow remapping
	if (nameL in config['maps'].keys()) and isDown('d'):
		gstate['viTriggeredYet'] = True # VI triggered, no longer type a 'd' on release
		gstate['stickyShift'] = False		# FIXME: repeated shift+D only capitalizes the first one
		thisSend = config['maps'][nameL]
		if down_event:
			kb.press(thisSend)
		else:
			kb.release(thisSend)
		#printf("\nSending: " + thisSend)


	# SECTION 7: Print Debug Info
	if config['printDebug']:
		info = "\nNew Event: type({type})\tname({scancode} = {name})\tkeysDown({keysDown})\tkeypad({keypad})".format(type=event.event_type, \
	                    name=event.name, scancode=scancode, keysDown=" | ".join(gstate['down']), keypad=event.is_keypad)
		if gstate['lastInfo'] != info:
			printf(info, end="")
			gstate['lastInfoCount'] = 0
		elif gstate['lastInfoCount'] < 20: # only print out if it's not already been held for a while
			printf(".", end="")
			gstate['lastInfoCount'] += 1
		gstate['lastInfo'] = info


def isDown(key):
	return key in gstate['down']


def shiftDown():
	if not gstate['shiftDown'] and not gstate['stickyShift']:
		#kb.press((42,54))
		kb.press(("left shift", "right shift"))		# press right and left shift to counteract the numlock auto-unshift
		gstate['shiftDown'] = True


def shiftUp():
	if gstate['shiftDown'] or gstate['stickyShift']:
		#kb.release((42,42,54))
		kb.release(("left shift", "left shift", "right shift"))		# release both shifts, plus the automatic one (order is important for some reason)
		gstate['shiftDown'] = False
	
	gstate['stickyShift'] = False


def startHooks(waitAtEnd = False):
	"""
	Attaches keyboard hooks, starts the program basically.
	"""

	# Avoid duplicate hooks by removing all hooks first
	#stopHooks()

	# Hook all keys
	# Issues: fails with 'left windows', types a 'd' when shift is pressed, etc.
	#kb.hook(hookCallback, True) # supress characters

	# Hook only letters (and maybe certain other characters)
	for character in config['hookKeys']:
		kb.hook_key(character, hookCallback, True) # supress characters

	if config['printDebug']:
		printf("\nAttached {} hooks.".format(len(config['hookKeys'])))

	# wait forever (only useful for when this function is the last thing called, not for system tray)
	if waitAtEnd:
		kb.wait()


def stopHooks():
	"""
	Removes keyboard hooks, stops listening. Pauses the program.
	"""
	kb.unhook_all() # should do it, but it doesn't

	if config['printDebug']:
		printf("\nStopped all hooks/paused the program.")


def traySetup(icon):
	"""
	Gets called when the system tray icon is created.
	This is run in a separate thread, and its completion is not awaited (it can run forever).
	@param icon presumably the icon itself
	"""
	startHooks()


def trayEnabledChanged(icon):
	""" Gets called when system tray "Enabled" changes state. This must keep track of its own state. """
	gstate['enabled'] = not gstate['enabled'] # toggle it
	if gstate['enabled']:
		startHooks()
	else:
		stopHooks()


def createSystemTray():
	"""
	Sends the script to run in the system tray.
	This method runs infinitely, until the program is stopped.
	"""

	image = Image.open("icon-64.png")
	menu = tray.Menu(
		tray.MenuItem("VI Arrow Keys", lambda: 1, enabled=False), # inactive item with the program's title
		tray.MenuItem('Enabled', trayEnabledChanged, checked=lambda item: gstate['enabled']),
		#tray.MenuItem('Resume', trayResume)
		tray.MenuItem('Quit/Exit', lambda: gstate['icon'].stop()), # just calls icon.stop(), steps the whole program
	)

	gstate['icon'] = tray.Icon("VI Arrow Keys", image, "VI Arrow Keys", menu) # originally stored in "icon", stored globally though
	gstate['icon'].visible = True
	gstate['icon'].run(setup=traySetup) # this creates an infinite loops and runs forever until exit here


def run():
	# Create the system tray icon
	createSystemTray() # never ends


def printf(*args, **kwargs):
	""" A print function that flushes the buffer for immediate feedback. """
	print(*args, **kwargs, flush=True)


if __name__ == "__main__":
	if config['enableSysTray']:
		run()
	else:
		startHooks(True)
