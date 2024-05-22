<h1>  <img src="https://github.com/BenjaminCarpenter480/memorytools/assets/6034496/8f94fa35-8e5a-492a-a61d-5c0a981c6cfc" alt="logo" style="width:4rem; height:auto;" /> MemoryTools - A low impact memory alert system  </h1>




This work presents a novel, low-impact, and language-independent memory alert system designed to detect potential memory leaks in software systems. Using machine learning techniques, the system integrates seamlessly with existing unit testing and continuous integration strategies at the European Southern Observatory (ESO) -notably Pytest- to provide early detection of memory leaks.
This proactive approach allows developers to address issues promptly and before they become an issue in production, enhancing the reliability and efficiency of their software.
The system has been tested using a memory leak simulator and real-world data, demonstrating its effectiveness in a practical setting.
This research contributes to ongoing efforts to improve software quality and reliability, particularly in the context of the ESO’s Very Large Telescope (VLT) software.

# System Design
The system, implemented in Python, records data by spawning a background thread, which periodically takes snapshots of key system metrics such as virtual memory usage, timestamp, process name and process ID via the psutil library. The collected data is stored in a dictionary containing data store objects representing information about a process.
The analysis is initiated post-data collection. Datasets are split up if they contain significant temporal gaps. Such gaps may be created due to the running characteristics of the system under test. For example, if the process under test is spawned in a test, detached and then reattached in a later test. Data from these objects should be grouped into one of the custom memory store objects, but for analysis, we would get fake artefacts if the later resampling is applied across too large a gap. After splitting the data across these significant gaps for each process, we then apply a Numpy linear interpolation function np.interp to smooth the data.
We adapt the Linear Backward Regression (LBR) method presented in the paper Memory leak detection algorithms in the cloud-based infrastructure
1. Select a window of observations from the end of the time series. The window has a minimum defined size to filter out data that would be too small to be representative.
2. Attempt to fit a line to this data collecting the gradient, intercepts and the measure of fit R2
3. If the model is a good enough fit, i.e. R2 is above a threshold, then we should calculate the time for the model to reach some threshold memory (e.g. 100% utilisation of system resources).
4. If that time is within a critical time (we use 1 hour for unit-like testing), then the data is anomalous and should be reported as an anomaly to the user with this PID.
5. Otherwise, we increase the window size by adding the next available data point up to the maximum window size/all observations.

Our implementation of this algorithm differs from that described  in _Memory leak detection algorithms in the cloud based infastructure, in that we add the process name/pid and then continue looking through other processes. The goal of this tool is less about where the leak is occurring and more about alerting the user of a potential leak to be investigated. In our use case other tools are subsequently used to investigate suspicious code. 


Example usage of the memory monitor tool 
```
#Setup memory monitor object
>>> from memorytools import MemoryMonitor
>>> mem_monitor = MemoryMonitor()

#Start monitoring memory usage
>>> mem_monitor.start_monitoring()

<Do some stuff while monitoring memory usage>

#Stop monitoring memory usage
>>> mem_monitor.stop_monitoring()
#Run the leak detection algorithm on the collected data
>>> mem_monitor.detect_leaks() 
```
