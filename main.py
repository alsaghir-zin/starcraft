import threading
import time


def worker(thread_id):
    """A simple worker function that prints messages."""
    for i in range(5):
        print(f"Thread {thread_id} is really working, iteration {i}")
        time.sleep(1)  # Simulate some work with a 1-second delay


# Create a list to hold our thread objects
threads = []

# Create and start 3 threads
for i in range(3):
    t = threading.Thread(target=worker, args=(i, ))
    threads.append(t)
    t.start()

# Wait for all threads to complete
for t in threads:
    t.join()

print("All threads finished.")
