from threading import Condition
import threading
import time
import random
from termcolor import colored
import sys
import os

# Dynamic population

# import call method from subprocess module
from subprocess import call

# import sleep to show output for some time period
from time import sleep


# define clear function
def clear():
    # check and make call for specific operating system
    _ = call('clear' if os.name == 'posix' else 'cls')


unit_types = [
    {
        'name': "Melee",
        #'nickname': "M",
        'nickname': "",
        'start': '\033[4m',
        'end': '\033[0m',
        'health': 120,
        'min': 20,
        'max': 30,
        'range': 0
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
        'range': 1
    }
]

faction_name = [
    "Uni staff", "The Goblins", "The Orcs", "The Trolls", "The Giants",
    "The Dragons", "The Golems", "The Gnomes"
]
faction_color = [
    'red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'black', 'grey'
]

# Global variable shared by all threads.

FACTION_NUM = 3  # 4  # 2 -> 8
FACTION_SIZE = 5  # Numbers of warriors in each faction
MAP_SIZE = 5  # 30 # 5 -> 100
low_thread_watermark = 3  # clock  + draw + main
out_file_name = "battle_log.txt"
number_of_unit_types = len(unit_types)
seed = 4   # Seed for main thread
epoch = 0  # Will be updated by the clock

clock_tick = Condition()    # To wake up all thread at the same time
condition_map = Condition() # To redraw the map ?
start_gun = Condition()

cadence = True           # All fighter will wake up at the same time 
war = True   # Battle is running
peace = True # Peace  
cell_size = 3        # Cell size
surrounding = False  # We do adjacent , not diagonal aka surrounding
lines = True         # We draw the line
walls = True         # We draw the cell wall


if MAP_SIZE > 24:
    cell_size = 1
if MAP_SIZE > 24:
    lines = False
    walls = False
if FACTION_NUM * FACTION_SIZE > 10:
    cell_size = 2

out_file = open(out_file_name, 'w')

def cvnotify(cv):
        cv.acquire()
        cv.notify()
        cv.release()

def cvwait(cv,timeout=None):
        cv.acquire()
        if timeout == None:
         cv.wait()
        else:
         try:
          cv.wait(timeout=timeout)
         except Empty:
          pass
        cv.release()


class Map:
    def __init__(self,size):
        self.maplock = threading.Lock()
        self.map = [[] for i in range(0, (MAP_SIZE * MAP_SIZE))]
        self.copy = []
        self.pending = 0
        self.tilelock = [threading.Lock() for i in range(0, (MAP_SIZE * MAP_SIZE))]

    def get(self):
     viewmap=[]
     with self.maplock:
        if len(self.copy)==0:
            viewmap=self.map # You got the current map , not a copy
        else:
            viewmap=self.copy # Changes are ongoing ... sorry
     return(viewmap)
    
    def xerox(self):
     with self.maplock:
        # We take a copy if none exists
        if len(self.copy)==0: 
         self.copy = self.map
        self.pending +=1 
   

    def shred(self):
      with  self.maplock:
        self.pending -=1
        # We a really destroying the map
        if self.pending <= 0:
         self.copy = []


    def moveto(self,previous,location,unit):
        self.xerox()
        # From this point get() will provide self.copy and not self.map
        if previous < 0 or previous >= MAP_SIZE * MAP_SIZE or location < 0 or location >= MAP_SIZE * MAP_SIZE:
           print(f"{epoch:<4}[Faction {army[unit].faction_name}] {army[unit].name} #{unit} invalid location {previous } {location}",file=out_file,end="\n")  
           return
        
        # Start of the tile protection
        if previous != location:
         self.tilelock[previous].acquire()
        self.tilelock[location].acquire() 
        try:
            self.map[previous].remove(unit)
        except ValueError:
            pass        
        if unit not in self.map[location]:
         try:
            self.map[location].append(unit)
         except ValueError:
            pass
        # End of the tile protection 
        self.tilelock[location].release()
        if previous != location:
         self.tilelock[previous].release()
        
        # From this point we will destroy self.copy if nobody is changing the map
        self.shred()

    def bury(self,location,unit): # A fighter is leaving the battlefield
        self.xerox()
        # From this point get() will provide self.copy and not self.map
        self.tilelock[location].acquire()
        try:
            self.map[location].remove(unit)
        except ValueError:
            pass
        self.tilelock[location].release()
        # From this point we will destroy self.copy if nobody is changing the map
        self.shred()
        

class Fighter:

    def __init__(self,threads,army,id, kind, faction, location):
        self.epoch_last_move = 0
        self.epoch_last_attack = 0
        self.epoch_last_flush = 0
        self.kill_count = 0
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
        self.t = threading.Thread(target=fighter_thread,args=(id,seed,condition_map,))
        threads.append(self.t)
        self.t.start()

    def moveto(self, location,condition_map):
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
            print(
                f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} #{self.id} cowardly tried to  {target.name} #{target.id} from the same faction",
                file=out_file,
                end="\n")
            return (success)
        with self.fighterlock:
         with target.fighterlock:
            if self.epoch_last_attack < epoch and self.alive and target.alive and distance(
                    self.location, target.location, self.range):
                damage = local_random.randint(self.min, self.max + 1)
                target.health -= damage
                self.epoch_last_attack = epoch
                success = True
                if target.health <= 0:
                    target.alive = False
                    self.kill_count += 1
                    print(
                        f"{epoch:<4}[Faction {army[target.id].faction_name}] {target.name} #{target.id} {dposition(army[target.id].location)} was eliminated by [Faction {army[self.id].faction_name}] {self.name} #{self.id} {dposition(army[self.id].location)} with a  {damage} decajoule strike",
                        file=out_file,
                        end="\n")
                else:
                    print(
                        f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} #{self.id}  {dposition(army[self.id].location)} attacked [Faction {army[target.id].faction_name}] {target.name} #{target.id} {dposition(army[target.id].location)}, dealing {damage} decajoule damage (health = {target.health})",
                        file=out_file,
                        end="\n")    
        return (success)


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


def print_map():
    global battlemap
    global army
    mapbuffer=""
    factionbuffer=""
    allfactions = {}
    i = 0
    j = 0
    map=battlemap.get()
    #print(end="\n\n")
    mapbuffer +="\n"
    factionbuffer += "\n" 
    if lines:
        #print(''.ljust((cell_size + 1) * MAP_SIZE + 1, '-'), end="\n")
        mapbuffer += ''.ljust((cell_size + 1) * MAP_SIZE + 1, '-') + "\n"
    for i in range(0, MAP_SIZE):
        if walls:
            #print("|", end="")
            mapbuffer += "|"
        for j in range(0, MAP_SIZE):
            rawbuffer = ",".join("%s%d" %
                                 (unit_types[army[x].kind]["nickname"], x)
                                 for x in map[i * MAP_SIZE + j])
            lpadding = cell_size - len(rawbuffer)
            if lpadding <= 0:
                lpadding = 0
                padding = ""
            else:
                padding = ' '.ljust(lpadding)
            buffer = ",".join(
                colored(
                    "%s%s%d%s" % (unit_types[army[x].kind]["start"],
                                  unit_types[army[x].kind]["nickname"], x,
                                  unit_types[army[x].kind]["end"]),
                    faction_color[army[x].faction])
                for x in map[i * MAP_SIZE + j])
            #print(f"{buffer}{padding}", end="")
            mapbuffer += f"{buffer}{padding}"
            if walls:
                #print("|", end="")
                mapbuffer += "|"
        #print(end="\n")
        mapbuffer += "\n"
        if lines:
            #print(''.ljust((cell_size + 1) * MAP_SIZE + 1, '-'), end="\n")
            mapbuffer += ''.ljust((cell_size + 1) * MAP_SIZE + 1, '-') + "\n"
    for x in range(FACTION_NUM):
        #print(colored(f"{faction_name[x]:<16}", faction_color[x]), end="")
        factionbuffer +=  colored(f"{faction_name[x]:<16}", faction_color[x])
        for y in army:
            if y.faction == x:
                #print(f"{y.id:<2}", end=" ")
                factionbuffer += f"{y.id:<3}"
        #print(end=" -- ")
        factionbuffer += " -- " 
        for y in army:

            if y.faction == x:
                #print(f"{y.health:<4}", end=" ")
                factionbuffer +=  f"{y.health:<4}"
        #print(end="\n")
        factionbuffer += "\n"
    print(mapbuffer,end="")
    print(factionbuffer,end="")
    


    


def draw_thread(thread_id,condition_map):
    global low_thread_watermark
    global peace
    local_epoch = 0
    while peace or threading.active_count() > low_thread_watermark:
        clear()
        print_map()
        # Wait 0.5 or event
        cvwait(condition_map,timeout=0.5)
   
        


# Not perfect but will be more repeatable ( cf seed stuff )
def clock_thread(thread_id,condition_map):
    global epoch
    global war
    global low_thread_watermark
    
    start_gun.acquire()
    start_gun.wait()
    start_gun.release()

    while peace or threading.active_count(
    ) > low_thread_watermark:  # Main , the clock and the display
        for tick in range(100):
            clock_tick.acquire()
            time.sleep(0.01)
            if tick == 50:
             epoch = epoch + 1
            clock_tick.notify_all()
            clock_tick.release()
        
        if not peace:
         factions_left = set([x.faction_name for x in army if x.alive])
         if war and len(factions_left) == 1:
            war = False
            winner = next(iter(factions_left))
            print(f"{epoch:<4}[Faction {winner}] wins the battle!",
                  file=out_file,
                  end="\n")
            cvnotify(condition_map)
        print(file=out_file, end="", flush=True)

    print(f"{epoch:<4}[Clock] is leaving", file=out_file, end="\n")


def fighter_thread(thread_id, seed,condition_map):
    # Local variable specific to each thread.
    global epoch
    global war
    local_random = random.Random()
    if seed > 0:
        local_random.seed(seed + thread_id)
    global battlemap
    global army
    start_gun.acquire()
    start_gun.wait()
    start_gun.release()
    while war:
        # I am leaving this world
        if not army[thread_id].alive:
            battlemap.bury(army[thread_id].location,thread_id)
            print(
                f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} #{thread_id} died in {dposition(army[thread_id].location)} with {army[thread_id].kill_count} victory(ies)",
                file=out_file,
                end="\n")
            break

        while war and army[thread_id].alive and ( army[thread_id].epoch_last_attack < epoch or army[thread_id].epoch_last_move < epoch ):
         # Check if attack possible
         hostiles = possible_attack(army[thread_id].location, thread_id,
                                   army[thread_id].range,
                                   army[thread_id].faction)
        
         if army[thread_id].epoch_last_attack < epoch and len(hostiles):
            for target in local_random.sample(hostiles, len(hostiles)):
                if army[thread_id].epoch_last_attack < epoch and army[target].alive:                     
                    if army[thread_id].attack(army[target], local_random) and not army[target].alive:
                     battlemap.bury(army[target].location,target)
                     cvnotify(condition_map)
                     #print(f"{epoch:<4}Attack",thread_id,army[thread_id].epoch_last_attack, hostiles,file=out_file,end="\n")

         else:
          pass
          #print(f"{epoch:<4}No attack",thread_id,army[thread_id].epoch_last_attack, hostiles,file=out_file,end="\n") 
          time.sleep(0.01)
         # Check if move possible
         hostiles = possible_attack(army[thread_id].location, thread_id,
                                   army[thread_id].range,
                                   army[thread_id].faction)
         if army[thread_id].epoch_last_move < epoch and len(hostiles) == 0:
            #print("Check for move no hostiles", army[thread_id].name,thread_id, hostiles)
            previouslocation = army[thread_id].location
            location = random_pos(army[thread_id].location, local_random)
            if army[thread_id].moveto(location,condition_map):
                # We update the map
                battlemap.moveto(previouslocation,location,thread_id)
                print(
                    f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} #{thread_id} move from {dposition(army[thread_id].prev_location)} to {dposition(army[thread_id].location)}",
                    file=out_file,
                    end="\n")
                cvnotify(condition_map)
         else:
          pass
          time.sleep(0.01)
        else:
          pass
          #print(f"{epoch:<4}Tour is complete",thread_id,army[thread_id].epoch_last_move,army[thread_id].epoch_last_attack,file=out_file,end="\n") 

        if army[thread_id].epoch_last_flush < epoch:
            army[thread_id].epoch_last_flush = epoch
            print(file=out_file, end="", flush=True)
        
        if cadence:
         time.sleep(0.1)
         clock_tick.acquire()
         clock_tick.wait()
         clock_tick.release()
        else:
            time.sleep(0.1)  # Simulate work.

    if army[thread_id].alive:
            print(f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} #{thread_id} {dposition(army[thread_id].location)} going back home with {army[thread_id].kill_count} victory(ies)",file=out_file,end="\n")


# Create a list to hold our thread objects.

battlemap=Map(MAP_SIZE)
threads = []
units = 0
army = []
if seed > 0:
    random.seed(seed)  # Global random

# Clock
t = threading.Thread(target=clock_thread, args=(units,condition_map))
threads.append(t)
t.start()


# Draw thread
t = threading.Thread(target=clock_thread, args=(units,condition_map))
t = threading.Thread(target=draw_thread, args=(units + 2,condition_map))
threads.append(t)
t.start()
sleep(2)

for i in range(0, FACTION_NUM):
    for j in range(0, FACTION_SIZE):
        giveashot=10000
        while giveashot > 0:
            candidateposition = random.randint(0, MAP_SIZE *
                                           MAP_SIZE-1)  # Global random
            giveashot -= 1
            if len(possible_attack(candidateposition, units, 1, i, all=True)) == 0:
                fighter=Fighter(threads,army,units,random.randint(0, number_of_unit_types - 1), i,
                        candidateposition)
                battlemap.moveto(candidateposition,candidateposition,units)
                cvnotify(condition_map)
                units += 1
                giveashot=-units                
        if giveashot == 0:
            print(f"{epoch:<4}[Units {units}] didnt find a place , aborting the battle",file=out_file,end="\n")
            war=False



sleep(0.5)
peace=False
start_gun.acquire()
start_gun.notify_all()
start_gun.release()


    
# Wait for all threads to complete.
for t in threads:
    t.join()
