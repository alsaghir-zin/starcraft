import threading
import time

# Global variable shared by all threads.
global_counter = 0
# A lock to ensure thread-safe updates to the global variable.
counter_lock = threading.Lock()

def worker(thread_id):
    # Local variable specific to each thread.
    local_counter = 0
    for i in range(5):
        # Update the local counter.
        local_counter += 1

        # Safely update the global counter using the lock.
        with counter_lock:
            global global_counter
            global_counter += 1

        # Print both the local and global counters.
        print(f"Thread {thread_id} - local_counter: {local_counter}, global_counter: {global_counter}")
        time.sleep(1)  # Simulate work.

# Create a list to hold our thread objects.
threads = []

# Create and start 3 threads.
for i in range(3):
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()

# Wait for all threads to complete.
for t in threads:
    t.join()

print("Final global_counter:", global_counter)
