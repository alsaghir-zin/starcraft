import threading
import time
import random
# Global variable shared by all threads.
global_counter = 0
map_size=5
round=10
map = [{} for i in range(0,map_size*map_size-1)]

def random_pos():
    return (random.randint(0,map_size*map_size-1))

def print_map():
    i=0
    j=0
    for i in range(0,map_size):
        for j in range(0,map_size):
            print(map[i+j],end="")
        print()    
# A lock to ensure thread-safe updates to the global variable.
counter_lock = threading.Lock()

def display(thread_id):
    for i in range(round):  
        with counter_lock:
         print_map()
         print(flush=True)
        time.sleep(1)       
def worker(thread_id):
    # Local variable specific to each thread.
    local_counter = 0
    location=random_pos()
    
    for i in range(round):
        # Update the local counter.
        local_counter += 1
        prev_location=location
        location=random_pos()
        # Safely update the global counter using the lock.
        with counter_lock:
            global global_counter
            global_counter += 1
            print(f" Thread {thread_id} , {prev_location}->{location}")
            #if thread_id in map[prev_location]:
            try:
             del map[prev_location][thread_id]
            except:
             pass   
            map[location][thread_id]=thread_id
            print(flush=True)
        # Print both the local and global counters.
        #print(f"Thread {thread_id} - local_counter: {local_counter}, global_counter: {global_counter}")
        time.sleep(1)  # Simulate work.

# Create a list to hold our thread objects.
threads = []

# Create and start 3 threads.
t = threading.Thread(target=display,args=(3+1,))
threads.append(t)
t.start()

for i in range(3):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

# Wait for all threads to complete.
for t in threads:
    t.join()

print("Final global_counter:", global_counter)
