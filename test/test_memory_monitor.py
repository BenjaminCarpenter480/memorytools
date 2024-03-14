import os
import sys
import time
import tempfile
from matplotlib import pyplot as plt
import numpy as np
import pytest
import csv

sys.path.append("..")
#Do Not Modify IMPORTS HERE #
import requests
from memorytools.memorymonitor import MemorySnapper, MemoryMonitor
import subprocess
#Do Not Modify IMPORTS HERE #

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
    time.sleep(1) #TODO Lazy replace with a check for the server being up
    if(proc.poll() is not None):
        proc.kill()
        raise Exception("Server failed to start")
    yield proc.pid,None #Proc name in second pos
    requests.get(f"http://127.0.0.1:{PORT}/exit")
    time.sleep(2)
    proc.kill()
    time.sleep(2)

@pytest.fixture(scope="function")
def reset_server(): #Do not change api
    """Startup the test server

    Yields:
        int: Server pid
    """
    #Spawn a test_server.py with Popen, yield and then kill it
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

########## SHOULD BE SAME BELOW LINE ##########

def simulate_simple_memory_leak(server):
    for _ in range(1000):
        time.sleep(np.random.randint(0,500))
        send_memory_request(server)

def simulate_sawtooth_memory_leak(server):
    for _ in range(50):
        simulate_simple_memory_leak(server)
        send_memory_clear_request(server)

# TESTING OF MEMORY SNAPPER LEAK DETECTION ALGORITHMS FOR SIMPLE LEAK# 

@pytest.mark.parametrize("leak_detection_algo", ALGORITHMS)
def test_memory_snapper_simple_memory_leak(server: (int, str), leak_detection_algo):
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()
    for _ in range(20):
        # Allocate some memory
        send_memory_request(server)
        time.sleep(0.5)

        # Take another snapshot of the memory usage
        mem_mon.take_memory_snapshot()

    # assert test server is in mem_mon.processes
    assert server[0] in mem_mon.pids

    assert server[0] in mem_mon.detect_leaks(algo=leak_detection_algo)[1]
    
    # Close the memory monitor
    mem_mon.close()

@pytest.mark.parametrize("leak_detection_algo", ALGORITHMS)
def test_memory_snapper_simple_no_leak(server: (int, str),  leak_detection_algo):
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Data will now increase in usage but be cleared by the exit
    for _ in range(20):
        # Allocate some memory
        send_memory_request(server)
        time.sleep(0.5)
    send_memory_clear_request(server)
    time.sleep(1)
    mem_mon.take_memory_snapshot()
    assert len(mem_mon[server[0]].vmss) == 2

    assert server[0] not in mem_mon.detect_leaks(algo=leak_detection_algo)[1]
    # Close the memory monitor
    mem_mon.close()

# TESTING OF MEMORY SNAPPER FOR SAWTOOTH LEAKS #

@pytest.mark.parametrize("leak_detection_algo", ALGORITHMS)
def test_memory_snapper_sawtooth_memory_leak(server: (int, str), leak_detection_algo):
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()
    for _ in range(200):
        # Allocate some memory
        if (np.random.random())<0.95:
            send_memory_request(server)
        else:
            send_memory_clear_request(server)
        time.sleep(0.5)

        # Take another snapshot of the memory usage
        mem_mon.take_memory_snapshot()

    # assert test server is in mem_mon.processes
    assert server[0] in mem_mon.pids

    # plt.scatter(mem_mon[server[0]].times, mem_mon[server[0]].vmss)
    # plt.show()

    assert server[0] in mem_mon.detect_leaks(algo=leak_detection_algo)[1]
    
    # Close the memory monitor
    mem_mon.close()

# TESTING OF MEMORY SNAPPER WITH SAVE AND LOAD

def test_memory_snapper_save_and_load_leak(server: (int,str)):
    assert not os.path.exists("memory_data_tmp.dat")
    # Create a memory monitor
    mem_mon = MemorySnapper()
    
    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    # Allocate some memory
    send_memory_request(server)

    # Take another snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Close the memory monitor and reopen it
    mem_mon.close()
    assert os.path.exists("memory_data_tmp.dat")
    mem_mon = MemorySnapper()

    # Take another snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Expect 3 snapshots
    assert len(mem_mon[server[0]].vmss) == 3

    leaks = mem_mon.detect_leaks()
    print(leaks)
    assert server[0] in leaks[1]
    # Close the memory monitor
    mem_mon.close()

def test_memory_snapper_save_and_load_no_leak(server: (int, str)):
    assert not os.path.exists("memory_data_tmp.dat")
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Close the memory monitor and reopen it
    mem_mon.close()
    assert os.path.exists("memory_data_tmp.dat")

    # Allocate some memory
    send_memory_request(server)

    # Allocate some more memory
    send_memory_request(server)

    mem_mon = MemorySnapper()

    send_memory_clear_request(server)

    # Take another snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    # Expect 2 snapshots
    assert len(mem_mon[server[0]].vmss) == 2

    assert server[0] not in mem_mon.detect_leaks()[1]
    # Close the memory monitor
    mem_mon.close()

# Very simple test of memory monitor
def test_memory_monitor(server):
    # Create a memory monitor
    mem_mon = MemoryMonitor()
    
    time.sleep(5)
    # Stop monitoring
    mem_mon.stop_monitoring()

    # Check that monitoring has stopped
    assert not mem_mon.is_monitoring()
    assert len(mem_mon[server[0]].times)>4 
    assert mem_mon[server[0]].vmss is not None

def test_export_to_csv():
    # Create a temporary file for the test
    temp_file = tempfile.NamedTemporaryFile(delete=False)

    # Initialize MemorySnapper and add some dummy data
    memory_snapper = MemorySnapper()
    memory_snapper.take_memory_snapshot()  # Assuming this method populates data

    # Export data to csv
    memory_snapper.export_to_csv(temp_file.name)

    # Read the csv file and check if data is written correctly
    with open(temp_file.name, 'r', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = ['Process ID', 'Process Name', 'Time', 'Memory Usage']
        assert reader.fieldnames == fieldnames

        for row in reader:
            assert 'Process ID' in row
            assert 'Process Name' in row
            assert 'Time' in row
            assert 'Memory Usage' in row

    # Delete the temporary file
    os.unlink(temp_file.name)

def test_import_from_csv():
    # Create a temporary file for the test
    temp_file = tempfile.NamedTemporaryFile(delete=False)

    # Write some dummy data to the file
    fieldnames = ['Process ID', 'Process Name', 'Time', 'Memory Usage']
    data = [{'Process ID': '1234', 'Process Name': 'test', 'Time': '2022-01-01 00:00:00', 'Memory Usage': '100'}]

    with open(temp_file.name, 'w', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    # Initialize MemorySnapper and import data from csv
    memory_snapper = MemorySnapper()
    memory_snapper.import_from_csv(temp_file.name)

    # Check if data is imported correctly
    imported_data = memory_snapper
    assert len(imported_data.pids) == 1
    assert imported_data[0]['Process ID'] == '1234'
    assert imported_data[0]['Process Name'] == 'test'
    assert imported_data[0]['Time'] == '2022-01-01 00:00:00'
    assert imported_data[0]['Memory Usage'] == '100'

    # Delete the temporary file
    os.unlink(temp_file.name)