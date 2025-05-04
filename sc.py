#!/usr/bin/python3

from threading import Condition
import concurrent.futures
import threading
import time
import random
from termcolor import colored
import sys
import os
import curses
import re
import queue


# https://stackoverflow.com/questions/16740104/python-lock-with-statement-and-timeout 
from contextlib import contextmanager
@contextmanager
def acquire_timeout(lock, timeout):
    result = lock.acquire(timeout=timeout)
    try:
        yield result
    finally:
        if result:
            lock.release()

# Dynamic population

# import call method from subprocess module
from subprocess import call

# import sleep to show output for some time period
from time import sleep

import argparse


    
# define clear function
def clear():
    # check and make call for specific operating system
    _ = call('clear' if os.name == 'posix' else 'cls')

# 4.2 Each faction has access to the same two unit types but with distinct health and attack values: 
unit_types = [
    {
        'name': "Melee",
        #'nickname': "M",
        'nickname': "",
        'start':  '\033[4m',
        'end':    '\033[0m',
        'health': 120,
        'min': 20,
        'max': 30,
        'range': 0,
        'weapon': "axe"
    },
    {
        'name': "Ranged",
        #'nickname': "R",
        'nickname': "",
        'start': '',
        'end': '',
        'health': 80,
        'min': 10,
        'max': 20,
        'range': 1,
        'weapon': "bow"
    }
]
# Melee will be show with an underscore
unit_curses = [curses.A_UNDERLINE,curses.A_NORMAL] # melee with underline and ranged is normal 


# Factions Name : 0->8
faction_name = [
    "Uni staff", "The Goblins", "The Orcs", "The Trolls", "The Giants",
    "The Dragons", "The Golems", "The Gnomes"
]

# Faction Colors - libcurse way : 0->8
faction_curses = [
    [curses.COLOR_WHITE,        curses.COLOR_BLACK],
    [curses.COLOR_GREEN, 	curses.COLOR_BLACK],
    [curses.COLOR_BLUE, 	curses.COLOR_BLACK],
    [curses.COLOR_MAGENTA,	curses.COLOR_BLACK],
    [curses.COLOR_CYAN,		curses.COLOR_BLACK],
    [curses.COLOR_RED,		curses.COLOR_BLACK],
    [curses.COLOR_BLUE, 	curses.COLOR_GREEN],
    [curses.COLOR_RED,		curses.COLOR_BLUE],
]


# Global variable shared by all threads.

FACTION_NUM = 2  # 4  # 2 -> 8     # 4.1 The number of factions (players) can be set between 2 to 8.
FACTION_SIZE = 5  # Numbers of warriors in each faction
MAP_SIZE = 6  # 30 # 5 -> 100      # 4.1 The user can select a map size (MAP_SIZE x MAP_SIZE), where MAP_SIZE is in the range of [5, 100].
MAX_WORKER_PER_FACTION = 8
faction_executor = [None] * 8      # Store the thread pool 
low_thread_watermark = 4  # clock  + draw + logger + main
out_file_name = "battle_log.txt"
number_of_unit_types = len(unit_types)  #the value always 2 
seed = 4   # Seed for main thread
epoch = 0  # Will be updated by the clock
map_refresh_rate = 5 # 5 sec as per spec
clock_tick = Condition()    # To wake up all thread at the same time
condition_map = Condition() # To redraw the map ?
live_map = False
faction_status = False
start_gun = Condition()
prompt="cmd# "
press="Esc or any key to  enter commands"
cliwin = None
cadence = True           # All fighter will wake up at the same time

prewar   = True    # Battle is imminent
cooldown = False   # Battle is over
war      = False   # Battle is running

refreshscreen = True # Stop refreshing  
cell_size = 5        # Cell size
cell_height = 2 
surrounding = False  # We do adjacent , not diagonal aka surrounding
lines = True         # We draw the line
walls = True         # We draw the cell wall



mapbuffer = ""
factionbuffer = ""
kind2id={}
overflow=False

if MAP_SIZE >= 24:
    cell_size = 1
    cell_height = 1


out_file = open(out_file_name, 'w')


# Parse the command line
parser = argparse.ArgumentParser()
parser.add_argument('-o', '--outputfile', default=out_file,help='File to collect the actions')
parser.add_argument('-m','--mapsize',default=MAP_SIZE,help='Size of the square battlefield 5-100',type=int, choices=range(5, 101))
parser.add_argument('-f','--factions',default=FACTION_NUM,help='Number of factions fighting 2-8',type=int, choices=range(2,9))
parser.add_argument('-s','--factionsize',default=FACTION_SIZE,help='Number of fighter per faction 5',type=int, choices=range(2,10))
parser.add_argument('-t','--cellthickness',default=cell_height,help='Height of the tile in character',type=int, choices=range(1,6))
parser.add_argument('-w','--cellwidth',default=cell_size,help='Width of the tile in charcher',type=int, choices=range(1,6))
parser.add_argument('-l','--livemap',default=live_map,help='Instant refresh of the map',action='store_true')
parser.add_argument('--status',default=faction_status,help='Display status',action='store_true')


args = parser.parse_args()

if args.outputfile:
    out_file=args.outputfile
if args.mapsize:
    MAP_SIZE=args.mapsize
if args.factions:
    FACTION_NUM=args.factions
if args.factionsize:
    FACTION_SIZE=args.factionsize
if args.cellthickness:
    cell_height=args.cellthickness   
if args.cellwidth:
    cell_size=args.cellwidth
if args.livemap:
    live_map=args.livemap
if args.status:
    faction_status=args.status 


for id,type in enumerate(unit_types):
  kind2id[type["name"].lower()]=id


def cvnotify(cv):
        cv.acquire()
        cv.notify()
        cv.release()

def cvwait(cv,timeout=None):
        cv.acquire()
        if timeout == None:
         cv.wait()
        else:
         cv.wait(timeout=timeout)
        cv.release()

# Class map with lock tilelock[] , one per tile to protect tiles subject during modification ( move in , move out or death of a unit )
#                     maplock , to make or destroy a readonly copy of the map , only available during modification of the global map 
                                            
class Map:
    def __init__(self,size):
        self.maplock = threading.Lock()
        self.map = [[] for i in range(0, (MAP_SIZE * MAP_SIZE))]
        self.copy = []
        self.pending = 0
        self.tilelock = [threading.Lock() for i in range(0, (MAP_SIZE * MAP_SIZE))]

    def get(self):                # Present map or a copy of the map
     viewmap=[]
     with self.maplock:
        if len(self.copy)==0:
            viewmap=self.map # You got the current map , not a copy
        else:
            viewmap=self.copy # Changes are ongoing ... sorry
     return(viewmap)
    
    def xerox(self):              # Duplicate map before doing a modification
     with self.maplock:
        # We take a copy if none exists
        if len(self.copy)==0: 
         self.copy = self.map
        self.pending +=1 
   

    def shred(self):             # Destroy the duplicated map
      with  self.maplock:
        self.pending -=1
        # We a really destroying the map
        if self.pending <= 0:
         self.copy = []


    def moveto(self,previous,location,unit):   # Modify some tiles
        self.xerox()
        # From this point get() will provide self.copy and not self.map
        if previous < 0 or previous >= MAP_SIZE * MAP_SIZE or location < 0 or location >= MAP_SIZE * MAP_SIZE:
           log_queue.put_nowait(f"[Faction {army[unit].faction_name}] {army[unit].name} #{unit} invalid location {previous } {location}")  
           return
        
        # Start of the tile protection 
        with self.tilelock[min(location,previous)]:        
          if location != previous:
           with self.tilelock[max(location,previous)]:
            try:
             self.map[previous].remove(unit)
            except ValueError:
             pass
          if unit not in self.map[location]:
            try:
             self.map[location].append(unit)
            except ValueError:
             pass
        
        # From this point we will destroy self.copy if nobody is changing the map
        self.shred()

    def bury(self,location,unit): # A fighter is leaving the battlefield - modify a tile
        self.xerox()
        # From this point get() will provide self.copy and not self.map
        with self.tilelock[location]:
         try:
          self.map[location].remove(unit)
         except ValueError:
            pass 
        # From this point we will destroy self.copy if nobody is changing the map
        self.shred()
        
# Class fighter with proctection "fighterlock" : health,alive,kill_count ( aka victories ) for method attack
#                                                location, prev_location for method walk()                                                           
#                                                nowere in the code this attributes are changed ( __init__ or under lock protection in method attack or walk  ) 
class Fighter:
    def __init__(self,executor,army,id, kind, faction, location):
        self.epoch_last_move = 0
        self.epoch_last_attack = 0
        self.epoch_last_flush = 0
        self.kill_count = 0                                                         #
        self.fighterlock = threading.Lock()
        self.id = id
        self.faction = faction
        self.kind = kind
        self.name = unit_types[kind]["name"]
        self.faction_name = faction_name[faction]
        self.health = unit_types[kind]["health"]
        self.min = unit_types[kind]["min"]
        self.max = unit_types[kind]["max"]
        self.range = unit_types[kind]["range"]
        self.alive = True
        self.rounds = 0
        self.location = location
        self.prev_location = self.location
        army.append(self)
        self.executor = executor
        self.local_random_t = random.Random()
        self.local_random_m = random.Random()
        self.local_random_d = random.Random()
        if seed > 0:
         self.local_random_t.seed(seed + 2048 + id) # Random for target 
         self.local_random_m.seed(seed + 3072 + id) # Random for move
         self.local_random_d.seed(seed + 4096 + id) # Random for dammage 
         

    def walk(self, location):
        if not self.alive:
            return
        success = False
        with self.fighterlock:
            if self.epoch_last_move < epoch and self.alive and self.prev_location != location:
                self.prev_location = self.location
                self.location = location
                self.epoch_last_move = epoch
                self.rounds += 1
                success = True
        return (success)

    def attack(self, target, local_random):
        success = False
        if not (self.alive and target.alive):
            return (success)
        if target.faction == self.faction:  # Normally already filtered out
            log_queue.put_nowait(f"[Faction {army[self.id].faction_name}] {army[self.id].name} #{self.id} cowardly tried to  {target.name} #{target.id} from the same faction")
            return (success)
        with self.fighterlock:                                                                                   # we protect the data of attacking fighter : health,alive,kill_count(victories)
          with acquire_timeout(target.fighterlock,local_random.randint(0,500)/1000) as acquired:                  # we protect the data of attacked fighter : health,alive,kill_count(victories)
                # 4.4 Each unit attacks every 1 second. 
            if acquired and self.epoch_last_attack < epoch and self.alive and target.alive and distance(self.location, target.location, self.range): # valid : epoch,both alive,range
                damage = local_random.randint(self.min, self.max)                                                # 4.4 Damage is randomized within the unit’s attack range.
                target.health -= damage                                                                        
                self.epoch_last_attack = epoch                                                                   
                success = True
                if target.health <= 0:
                    target.health = 0
                    target.alive = False
                    self.kill_count += 1
                    log_queue.put_nowait(f"[Faction {army[target.id].faction_name}] {target.name} #{target.id} {dposition(army[target.id].location)} was eliminated by [Faction {army[self.id].faction_name}] {self.name} #{self.id} {dposition(army[self.id].location)} with a  {damage} decajoule strike")
                else:
                    log_queue.put_nowait(f"[Faction {army[self.id].faction_name}] {army[self.id].name} #{self.id}  {dposition(army[self.id].location)} attacked [Faction {army[target.id].faction_name}] {target.name} #{target.id} {dposition(army[target.id].location)}, dealing {damage} decajoule damage (health = {target.health})")    
        return (success)

#  End of class Fighter

def dposition(x):
    return (f"({x//MAP_SIZE+1},{x%MAP_SIZE+1})" if x < MAP_SIZE *
            MAP_SIZE else "out of map")


def possible_moves(position, range=1, all=False):
    moves = []
    if range == 0 or all:
        moves.append(position)
    if range == 1 or all:
        if position % MAP_SIZE != 0:  # Not First column
            moves.append(position - 1)
        if position % MAP_SIZE != (MAP_SIZE - 1):  # Not Last column
            moves.append(position + 1)
        if position >= MAP_SIZE:  # Not first row
            moves.append(position - MAP_SIZE)
            if all:  # surrounding but not adjacent
                if (position - MAP_SIZE) % MAP_SIZE != 0:
                    moves.append(position - MAP_SIZE - 1)
                if (position - MAP_SIZE) % MAP_SIZE != MAP_SIZE - 1:
                    moves.append(position - MAP_SIZE + 1)
        if position < (MAP_SIZE * (MAP_SIZE - 1)):  # Not last row
            moves.append(position + MAP_SIZE)
            if all:  # surrounding but not adjacent
                if (position + MAP_SIZE) % MAP_SIZE != 0:
                    moves.append(position + MAP_SIZE - 1)
                if (position + MAP_SIZE) % MAP_SIZE != MAP_SIZE - 1:
                    moves.append(position + MAP_SIZE + 1)
    return [i for i in moves if i >= 0 and i < (MAP_SIZE * MAP_SIZE)]


def distance(position1, position2, range):
    if position1 == position2 and range == 0:
        return (True)
    if range == 1 and position2 in possible_moves(position1):
        return (True)
    return (False)


def possible_attack(position, id, range, faction, all=False):
    global battlemap

    candidate = []

    map=battlemap.get()
    for position in possible_moves(position, range, all=all):
        candidate.extend(map[position])
    
    for friend_of_foe in army:
        if friend_of_foe.faction == faction and friend_of_foe.id in candidate:
            candidate.remove(friend_of_foe.id)
    return (candidate)


def random_pos(position, local_random):
    moves = possible_moves(position)
    return (moves[local_random.randint(0, len(moves) - 1)])




  

def maincurses_thread(stdscr):
    global low_thread_watermark
    global prewar
    global cooldown
    global cliwin
    global refreshscreen
    global faction_status
    global condition_map
    global war
    local_epoch = 0
    local_buffer=""
    map=battlemap.get()
    screenh, screenw = stdscr.getmaxyx()
    stdscr.erase()
    log_queue.put_nowait(f"[Screen] {screenh}x{screenw}")
    curses.start_color()
    curses.use_default_colors()
    # Define some color pairs (foreground, background)
    for faction,color in enumerate(faction_curses):
         curses.init_pair(faction,color[0],color[1])
    mapwinheight=(cell_height+1)*MAP_SIZE+2
    factionwinheight=FACTION_NUM
    cliwinheight=2
    offseth=0
    offsetw=0 
    mapwin = curses.newwin(mapwinheight,(cell_size + 2)* MAP_SIZE + 1, offseth, 0)
    if mapwinheight >= screenh-factionwinheight-cliwinheight:
     offsetw=(cell_size + 2)* MAP_SIZE + 1 + 2
     
    else:
     offseth += mapwinheight
    factionwin = curses.newwin(factionwinheight,24+FACTION_SIZE*(3+4),offseth,offsetw)
    offseth += factionwinheight + 1
    cliwin  = curses.newwin(cliwinheight,64,offseth,offsetw)
     

    while prewar or  war or cooldown:
      if refreshscreen:
        factionwin.clear()
        for x in range(FACTION_NUM):
          factionwin.addstr(x,0,faction_name[x],curses.color_pair(x))
          factionwin.addstr(x,16," ")
          if faction_status: 
           max=0
           for y in army:
            if y.faction == x:
                if y.alive:
                 max +=1
                 if not overflow:
                   factionwin.addstr(f"{y.id:<3}",curses.A_BOLD)
                else:
                 if not overflow:
                   factionwin.addstr(f"{y.id:<3}",curses.A_DIM)
           if not overflow:
             factionwin.addstr(" / ")
             for y in army:
              if y.faction == x:
                factionwin.addstr(f"{y.health:<4}")
           if overflow:
             factionwin.addstr(f"Size {max:<3}",curses.A_BOLD) 
          factionwin.refresh()
        mapwin.clear()
        for i in range(0, MAP_SIZE):
         mapwin.addstr(i*(cell_height+1),0,''.ljust((cell_size + 2) * MAP_SIZE + 1, '-'))
         ioffset=1
         for j in range(0, MAP_SIZE+1):
          for h in range(cell_height+1):
           mapwin.addstr(i*(cell_height+1)+h+1,j*(cell_size+2),'|')
         for j in range(0, MAP_SIZE):
          joffset=1
          for x in map[i * MAP_SIZE + j]:
           local_buffer=f"{x}"
           mapwin.addstr(i*(cell_height+1)+ioffset,j*(cell_size+2)+joffset,local_buffer,unit_curses[army[x].kind]|curses.color_pair(army[x].faction)|curses.A_BOLD) 
           joffset+=len(local_buffer)
        mapwin.addstr(MAP_SIZE*(cell_height+1),0,''.ljust((cell_size + 2) * MAP_SIZE + 1, '-'))
        if mapwinheight >= screenh-factionwinheight-cliwinheight:
         mapwin.addstr(MAP_SIZE*(cell_height+1),MAP_SIZE//3, f"Clock {epoch:<4}")
        else:
         mapwin.addstr(MAP_SIZE*(cell_height+1)+1,0, f"Clock {epoch:<4}")
        mapwin.refresh()
        cliwin.move(0,len(press))
        cliwin.refresh()
      # Wait 5 sec or a refresh ...
      cvwait(condition_map,timeout=map_refresh_rate)
    factionwin.clear()
    cliwin.clear()
    mapwin.clear()
    #stdscr.erase()

    #curses.nocbreak()
    #stdscr.keypad(False)
    #curses.echo()
    
    print(f"{epoch:<4}[Draw] is leaving", file=out_file, end="\n")
    sys.exit(0)
    
def cli_thread():
    global low_thread_watermark
    global prewar
    global cooldown
    global war
    global cliwin
    global refreshscreen
    global faction_status
    global overflow
    global live_map
    global condition_map
    global press
    
    local_epoch = 0
    while prewar or war or cooldown:
     if cliwin:
      cliwin.addstr(0,0,press, curses.A_BOLD | curses.color_pair(1))
      cliwin.move(0,len(press))
      cliwin.refresh()
      #input_str = cliwin.getstr(0,len(press), 1)
      cliwin.getch() 
      cliwin.addstr(0,0,"Refresh is paused but the battle is still raging", curses.A_BOLD | curses.color_pair(1))
      cliwin.addstr(1,0,prompt, curses.A_BOLD|curses.A_BLINK | curses.color_pair(1))
      cliwin.refresh()
      refreshscreen=False
      curses.echo()
      input_str = cliwin.getstr(1,len(prompt), 20)  # Max 20 chars
      curses.noecho()
      cliwin.clear()
      cliwin.refresh()
       
      command=input_str.decode('utf-8') 
      log_queue.put_nowait(f"[Prompt] /{command}/") 
      refreshscreen=True
      if command.lower() in  ("exit","quit","bye","end","q"):
       cliwin.clear()
       cliwin.refresh()
       war=False
       cooldown=True
       press=" Battle is over "
       cvnotify(condition_map)
      if command.lower() in  ["h","help","?"]:
       log_queue.put_nowait(f"[Help] ")
       cliwin.addstr(1,0,"Press a key") 
       cliwin.addstr(0,0,"help , live , status , spawn 5 1 melee ,  spawn 3 1 ranged")
       cliwin.refresh()
       cliwin.getch()  
      if command.lower() in  ("r","refresh"):
       cvnotify(condition_map)
      if command.lower() in ( "l" ,"live"):
       live_map=True
      if command.lower() in ("s","status"):
       if faction_status:
        faction_status=False
        cvnotify(condition_map)
       else:
        faction_status=True 
        cvnotify(condition_map)
      answer=re.findall(r'spawn\s+(\d+)\s+(\d+)\s+(melee|ranged)',command )
      if len(answer):
         log_queue.put_nowait(f"[Spawn] parameters {answer}") 
         localfaction=int(answer[0][1])
         localpopulation=int(answer[0][0])
         localkindtext=answer[0][2].lower()
         if localkindtext in kind2id:
          kind=kind2id[localkindtext] 
          if localfaction >= 0 and localfaction < FACTION_NUM :
           while localpopulation > 0:
            overflow=True
            spawn(localfaction,kind)   # 2 At any time, the user may deploy reinforcements for any faction via terminal commands.
            log_queue.put_nowait(f"[Spawn] birth in faction {localfaction} kind {kind}")
            localpopulation -= 1 
          else:
           log_queue.put_nowait(f"[Spawn] faction {localfaction} is unkown")
         else:
          log_queue.put_nowait(f"[Spawn] type {localkindtext} is unkown")  
              
        
     else:
      sleep(1)
    print(f"{epoch:<4}[Cli] is leaving", file=out_file, end="\n")
    sys.exit(0)
    
# Not perfect but will be more repeatable ( cf seed stuff )
def clock_thread():
    global epoch
    global war
    global cooldown
    global low_thread_watermark
    global condition_map
    global log_queue
    start_gun.acquire()
    start_gun.wait()
    start_gun.release()

    while prewar or war:  # Main , the clock and the display
        for tick in range(100):
            clock_tick.acquire()
            time.sleep(0.01)
            if tick == 50:
             epoch = epoch + 1
            clock_tick.notify_all()
            clock_tick.release()
        factions_left = set([x.faction_name for x in army if x.alive])
        if war and len(factions_left) == 1:
            cooldown = True
            war = False
            winner = next(iter(factions_left))
            log_queue.put_nowait(f"[Faction {winner}] wins the battle!")
            if live_map: 
             cvnotify(condition_map)
        print(file=out_file, end="", flush=True)
    
    log_queue.put_nowait(f"[Clock] is leaving")
    log_queue.put_nowait("QUIT")
    sleep(3)
    cooldown=False
    sys.exit(0)
    
# 3 : Simultaneous combat processing—units must be able to attack in parallel without blocking each other.
# 3 : Independent movement—no unit should wait for another before acting.
# A thread per faction (the commander ) that will give batch of order to each live unit  ( that will not necesseraly succeed )
def commander_thread(faction_id, seed): 
    global epoch
    global war
    global battlemap
    global army
    global condition_map
    global live_map
    start_gun.acquire()
    start_gun.wait()
    start_gun.release()
    
    local_random_c = random.Random()
    if seed > 0:
        local_random_c.seed(seed + 1024 + faction_id) # Random for commander 
    log_queue.put_nowait(f"[Commander] of {faction_name[faction_id]} is ready to dispatch orders")
    while prewar:
     time.sleep(0.1)
    while war:
     local_faction=list(map(lambda n: n.id,list(filter(lambda x: x.alive and x.faction == faction_id, army))))           # My people which are still alive
     if len(local_faction) == 0:
      log_queue.put_nowait(f"[Commander] of {faction_name[faction_id]} is leaving")
      break
     local_results=faction_executor[faction_id].map(fighter_task,local_random_c.sample(local_faction,len(local_faction))) # Submit to a threadpool a task per  fighter
     refresh = False
     for local_result in local_results:
      if local_result > 0 and local_result < 16:    # Detect if our people did something
       refresh = True
     if live_map and refresh: 
             cvnotify(condition_map)
     if not refresh: # If nothing append we sleep , otherwise we try to immediatly attack or move
      time.sleep(0.1)
    log_queue.put_nowait(f"[Commander] of {faction_name[faction_id]} is gone") 
    sys.exit(0)         


def fighter_task(thread_id):
    # Local variable specific to each thread.
    global epoch
    global war
    global battlemap
    global army
    status = 0
    
    if war:
        # I am leaving this world
        if not army[thread_id].alive:
            battlemap.bury(army[thread_id].location,thread_id)
            log_queue.put_nowait(f"[Faction {army[thread_id].faction_name}] {army[thread_id].name} #{thread_id} died in {dposition(army[thread_id].location)} with {army[thread_id].kill_count} victory(ies)")
            status += 2
            return(status)

        if war and army[thread_id].alive and ( army[thread_id].epoch_last_attack < epoch or army[thread_id].epoch_last_move < epoch ):
         # Check if attack possible                                                         # 2: If multiple enemy units occupy the same tile 
         hostiles = possible_attack(army[thread_id].location, thread_id,
                                   army[thread_id].range,
                                   army[thread_id].faction)
        
         if army[thread_id].epoch_last_attack < epoch and len(hostiles):
            for target in army[thread_id].local_random_t.sample(hostiles, len(hostiles)):    # 2: [...] randomly selects a target 
                if army[thread_id].epoch_last_attack < epoch and army[target].alive:                     
                    if army[thread_id].attack(army[target], army[thread_id].local_random_d): # 2: to attack.
                     if not army[target].alive:  
                      battlemap.bury(army[target].location,target)
                     status += 4
                     #log_queue.put_nowait(f"Attack",thread_id,army[thread_id].epoch_last_attack, hostiles)
         else:
          pass
          #log_queue.put_nowait(f"No attack",thread_id,army[thread_id].epoch_last_attack, hostiles) 

         # Check if move possible
         hostiles = possible_attack(army[thread_id].location, thread_id,
                                   army[thread_id].range,
                                   army[thread_id].faction)
         if army[thread_id].epoch_last_move < epoch and len(hostiles) == 0:
            #log_queue.put_nowait(f"Check for move no hostiles", army[thread_id].name,thread_id, hostiles)
            previouslocation = army[thread_id].location
            location = random_pos(army[thread_id].location, army[thread_id].local_random_m)
            if army[thread_id].walk(location):
                # We update the map
                battlemap.moveto(previouslocation,location,thread_id)
                log_queue.put_nowait(f"[Faction {army[thread_id].faction_name}] {army[thread_id].name} #{thread_id} move from {dposition(army[thread_id].prev_location)} to {dposition(army[thread_id].location)}")
                status += 8
         else:
          pass # Cannot move
        else:
          pass
          #log_queue.put_nowait(f"Tour is complete",thread_id,army[thread_id].epoch_last_move,army[thread_id].epoch_last_attack) 
          status += 16
       
        
        return(status)

def log_thread(): # threading reading a msg queue 3 : Efficient logging—game events should be recorded in a text file (battle_log.txt) without interrupting gameplay.
    global war
    global prewar
    global log_queue
    while prewar or  war or cooldown: 
        try:
            msg = log_queue.get()      # We read the message from a queue 
            if msg == "QUIT":
                break
            print(f"{epoch:<4}{msg}",file=out_file, end="\n")
        except Exception:
            continue
    print(f"{epoch:<4}[Logger is gone]", file=out_file, end="\n")
    sys.exit(0)
    
def spawn(faction,kind):
 global units
 global threads
 global army
 global battlemap
 global live_map
 global condition_map
 if True:
        giveashot=10000
        while giveashot > 0:
            candidateposition = random.randint(0, MAP_SIZE * MAP_SIZE-1)  # Global random # 2 Each faction’s units spawn at random locations, maintaining at least one tile of separation from other factions.
            giveashot -= 1
            if len(possible_attack(candidateposition, units, 1, faction, all=True)) == 0: # 2 [...] at least one tile of separation from other factions
                fighter=Fighter(faction_executor[faction],army,units,kind, faction,
                        candidateposition)
                battlemap.moveto(candidateposition,candidateposition,units)
                if live_map:
                 cvnotify(condition_map)
                units += 1
                giveashot=-units
 return(giveashot) 
 
# Create a list to hold our thread objects.

battlemap=Map(MAP_SIZE)
threads = []
units = 0
army = []
armylock = threading.Lock()
log_queue = queue.Queue()



if seed > 0:
    random.seed(seed)  # Global random

if __name__ =="__main__":

 # Log queue
 t = threading.Thread(target=log_thread, args=())
 threads.append(t)
 t.start()

if __name__ =="__main__":
 # Draw thread
 t = threading.Thread(target=cli_thread, args=())
 threads.append(t)
 t.start()

if __name__ =="__main__":
 sleep(2)

 for faction in range(0, FACTION_NUM):
  faction_executor[faction]=concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKER_PER_FACTION)

 for faction in range(0, FACTION_NUM):                         # 4.1 The number of factions (players) can be set between 2 to 8.
    for j in range(0, FACTION_SIZE):                          # size of the faction (size of the team)
        kind=random.randint(0, number_of_unit_types - 1)      # we have to choose between 0,1 (0 is melee and 1 is ranged )
        if spawn(faction,kind) == 0:
            log_queue.put_nowait(f"[Units {units}] didnt find a place , aborting the battle")
            war=False
if __name__ =="__main__":
 for faction in range(0, FACTION_NUM):
  t = threading.Thread(target=commander_thread,args=(faction,seed,))
  threads.append(t)
  t.start()

if __name__ =="__main__":
 sleep(0.5)

 war=True
 prewar=False

 # Clock
 t = threading.Thread(target=clock_thread, args=())
 threads.append(t)
 t.start()


if __name__ =="__main__":
 start_gun.acquire()
 start_gun.notify_all()
 start_gun.release()

 # This also a thread
 curses.wrapper(maincurses_thread)
 curses.echo()

 print("SALUT#####################################################")

    
 # Wait for all threads to complete.
 for t in threads:
    t.join()


