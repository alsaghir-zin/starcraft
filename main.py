import threading
import time
import random
from termcolor import colored
import sys
import os

# import call method from subprocess module
from subprocess import call

# import sleep to show output for some time period
from time import sleep

# define clear function
def clear():
    # check and make call for specific operating system
    _ = call('clear' if os.name == 'posix' else 'cls')

warrior_spec = [{
    'name': "Melee",
    #'nickname': "M",
    'nickname': "",
    'start' : '\033[4m',
    'end' :'\033[0m',
    'health': 120,
    'min': 20,
    'max': 30,
    'range': 0
}, {
    'name': "Ranged",
    #'nickname': "R",
    'nickname': "",
    'start' : '',
    'end' :'',
    'health': 80,
    'min': 10,
    'max': 20,
    'range': 1
}]

faction_name = [
    "Uni staff", "The Goblins", "The Orcs", "The Trolls", "The Giants",
    "The Dragons", "The Golems", "The Gnomes"
]
faction_color = [
    'red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white', 'grey'
]

# Global variable shared by all threads.
out_file_name = "battle_log.txt"
faction_num = 4  # 2 -> 8
faction_size = 5  # Numbers of warriors in each faction
MAP_SIZE = 30 # 5 -> 100
KINDS = 2
global_counter = 0
seed = 4
round = 10
epoch = 0
war = True
warrior_speed=0.2
cell_size=3
surrounding = False
lines=True
walls=True

if MAP_SIZE > 24:
    cell_size=1
if MAP_SIZE > 24:
    lines=False
    walls=False
if faction_num * faction_size > 10:
    cell_size=2


map = [[] for i in range(0, (MAP_SIZE * MAP_SIZE))]
# A lock to ensure thread-safe updates to the global variable.
counter_lock = threading.Lock()

out_file = open(out_file_name, 'w')


class Fighter:

    def __init__(self, id, kind, faction):
        self.epoch_last_move = 0
        self.epoch_last_attack = 0
        self.epoch_last_flush = 0
        self.kill_count = 0
        self.lock = threading.Lock()
        self.id = id
        self.faction = faction
        self.kind = kind
        self.name = warrior_spec[kind]["name"]
        self.faction_name = faction_name[faction]
        self.health = warrior_spec[kind]["health"]
        self.min = warrior_spec[kind]["min"]
        self.max = warrior_spec[kind]["max"]
        self.range = warrior_spec[kind]["range"]
        self.alive = True
        self.rounds = 0
        self.location = random.randint(0, MAP_SIZE * MAP_SIZE) # Global random
        self.prev_location = self.location

    def moveto(self, location):
        if not self.alive:
            return
        self.lock.acquire()
        try:
            if self.epoch_last_move < epoch and self.alive and self.prev_location != location:
                self.prev_location = self.location
                self.location = location
                self.epoch_last_move = epoch
                self.rounds += 1
                #print(self.id,"is on the move from ",self.prev_location," to ",self.location)
        finally:
            self.lock.release()

    def attack(self, target, local_random):
        if not (self.alive and target.alive):
            return
        if target.faction == self.faction:  # Normally already filtered out
            print(
                f"{epoch:<4}[Faction {army[self.id].faction_name}] {army[self.id].name} {self.id} cowardly tried to  {target.name} {target.id} from the same faction",
                file=out_file,
                end="\n")
            return
        target.lock.acquire()
        self.lock.acquire()
        try:
            if self.epoch_last_attack < epoch and self.alive and target.alive and distance(
                    self.location, target.location, self.range):
                damage = local_random.randint(self.min, self.max + 1)
                target.health -= damage
                self.epoch_last_attack = epoch
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

def dposition(x):
    return(f"({x//MAP_SIZE},{x%MAP_SIZE})" if x < MAP_SIZE * MAP_SIZE else "out of map")

def possible_moves(position):
    moves = []
    if position % MAP_SIZE != 0:                # Not First column
        moves.append(position - 1)
    if position % MAP_SIZE != (MAP_SIZE - 1):  # Not Last column
        moves.append(position + 1)
    if position >= MAP_SIZE:                    # Not first row
        moves.append(position - MAP_SIZE)
        if surrounding:                         # surrounding but not adjacent
         if (position - MAP_SIZE) % MAP_SIZE != 0:           
            moves.append(position - MAP_SIZE - 1)
         if (position - MAP_SIZE) % MAP_SIZE != MAP_SIZE - 1:
            moves.append(position - MAP_SIZE + 1)
    if position < (MAP_SIZE * (MAP_SIZE - 1)):  # Not last row
        moves.append(position + MAP_SIZE)
        if surrounding:                         # surrounding but not adjacent
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


def possible_attack(position, id, range, faction):
    global map
    candidate = []
    if range == 0:
        candidate.extend(map[position])
        #print(".................",position,candidate,"..........")
        try:
            candidate.remove(id)
        except:
            pass
    if range == 1:
        for position in possible_moves(position):
            candidate.extend(map[position])
    for friend_of_foe in army:
        if friend_of_foe.faction == faction and friend_of_foe.id in candidate:
            candidate.remove(friend_of_foe.id)
    return (candidate)


def random_pos(position, local_random):
    moves = possible_moves(position)
    #print(position, moves, len(moves))
    return (moves[local_random.randint(0, len(moves) - 1)])


def print_map():
    global map
    global army
    allfactions = {}
    i = 0
    j = 0
    print(end="\n\n")
    if lines:
     print(''.ljust((cell_size+1)*MAP_SIZE+1,'-'),end="\n")
    for i in range(0, MAP_SIZE):
        if walls:
            print("|", end="")
        for j in range(0, MAP_SIZE):
            rawbuffer = ",".join("%s%d" % (warrior_spec[army[x].kind]["nickname"], x) for x in map[i * MAP_SIZE + j])
            lpadding = cell_size-len(rawbuffer)
            if lpadding <= 0:
                lpadding = 0
                padding=""
            else:
                padding = ' '.ljust(lpadding)
            buffer=",".join(colored("%s%s%d%s" % (warrior_spec[army[x].kind]["start"],warrior_spec[army[x].kind]["nickname"],x,warrior_spec[army[x].kind]["end"]),faction_color[army[x].faction]) for x in map[i * MAP_SIZE + j])
            print(f"{buffer}{padding}",end="")
            if walls:
                print("|", end="")    
        print(end="\n")
        if lines:
         print(''.ljust((cell_size+1)*MAP_SIZE+1,'-'),end="\n")
    for x in range(faction_num):   
     print(colored(f"{faction_name[x]:<16}",faction_color[x]),end="")
     for y in army:
        if y.faction == x:
                 print(f"{y.id:<2}",end=" ")
     print(end=" -- ")
     for y in army:
      
         if y.faction == x:
            print(f"{y.health:<4}",end=" ")
     print(end="\n")


def display(thread_id):
    global map
    global army
    global war
    global epoch
    local_epoch=0
    while epoch < 10 or threading.active_count() > 3:
        for thread_id in range(0, len(army)):
            try:
                if thread_id in map[army[thread_id].prev_location]:
                    map[army[thread_id].prev_location].remove(thread_id)
                if thread_id in map[army[thread_id].
                                    location] and not army[thread_id].alive:
                    map[army[thread_id].location].remove(thread_id)
            except Exception as e:
                pass
            try:
                if thread_id not in map[
                        army[thread_id].location] and army[thread_id].alive:
                    map[army[thread_id].location].append(thread_id)
            except Exception as e:
                pass
        
        for x in range(len(map)):
                for y in map[x]:
                    if army[y].location != x:
                        try:
                            map[x].remove(y)
                            print(f"{epoch:<4}[Display]  {y} ghosting in {dposition(x)}",
                                file=out_file,
                                end="\n")
                        except Exception as e:
                            pass
                            
        clear()
        print_map()
        time.sleep(0.3)


def clock(thread_id
          ):  # Not perfect but will be more repeatable ( cf seed stuff )
    global epoch
    global global_counter
    global war
    global_counter += 1
    while epoch < 10 or threading.active_count(
    ) > 3:  # Main , the clock and the display
        time.sleep(1) 
        epoch = epoch + 1
        factions_left = set([x.faction_name for x in army if x.alive])
        if war and len(factions_left) == 1:
            war = False
            winner = next(iter(factions_left))
            print(f"{epoch:<4}[Faction {winner}] won the battle",
                  file=out_file,
                  end="\n")
        print(file=out_file,end="", flush=True)
        

def worker(thread_id, seed):
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
            army[thread_id].moveto(location)
            print(
                f"{epoch:<4}[Faction {army[thread_id].faction_name}] {army[thread_id].name} {thread_id} , {dposition(army[thread_id].prev_location)} -> {dposition(army[thread_id].location)} ",
                file=out_file,
                end="\n")
        if army[thread_id].epoch_last_flush < epoch:
            army[thread_id].epoch_last_flush = epoch
            print(file=out_file,end="", flush=True)
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
    random.seed(seed) # Global random

for i in range(0, faction_num):
    for j in range(0, faction_size):
        army.append(Fighter(units, random.randint(0, KINDS - 1), i)) # Global random
        units += 1

# Clock
t = threading.Thread(target=clock, args=(units + 1, ))
threads.append(t)
t.start()

# Display thread
t = threading.Thread(target=display, args=(units, ))
threads.append(t)
t.start()

for i in range(units):
    t = threading.Thread(target=worker, args=(
        i,
        seed,
    ))
    threads.append(t)
    t.start()

# Wait for all threads to complete.
for t in threads:
    t.join()

print(f"{epoch:<4}Final global_counter: {global_counter}", file=out_file)
