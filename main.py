import threading
import time
import random
import curses
import sys
import os

warrior_spec = [{
    'name': "Melee",
    'health': 120,
    'min': 20,
    'max': 30,
    'range': 0
}, {
    'name': "Ranged",
    'health': 80,
    'min': 10,
    'max': 20,
    'range': 1
}]

faction_name = [
    "Uni staff", "The Goblins", "The Orcs", "The Trolls", "The Giants",
    "The Dragons", "The Golems", "The Gnomes"
]

# Global variable shared by all threads.
out_file_name = "battle_log.txt"
faction_num = 2  # 2 -> 8
faction_size = 5  # Numbers of warriors in each faction
MAP_SIZE = 6  # 5 -> 100
KINDS = 2
global_counter = 0

round = 10

map = [[] for i in range(0, (MAP_SIZE * MAP_SIZE))]
out_file = open(out_file_name, 'w')


class Fighter:

    def __init__(self, id, kind, faction):
        self.id = id
        self.faction = faction
        self.kind = kind
        self.name = warrior_spec[kind]["name"]
        self.faction_name = faction_name[faction]
        self.health = warrior_spec[kind]["health"]
        self.min = warrior_spec[kind]["min"]
        self.max = warrior_spec[kind]["max"]
        self.max = warrior_spec[kind]["range"]
        self.alive = True
        self.rounds = 0
        self.location = 0

    def moveto(self, location):
        self.location = location
        self.rounds += 1


def random_pos():
    return (random.randint(0, (MAP_SIZE * MAP_SIZE) - 1))


def print_map():
    i = 0
    j = 0
    for i in range(0, MAP_SIZE):
        for j in range(0, MAP_SIZE):
            print("{:<4}".format(",".join(str(x) for x in map[i*MAP_SIZE + j])),
                  end="",
                  file=out_file)
            print("|", end="", file=out_file)
        print(end="\n", file=out_file)
        for j in range(0, MAP_SIZE+1):
            print("----", end="", file=out_file)
        print(end="\n",file=out_file)


# A lock to ensure thread-safe updates to the global variable.
counter_lock = threading.Lock()


def display(thread_id):
    i = 0
    for i in range(round*3):
        with counter_lock:
            print_map()
            print(flush=True, file=out_file)
        time.sleep(0.3)


def worker(thread_id):
    # Local variable specific to each thread.
    local_counter = 0
    
    i = 0
    for i in range(round):
        # Update the local counter.
        local_counter += 1
        location = random_pos()
        with counter_lock:
            global map
            global army
            
            prev_location = army[thread_id].location
            army[thread_id].location = location
            # Safely update the global counter using the lock.
            global global_counter
            global_counter += 1
            print(f" Thread {thread_id} , {prev_location}->{location}",
                  file=out_file)
            #if thread_id in map[prev_location]:
            try:
                map[prev_location].remove(thread_id)
            except Exception as e:
                print(e,prev_location)
                print(
                    f"Cannot delete Thread {thread_id} , {prev_location}->{location}",
                    file=out_file)
            try:
                map[location].append(thread_id)
                print(f"In {location} we got {map[location]}", file=out_file)
            except Exception as e:
                print(e,location)
                print(
                    f"Cannot move Thread {thread_id} , {prev_location}->{location}",
                    file=out_file)
            print(flush=True, file=out_file)
        # Print both the local and global counters.
        #print(f"Thread {thread_id} - local_counter: {local_counter}, global_counter: {global_counter}")
        time.sleep(1)  # Simulate work.


# Create a list to hold our thread objects.
threads = []
units = 0
army = []

for i in range(0,faction_num):
    for j in range(0,faction_size):
        army.append(Fighter(units, random.randint(0, KINDS - 1), i))
        print(units, i, j)
        units += 1

# Display thread
t = threading.Thread(target=display, args=(units, ))
threads.append(t)
t.start()

for i in range(units):
    t = threading.Thread(target=worker, args=(i, ))
    threads.append(t)
    t.start()

# Wait for all threads to complete.
for t in threads:
    t.join()

print("Final global_counter:", global_counter, file=out_file)
