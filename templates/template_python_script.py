#Setup memory monitor object
from memorytools.memorymonitor import MemoryMonitor
mem_monitor = MemoryMonitor()

#Start monitoring memory usage
mem_monitor.start_monitoring()
 
#Stop monitoring memory usage
mem_monitor.stop_monitoring()

#Run the leak detection algorithm on the collected data
print(mem_monitor.detect_leaks())
