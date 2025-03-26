import threading
import time
import random
from termcolor import colored
import sys
import os

from queue import Empty, Queue

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
    'red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white', 'grey'
]

# Global variable shared by all threads.

FACTION_NUM = 2  # 4  # 2 -> 8
FACTION_SIZE = 5  # Numbers of warriors in each faction
MAP_SIZE = 5  # 30 # 5 -> 100
low_thread_watermark = 4  # clock + map + draw + main
out_file_name = "battle_log.txt"
number_of_unit_types = len(unit_types)
seed = 4
round = 10
epoch = 0
war = True
peace = True
warrior_speed = 0.2
cell_size = 3
surrounding = False  # diagonal OK ?
lines = True
walls = True
step = 3

if MAP_SIZE > 24:
    cell_size = 1
if MAP_SIZE > 24:
    lines = False
    walls = False
if FACTION_NUM * FACTION_SIZE > 10:
    cell_size = 2


queue_map_event = Queue()

out_file = open(out_file_name, 'w')

class Map:
    def __init__(self, id,size):
        self.lock = threading.Lock()
        self.map = [[] for i in range(0, (MAP_SIZE * MAP_SIZE))]
        self.copy = []
        self.pending = 0
        self.celllock = [threading.Lock() for i in range(0, (MAP_SIZE * MAP_SIZE))]
    
    def get(self)
        self.lock.acquire()
        viewmap=[]
        if len(self.copy)==0:
            viewmap=self.map # You got the current map , not a copy
        else:
            viewmap=self.copy # Changes are ongoing ... sorry
        self.lock.release()
        return(viewmap)
    
    def xerox(self)
        self.lock.acquire()
        if len(self.copy)==0: 
         self.copy = self.map
        self.pending +=1 
        self.lock.release()

    def shred(self)    
        self.lock.acquire()
        self.pending -=1
        if self.pending <= 0:
         self.copy = []
        self.lock.release()

    def moveto(self,previous,location,unit,):
        self.xerox()
        if previous != location:
         self.celllock[previous].acquire()
         try:
            self.map[previous].remove(unit)
         except ValueError:
            pass
         self.celllock[previous].release()
        self.celllock[location].acquire()
        if unit not in self.map[location]
         try:
            self.map[location].extend(unit)
         except ValueError:
            pass
        self.celllock[location].release()
        self.shred()
        
    def bury(self,location,unit):
        self.xerox()
        self.celllock[location].acquire()
        try:
            self.map[location].remove(unit)
        except ValueError:
            pass
        self.celllock[location].release()
        self.shred()
        

class Fighter:

    def __init__(self, id, kind, faction, location):
        self.epoch_last_move = 0
        self.epoch_last_attack = 0
        self.epoch_last_flush = 0
        self.kill_count = 0
        self.lock = threading.Lock()
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

    def moveto(self, location, queue_map_event):
        if not self.alive:
            return
        success = False
        self.lock.acquire()

        try:
            if self.epoch_last_move < epoch and self.alive and self.prev_location != location:
                self.prev_location = self.location
                self.location = location
                self.epoch_last_move = epoch
                self.rounds += 1
                success = True
                try:
                    queue_map_event.put_nowait(0)
                except Full:
                    print(
                        f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} {self.id} queue full",
                        file=out_file,
                        end="\n")
                #print(self.id,"is on the move from ",self.prev_location," to ",self.location)
        finally:
            self.lock.release()
        return (success)

    def attack(self, target, local_random):
        success = False
        if not (self.alive and target.alive):
            return (success)
        if target.faction == self.faction:  # Normally already filtered out
            print(
                f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} {self.id} cowardly tried to  {target.name} {target.id} from the same faction",
                file=out_file,
                end="\n")
            return (success)
        target.lock.acquire()
        self.lock.acquire()
        try:
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
                        f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} {self.id} {dposition(army[self.id].location)} attacked {target.name} {target.id} {dposition(army[target.id].location)}  with damage {damage} and killed it",
                        file=out_file,
                        end="\n")
                else:
                    print(
                        f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} {self.id}  {dposition(army[self.id].location)} attacked {target.name} {target.id} {dposition(army[target.id].location)}  with damage {damage} {target.health}",
                        file=out_file,
                        end="\n")
        finally:
            self.lock.release()
            target.lock.release()

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
    global map

    candidate = []

    maplock.acquire()
    for position in possible_moves(position, range, all=all):
        candidate.extend(map[position])
    maplock.release()

    for friend_of_foe in army:
        if friend_of_foe.faction == faction and friend_of_foe.id in candidate:
            candidate.remove(friend_of_foe.id)
    return (candidate)


def random_pos(position, local_random):
    moves = possible_moves(position)
    return (moves[local_random.randint(0, len(moves) - 1)])


def print_map():
    global map
    global army
    allfactions = {}
    i = 0
    j = 0
    print(end="\n\n")
    if lines:
        print(''.ljust((cell_size + 1) * MAP_SIZE + 1, '-'), end="\n")
    for i in range(0, MAP_SIZE):
        if walls:
            print("|", end="")
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
            print(f"{buffer}{padding}", end="")
            if walls:
                print("|", end="")
        print(end="\n")
        if lines:
            print(''.ljust((cell_size + 1) * MAP_SIZE + 1, '-'), end="\n")
    for x in range(FACTION_NUM):
        print(colored(f"{faction_name[x]:<16}", faction_color[x]), end="")
        for y in army:
            if y.faction == x:
                print(f"{y.id:<2}", end=" ")
        print(end=" -- ")
        for y in army:

            if y.faction == x:
                print(f"{y.health:<4}", end=" ")
        print(end="\n")

def update_map():
    global map
    global maplock
    newmap = [[] for i in range(0, (MAP_SIZE * MAP_SIZE))]
    maplock.acquire()
    for unit in range(0, len(army)):
        if army[unit].alive:
            newmap[army[unit].location].append(unit)
    map = newmap
    maplock.release()
    
def map_thread(thread_id, queue_map_event):
    global map
    global army
    global war
    global epoch
    global low_thread_watermark
    local_epoch = 0
    while peace or threading.active_count() > low_thread_watermark:
        try:
            event = queue_map_event.get(block=True, timeout=1)
        except Empty:
            pass
        update_map()
        print(
                f"{epoch:<4}GMap {map}",
                file=out_file,
                end="\n")
        print(file=out_file, end="", flush=True)
        while not queue_map_event.empty():
             try:
                event = queue_map_event.get(False)
                if event == 1:
                    update_map()
                    print(
                        f"{epoch:<4}GMap {map}",
                        file=out_file,
                        end="\n")
                    print(file=out_file, end="", flush=True)
             except Empty:
                pass
        


def draw_thread(thread_id, queue_map_event):
    global map
    global army
    global war
    global epoch
    global low_thread_watermark
    local_epoch = 0
    while peace or threading.active_count() > low_thread_watermark:
        clear()
        print_map()
        time.sleep(0.5)


# Not perfect but will be more repeatable ( cf seed stuff )
def clock_thread(thread_id, queue_map_event):
    global epoch
    global war
    global low_thread_watermark
    global step
    while peace or threading.active_count(
    ) > low_thread_watermark:  # Main , the clock and the display
        time.sleep(step)
        epoch = epoch + 1
        if not peace:
         factions_left = set([x.faction_name for x in army if x.alive])
         if war and len(factions_left) == 1:
            war = False
            winner = next(iter(factions_left))
            print(f"{epoch:<4}[Faction {winner}] won the battle",
                  file=out_file,
                  end="\n")
        print(file=out_file, end="", flush=True)
    print(f"{epoch:<4}[Clock] is leaving", file=out_file, end="\n")


def fighter_thread(thread_id, seed, queue_map_event):
    # Local variable specific to each thread.
    global epoch
    global war
    local_counter = 0
    local_random = random.Random()
    if seed > 0:
        local_random.seed(seed + thread_id)
    global map
    global army
    while war:
        # I am leaving this world
        if not army[thread_id].alive:
            print(
                f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} {thread_id} died in {dposition(army[thread_id].location)} with {army[thread_id].kill_count} victory(ies)",
                file=out_file,
                end="\n")
            break

        # Update the local counter.
        local_counter += 1

        # Check if attack possible
        hostiles = possible_attack(army[thread_id].location, thread_id,
                                   army[thread_id].range,
                                   army[thread_id].faction)
        if len(hostiles):
            for target in local_random.sample(hostiles, len(hostiles)):
                if army[thread_id].epoch_last_attack < epoch and army[
                        target].alive:
                    army[thread_id].attack(army[target], local_random)
        # Check if move possible
        hostiles = possible_attack(army[thread_id].location, thread_id,
                                   army[thread_id].range,
                                   army[thread_id].faction)
        if army[thread_id].epoch_last_move < epoch and len(hostiles) == 0:
            #print("Check for move no hostiles", army[thread_id].name,thread_id, hostiles)
            location = random_pos(army[thread_id].location, local_random)
            if army[thread_id].moveto(location, queue_map_event):
                print(
                    f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} {thread_id} , {dposition(army[thread_id].prev_location)} -> {dposition(army[thread_id].location)} ",
                    file=out_file,
                    end="\n")
        if army[thread_id].epoch_last_flush < epoch:
            army[thread_id].epoch_last_flush = epoch
            print(file=out_file, end="", flush=True)
        time.sleep(warrior_speed)  # Simulate work.

    if army[thread_id].alive:
        print(
            f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} {thread_id} {dposition(army[thread_id].location)} going back home with {army[thread_id].kill_count} victory(ies)",
            threading.active_count(),
            file=out_file,
            end="\n")


# Create a list to hold our thread objects.
threads = []
units = 0
army = []
if seed > 0:
    random.seed(seed)  # Global random

# Clock
t = threading.Thread(target=clock_thread, args=(units, queue_map_event))
threads.append(t)
t.start()

# Map thread
t = threading.Thread(target=map_thread, args=(units + 1, queue_map_event))
threads.append(t)
t.start()

# Draw thread
t = threading.Thread(target=draw_thread, args=(units + 2, queue_map_event))
threads.append(t)
t.start()

sleep(2)

for i in range(0, FACTION_NUM):
    for j in range(0, FACTION_SIZE):
        giveashot=10000
        while giveashot > 0:
            candidateposition = random.randint(0, MAP_SIZE *
                                           MAP_SIZE)  # Global random
            print(
            f"Candidate {units} is inspecting {dposition(candidateposition)}{possible_attack(candidateposition,units,1,i,all=True)}",
            file=out_file,
            end="\n")
            giveashot -= 1
            if len(possible_attack(candidateposition, units, 1, i, all=True)) == 0:
                army.append(Fighter(units, random.randint(0, number_of_unit_types - 1), i,
                        candidateposition))
                update_map()
                #queue_map_event.put(1)
                #queue_map_event.put(1)
                units += 1
                giveashot=0
                
        else:
            print(
                f"Candiate {units} is rejected {possible_attack(candidateposition,units,1,i,all=True)}",
                file=out_file,
                end="\n")



# Make all fighters alive
for i in range(units):
    t = threading.Thread(target=fighter_thread,
                         args=(
                             i,
                             seed,
                             queue_map_event,
                         ))
    threads.append(t)
    t.start()


peace=False

    
# Wait for all threads to complete.
for t in threads:
    t.join()
