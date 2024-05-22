from ast import Tuple
import csv
import datetime
import os
import sys
import time
from matplotlib import pyplot as plt
import numpy as np
import pytest

from memorytools import memoryanalysis
sys.path.append("..")
import requests
from memorytools.memorymonitor import MemorySnapper, MemoryMonitor
import subprocess


ALGORITHMS = ["linefit", "LBR", "LBRCPD"]


@pytest.fixture(scope="module", name="server")
def start_server(request: type[pytest.FixtureRequest]): #Do not change api
    """Startup the test server

    Yields:
        (int, str): The pid and name of the server (pid, name)s
    """
    
    global PORT
    PORT = 8130

    #Spawn a test_server.py with Popen, yield and then kill it
    proc = subprocess.Popen(["python3", "test/test_server.py"])
    time.sleep(5) #TODO Lazy replace with a check for the server being up
    if(proc.poll() is not None):
        proc.kill()
        raise Exception("Test server failed to start")
    yield proc.pid,None #Proc name in second pos
    requests.get(f"http://127.0.0.1:{PORT}/exit")
    time.sleep(2)
    proc.kill()
    time.sleep(2)

@pytest.fixture(scope="function")
def reset_server():
    """
    Spawn a test_server.py with Popen, yield and then kill it when we are done
    
    Yields:
        int: Server pid
    """
    #
    # proc = subprocess.Popen(["python", "test_server.py"])
    requests.get(f"http://127.0.0.1:{PORT}/clrmem")
    time.sleep(1) #TODO Lazy replace with a check for the server being up
    yield
    requests.get(f"http://127.0.0.1:{PORT}/clrmem")
    time.sleep(1)

@pytest.fixture(scope="function", autouse=True)
def delete_memory_pickle():
    os.remove("memory_data_tmp.dat") if os.path.exists("memory_data_tmp.dat") else None
    yield
    os.remove("memory_data_tmp.dat") if os.path.exists("memory_data_tmp.dat") else None

def send_memory_request(server): #Do not change api
    response = requests.get(f"http://127.0.0.1:{PORT}/addmem")
    assert response.status_code==200

def send_memory_clear_request(server): #Do not change api
    response = requests.get(f"http://127.0.0.1:{PORT}/clrmem")
    assert response.status_code==200



def simulate_simple_memory_leak(server, duration=60):
    """
    Simulate a memory leak by continuously sending memory requests to a server.

    Parameters:
    server: The server to send the memory requests to.
    duration: The duration in seconds for which to simulate the memory leak, in seconds. Defaults to 60.
    """
    send_memory_clear_request(server)
    start_time = time.time()
    while time.time() - start_time < duration:
        send_memory_request(server)
        time.sleep(duration/50)  # Pause for a second between requests

def simulate_sawtooth_memory_leak(server):
    for _ in range(3): #60 seconds 
        simulate_simple_memory_leak(server,10)
        send_memory_clear_request(server)



class TestMemoryRecording():
    def test_memory_snapper_simple(self, server: (int, str)):
        # Create a memory monitor
        mem_mon = MemorySnapper()

        #Data will now increase in usage but be cleared by the exit
        for _ in range(100): #100*0.5 = 50s
            time.sleep(0.5)
            mem_mon.take_memory_snapshot()
        assert len(mem_mon[server[0]].vmss) == 100

        # Close the memory monitor
        mem_mon.close()


    def test_memory_snapper_save_and_load(self, server: (int, str)):
        assert not os.path.exists("memory_data_tmp.dat")
        # Create a memory monitor
        mem_mon = MemorySnapper()

        # Take a snapshot of the memory usage
        mem_mon.take_memory_snapshot()

        #Close the memory monitor and reopen it
        mem_mon.close()
        assert os.path.exists("memory_data_tmp.dat")

        mem_mon = MemorySnapper()

        # Take another snapshot of the memory usage
        mem_mon.take_memory_snapshot()

        # Expect 2 snapshots
        assert len(mem_mon[server[0]].vmss) == 2
        
        # Close the memory monitor
        mem_mon.close()

    # Very simple test of memory monitor
    def test_memory_monitor(self, server):
        # Create a memory monitor
        mem_mon = MemoryMonitor()
        mem_mon.start_monitoring()
        time.sleep(10)
        # Stop monitoring
        mem_mon.stop_monitoring()

        # Check that monitoring has stopped
        print(mem_mon.pids)
        assert not mem_mon.is_monitoring()
        assert len(mem_mon[server[0]].times)>5 
        assert mem_mon[server[0]].vmss is not None

    def test_import_valid_data(self):
        # Initialize the MemorySnapper object
        mem_snap = MemorySnapper()

        # Create a CSV file with valid data
        filename = "data/valid_data.csv"
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Process ID', 'Process Name', 'Time', 'Memory Usage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerow({'Process ID': 1001001001, 'Process Name': 'Process 1', 'Time': '2022-01-01 00:00:00.00001', 'Memory Usage': 100})
            writer.writerow({'Process ID': 2002002002, 'Process Name': 'Process 2', 'Time': '2022-01-01 00:01:00.00001', 'Memory Usage': 200})
            writer.writerow({'Process ID': 1001001001, 'Process Name': 'Process 1', 'Time': '2022-01-01 00:02:00.00001', 'Memory Usage': 150})

        # Import the data from the CSV file
        mem_snap.import_from_csv(filename)

        # Assert that the data was imported correctly
        assert "Process 1" in mem_snap.processes
        assert "Process 2" in mem_snap.processes
        assert len(mem_snap[1001001001].times) == 2
        assert len(mem_snap[2002002002].times) == 1
        assert mem_snap[1001001001][datetime.datetime(2022, 1, 1, 0, 0, 0)] == 100
        assert mem_snap[1001001001][datetime.datetime(2022, 1, 1, 0, 2, 0)] == 150
        assert mem_snap[2002002002][datetime.datetime(2022, 1, 1, 0, 1, 0)] == 200

        
@pytest.mark.parametrize("leak_detection_algo", 
                        [pytest.param("linefit", marks=pytest.mark.skip(
                                                    "Linefit cannot detect issues in sawtooth")),
                        "LBR",
                        pytest.param("LBRCPD", marks=pytest.mark.skip(
                                                            "LBRCPD is unfinished at the moment"))
                        ])
class TestLeakDetection():
    def test_memory_monitor_sawtooth_memory_leak(self, server, leak_detection_algo):
        # Create a memory monitor
        mem_mon_sawtooth = MemoryMonitor(time_interval=0.05)
        mem_mon_sawtooth.start_monitoring()
        # proc=None
        simulate_sawtooth_memory_leak(server)
        mem_mon_sawtooth.stop_monitoring()

        # assert test server is in mem_mon.processes
        assert server[0] in mem_mon_sawtooth.pids

        assert server[0] in mem_mon_sawtooth.detect_leaks(algo=leak_detection_algo)[1]
        
        # Close the memory monitor
        mem_mon_sawtooth.close()


    def test_memory_monitor_growing_memory_leak(self, server, leak_detection_algo):

        mem_mon = MemoryMonitor(time_interval=0.05)
        mem_mon.start_monitoring()

        simulate_simple_memory_leak(server, 10)

        mem_mon.stop_monitoring()
        
        # assert test server is in mem_mon.processes
        assert server[0] in mem_mon.pids

        assert server[0] in mem_mon.detect_leaks(algo=leak_detection_algo)[1]
        
        # Close the memory monitor
        mem_mon.close()

    def test_memory_monitor_gaps(self, server, leak_detection_algo):
    
        mem_mon_gaps = MemoryMonitor(time_interval=0.05)
        mem_mon_gaps.start_monitoring()
        simulate_sawtooth_memory_leak(server)

        # Create a gap in our memory recording
        mem_mon_gaps.stop_monitoring()

        time.sleep(10)

        mem_mon_gaps.start_monitoring()

        #Back to memory monitoring!

        simulate_simple_memory_leak(server,10)
        mem_mon_gaps.stop_monitoring()

        # assert test server is in mem_mon.processes
        assert server[0] in mem_mon_gaps.pids

        assert server[0] in mem_mon_gaps.detect_leaks(algo=leak_detection_algo)[1]
        
        # Close the memory monitor
        mem_mon_gaps.close()

    def test_memory_monitor_gaps_no_leak(self, server, leak_detection_algo):
    
        mem_mon_gaps = MemoryMonitor(time_interval=0.05)
        mem_mon_gaps.start_monitoring()
        time.sleep(10)

        # Create a gap in our memory recording
        mem_mon_gaps.stop_monitoring()

        time.sleep(10)

        mem_mon_gaps.start_monitoring()

        #Back to memory monitoring!
        time.sleep(10)

        mem_mon_gaps.stop_monitoring()

        # assert test server is in mem_mon.processes
        assert server[0] in mem_mon_gaps.pids

        assert server[0] not in mem_mon_gaps.detect_leaks(algo=leak_detection_algo)[1]
        
        # Close the memory monitor
        mem_mon_gaps.close()

