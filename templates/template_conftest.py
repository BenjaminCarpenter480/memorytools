import pytest
from memorytools.memorymonitor import MemoryMonitor

@pytest.fixture(scope='session')
def mem_monitor(config):

    if(config.getoption('--memoryleaks')):
        mem_monitor = MemoryMonitor(data_file="memory_data.csv")
        mem_monitor.start_monitoring()

    yield mem_monitor

    if(config.getoption('--memoryleaks')):
        mem_monitor.stop_monitoring()
        mem_monitor.close()



def pytest_addoption(parser):
    parser.addoption("--memoryleaks", action="store_true", default=True, help="Enable memory leak detection")
