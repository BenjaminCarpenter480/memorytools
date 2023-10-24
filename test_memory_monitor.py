import os
import subprocess
import time
from matplotlib.dates import date2num
import numpy as np
import pytest
import requests
from memorymonitor import MemorySnapper, MemoryMonitor
PORT = 8129

@pytest.fixture(scope="module", name="server")
def start_server(request):
    """Startup the test server

    Yields:
        int: Server pid
    """
    #Spawn a test_server.py with Popen, yield and then kill it
    proc = subprocess.Popen(["python3", "test_server.py"])
    time.sleep(1) #TODO Lazy replace with a check for the server being up
    if(proc.poll() is not None):
        raise Exception("Server failed to start")
    yield proc.pid #Proc name in second pos
    requests.get(f"http://127.0.0.1:{PORT}/EXIT")
    time.sleep(2)

@pytest.fixture(scope="function")
def reset_server():
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

def test_memory_snapper_simple_memory_leak(server: int):
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()
    for _ in range(0,50):
        # Allocate some memory
        send_memory_request()
        time.sleep(0.5)

        # Take another snapshot of the memory usage
        mem_mon.take_memory_snapshot()

    # assert test server is in mem_mon.processes
    assert len(mem_mon[server].vmss) == 51
    mem_mon.plot_data(server)
    
    assert mem_mon[server].vmss[-1] > mem_mon[server].vmss[0]
    m,c = np.polyfit(date2num(mem_mon[server].times), mem_mon[server].vmss, 1)
    print(m)
    print((mem_mon[server].vmss))
    assert m>0.1 #We expect the memory to be dramatically increasing over time

    # Close the memory monitor
    mem_mon.close()

def test_memory_snapper_simple_no_leak(server: int):
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Data will now increase in usage but be cleared by the exit
    for _ in range(5):
        # Allocate some memory
        send_memory_request()
        time.sleep(0.1)

    send_memory_clear_request()
    time.sleep(1)
    mem_mon.take_memory_snapshot()
    assert len(mem_mon[server].vmss) == 2

    
    # mem_mon.detect_abnormalites() #We expect this to not raise any issues

    # Close the memory monitor
    mem_mon.close()

def test_memory_snapper_save_and_load_leak(server: int):
    assert not os.path.exists("memory_data_tmp.dat")
    # Create a memory monitor
    mem_mon = MemorySnapper()
    
    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    for _ in range(0,50):
        # Allocate some memory
        send_memory_request()
        time.sleep(1)
        # Take another snapshot of the memory usage
        mem_mon.take_memory_snapshot()


    #Close the memory monitor and reopen it
    mem_mon.close()
    assert os.path.exists("memory_data_tmp.dat")
    mem_mon = MemorySnapper()

    # Take another snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Expect 3 snapshots
    assert len(mem_mon[server].vmss) == 52

    mem_mon.plot_data(server)

    m,c = np.polyfit(date2num(mem_mon[server].times), mem_mon[server].vmss, 1)
    assert m>0.1 #We expect the memory to be dramatically increasing over time
    print(m)
    print((mem_mon[server].vmss))
    # Close the memory monitor
    mem_mon.close()

def test_memory_snapper_save_and_load_no_leak(server: int):
    assert not os.path.exists("memory_data_tmp.dat")
    # Create a memory monitor
    mem_mon = MemorySnapper()

    # Take a snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    #Close the memory monitor and reopen it
    mem_mon.close()
    assert os.path.exists("memory_data_tmp.dat")

    # Allocate some memory
    send_memory_request()

    # Allocate some more memory
    send_memory_request()
    mem_mon = MemorySnapper()

    send_memory_clear_request()

    # Take another snapshot of the memory usage
    mem_mon.take_memory_snapshot()

    # Expect 2 snapshots
    assert len(mem_mon[server].vmss) == 2

    # Close the memory monitor
    mem_mon.close()

def test_memory_monitor(server):
    # Create a memory monitor
    mem_mon = MemoryMonitor()
    
    time.sleep(5)
    # Stop monitoring
    mem_mon.stop_monitoring()

    # Check that monitoring has stopped
    assert not mem_mon.is_monitoring()
    assert len(mem_mon[server].times)>4 
    assert mem_mon[server].vmss is not None


def send_memory_request():
    response = requests.get(f"http://127.0.0.1:{PORT}/addmem")
    assert response.status_code==200


def send_memory_clear_request():
    response = requests.get(f"http://127.0.0.1:{PORT}/clrmem")
    assert response.status_code==200