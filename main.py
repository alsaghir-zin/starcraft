import threading
import time
import random
import curses
import sys
import os

# Global variable shared by all threads.
global_counter = 0
map_size = 6
round = 10
map = [{} for i in range(0, (map_size * map_size) - 1)]
out_file = open('battle_log.txt', 'w')
units = 3
PACMAN = 'P'
GHOST = 'G'
WALL = '#'
DOT = '.'
EMPTY = ' '


def random_pos():
    return (random.randint(0, (map_size * map_size) - 1))


def initialize_grid():
    grid = [[DOT for _ in range(0,map_size)] for _ in range(0,map_size)]
    # Add walls
    #for i in range(map_size-1):
    #    grid[i][0] = WALL
    #    grid[i][map_size - 1] = WALL
    #for j in range(map_size-1):
    #    grid[0][j] = WALL
    #    grid[map_size - 1][j] = WALL
    # Place Pac-Man and Ghost
    grid[1][1] = PACMAN
    grid[map_size - 2][map_size - 2] = GHOST
    return grid


# Draw the grid on the screen
def draw_grid(stdscr, grid):
    stdscr.clear()
    for row in grid:
        stdscr.addstr(''.join(row) + '\n')
    stdscr.refresh()


def print_map():
    i = 0
    j = 0
    for i in range(0, map_size - 1):
        for j in range(0, map_size - 1):
            print("{:<4}".format(" ".join(str(x) for x in map[i + j].keys())),
                  end="",
                  file=out_file)
            print("|", end="", file=out_file)
        print()
        for j in range(0, map_size):
            print("----", end="", file=out_file)
        print(file=out_file)


# A lock to ensure thread-safe updates to the global variable.
counter_lock = threading.Lock()


def display(thread_id):
    i = 0
    for i in range(round):
        with counter_lock:
            draw_grid(stdscr, grid)
            print_map()
            print(flush=True, file=out_file)
        time.sleep(1)


def worker(thread_id):
    # Local variable specific to each thread.
    local_counter = 0
    location = random_pos()
    i = 0
    for i in range(round):
        # Update the local counter.
        local_counter += 1
        prev_location = location
        location = random_pos()
        # Safely update the global counter using the lock.
        with counter_lock:
            global global_counter
            global_counter += 1
            print(f" Thread {thread_id} , {prev_location}->{location}",
                  file=out_file)
            #if thread_id in map[prev_location]:
            try:
                del map[prev_location][thread_id]
            except:
                print(
                    f"Cannot delete Thread {thread_id} , {prev_location}->{location}",
                    file=out_file)
            try:
                map[location][thread_id] = thread_id
                print(f"In {location} we got {map[location]}", file=out_file)
            except:
                print(
                    f"Cannot move Thread {thread_id} , {prev_location}->{location}",
                    file=out_file)
            print(flush=True, file=out_file)
        # Print both the local and global counters.
        #print(f"Thread {thread_id} - local_counter: {local_counter}, global_counter: {global_counter}")
        time.sleep(1)  # Simulate work.


# Create a list to hold our thread objects.
threads = []
grid = initialize_grid()
stdscr = curses.initscr()

if __name__ == "__main__":
    draw_grid(stdscr, grid)

    # Create and start 3 threads.
    t = threading.Thread(target=display, args=(units + 1, ))
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

    grid = initialize_grid()
    stdscr = curses.initscr()
    draw_grid(stdscr, grid)
