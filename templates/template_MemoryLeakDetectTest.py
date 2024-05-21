import os
import pytest
from memorytools.memorymonitor import MemoryMonitor

def test_detect_memory_leaks(config):
    """
    Test to analyse memory data collected throughout the continuous integration testing and run the 
    leak detection algorithm on the collected data 
    """
    leaking_proc_name = "leaky_process" #The leaky process tested throughout the CI pipeline

    #Skip the test if memory leak detection is disabled, no data would be collected etc.
    if(config.getoption('--memoryleaks')==False):
        pytest.skip("Memory leak detection disabled")
    
    #Restor the MemoryMonitor object from test session runs
    mem_monitor = MemoryMonitor(data_file="memory_data.csv")

    #Run the leak detection algorithm on the collected data
    assert leaking_proc_name not in mem_monitor.detect_leaks()[0]

    
    
    #Do something with data files for later analysis 
    mem_monitor.export_to_csv("/dev/null/memory_data.csv")
    
    #Close the memory monitor object before moving data file
    mem_monitor.close()
    os.system("mv memory_data.csv /dev/null") 
