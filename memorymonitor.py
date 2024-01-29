import csv
import logging
import pickle
import time
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import datetime
import numpy as np
import psutil as ps
import threading
from typing import List, Tuple

import scipy

try:
    import ccs
    CCSENV=True
except ImportError:
    CCSENV=False
    

class MemorySnapper:
    """Environment process memory information recorder
    
    Example usage::
        >>> mem_snap = MemorySnapper() #Create a memory snapper object
        >>> mem_snap.take_memory_snapshot() #Take a snapshot of the current memory usage
        >>> <Do some stuff that should leave the system with the same memory as before>
        >>> mem_snap.take_memory_snapshot() #Take another snapshot
        >>> assert mem_snap.detect_leaks() == set() #No memory leaks detected
    
    """

    class ProcMemData:
        """Class to store memory data for a single process"""

        def __init__(self, pid):
            """
            Base monitoring used to collect data that can be used to calculate the stdev of the memory usage for the entire environment
            """
            self.pid = pid
            self.name = ps.Process(pid).name()
            self._vmss = {}

        def __getitem__(self, time):
            return self._vmss[time]

        def __setitem__(self, time, full_memory):
            self._vmss[time] = full_memory.vms

        @property
        def vmss(self) ->List[int]:
            """Returns a List[int] of virtual memory sizes for a process over time"""
            return list(self._vmss.values())

        @property
        def times(self)->List[datetime.datetime]:
            """Returns a List[datetime.datetime] of times at which a memory snapshot was taken"""
            return list(self._vmss.keys())

    def __init__(self, existing_data_file=None, base_monitoring=False):
        self._base_monitoring = base_monitoring
        self.__proc_names = set()
        self.totals = {}
        if existing_data_file == None:
            self.__data_file = "memory_data_tmp.dat"
        else:
            self.__data_file = existing_data_file
        logging.debug("MEMORY DATA FILE: " + self.__data_file)
        # Check if file exists, if it does load it as a pickle file into a dictionary
        # If it doesn't, create an empty dictionary
        try:
            with open(self.__data_file, "rb") as f:
                loaded_data = pickle.load(f)
                self.__dict__.update(loaded_data)
                logging.debug("LOADING MEMORY DATA FROM FILE")

        except FileNotFoundError as err:
            self.__data = {}
            logging.debug("NO MEMORY DATA FILE FOUND")

    def proc_by_name(self, name):
        """Return a Dict[datetime.datetime, int] of process data by the name of that process"""
        for pid in self.pids:
            if self.__data[pid].name == name:
                return self.__data[pid]

    def __getitem__(self, pid):
        return self.__data[pid]

    def __enter__(self):
        return self

    @property
    def processes(self)->List[str]:
        """List of processes names for which memory data has been collected"""
        return self.__proc_names

    @property
    def pids(self)->List[int]:
        """List of processes ids for which memory data has been collected"""
        return self.__data.keys()

    def close(self):
        """Close the memory monitoring object, saving the collected data as a pickle"""
        with open(self.__data_file, "wb") as fp:
            pickle.dump(self.__dict__, fp)

    def take_memory_snapshot(self):
        """Create an entry in the data structure for memory processes in the environment at the
        current time.
        """

        # SETUP TIME
        if CCSENV:
            total = 0
            env_procs = ccs.GetEnvProcs(
                full_report=True
            )  # Whilst process_iter might thread safe this ccs.GetEnvProcs is not
            del env_procs[ccs.procName]
            env_pids = {v["pid"]: k for k, v in env_procs.items()}

        # MEASURE TIME
        current_time = datetime.datetime.now()
        total_mem = 0 # Total memory usage for all processes
        for p in ps.process_iter():
            if CCSENV:
                #CCS Make CCS related changes
                #Only interested in the current environment
                if p.pid not in env_pids:
                    continue
                p_name = env_pids[p.pid]  # Make use of ccs names
            else:
                p_name = p.name()
            p_pid = p.pid
            with p.oneshot():
                total_mem = total_mem + p.memory_info().vms
            #'New' procs will be missing from stored info
            if p_pid not in self.__data.keys():
                self.__data[p_pid] = self.ProcMemData(p_pid)
                self.__proc_names.add(p_name)
            with p.oneshot():
            # Update memory usage
                self[p_pid][current_time] = p.memory_info()
            # total_mem = total_mem + self[p_pid][current_time]
        logging.info(f"Total memory usage: {total_mem}")
        self.totals[current_time]=total_mem

    def detect_leaks(self,algo="linefit")->Tuple[List[str],List[int]]:
        """ Detect memory leaks using a given algorithm

        Args:
            algo: Algorithm to use to detect memory leaks

        Returns:
            A set of names and pids of processes that are abnormally using memory
        """
        if algo=="linefit":
            abnorm_names, abnorm_pids =  self.detect_leaks_line_fit()
        elif algo=="LBR":
            abnorm_names, abnorm_pids =  self.detect_leaks_linear_backward_regression()
        else:
            raise NotImplementedError()
        abnorm_names = list(abnorm_names)
        abnorm_pids = list(abnorm_pids)

        for proc_index in range(len(abnorm_names)):
            logging.warning(f"Abnormal memory usage detected in process: {abnorm_names[proc_index]}"
                            f"with pid {abnorm_pids[proc_index]}")
            print(f"Abnormal memory usage detected in process: {abnorm_names[proc_index]} with pid "
                  f"{abnorm_pids[proc_index]}")

        return (abnorm_names, abnorm_pids)

    def detect_leaks_line_fit(self)->Tuple[List[str],List[int]]:
        """
        Fit a line to the avalible memory data, assuming a 'nice' fit and if it has a particuarly 
        large gradient then suggest it as a memory leaking process.

        Returns:
            A set of names and pids of processes that are abnormally using memory
        """
        grads = []
        abnorm_names = set()
        abnorm_pids = set()
        for proc in self.pids:
            m,c  = np.polyfit(date2num(self[proc].times), self[proc].vmss, 1) #Fit a straight line to the data
            if m>0.1:
                abnorm_names.add(self.__data[proc].name)
                abnorm_pids.add(proc)
            grads.append(m) 
        return (abnorm_names, abnorm_pids)

    def detect_leaks_linear_backward_regression(self)->Tuple[List[str],List[int]]:
        """Detect memory leaks using the linear backward regression algorithm
        Not yet implemented sucessfully
        """
        anomalus_names = set()
        anomalus_pids = set()
        WINDOW_MIN = 4 # Add in some form of smoothing
        R_sqr_min = 0.8 #From paper
        CRITICAL_TIME_MAX = 60*60*5 # One hour
        CRITICAL_MEMORY_USAGE = ps.virtual_memory().total
        
        for pid in self.pids:
            # if self[pid].name != "python3":
            #     continue #TODO bcarpent Need to remove later
            input_data = self[pid]
            anomalus_ts = set()#type :set(datetimes) #Anomalus data points
            
            i = WINDOW_MIN
            WINDOW_MAX = len(input_data.times)
            n = len(input_data.times)
            while(i<= n and i<=WINDOW_MAX):
                ts = date2num(input_data.times[n-i:n])
                ys = input_data.vmss[n-i:n]
                # plt.scatter(ts,ys, label=i)
                m,c,r_pcc,*_ =scipy.stats.linregress(ts,ys) #Gives us Pearson correlation coeff unlike np.polyfit
                r2 = r_pcc**2 #Rsquare is the square of the pearson correlation coefficient
                if m == 0:
                    t_crit = np.Infinity # No memory leak, gradient flat
                else:
                    t_crit = (CRITICAL_MEMORY_USAGE - c)/m

                if (r2>=R_sqr_min):
                    print("-------------------------------------------")
                    print(f"Data with good fit {self.__data[pid].name} pid {pid}")
                    print(f"m: {m}, c: {c}, r2: {r2}")
                    print(f"t_crit: {t_crit}")
                    print("-------------------------------------------")
                    if(t_crit > CRITICAL_TIME_MAX):
                        #Add ts to the erronus stamps (unpack)
                        # anomalus_ts = anomalus_ts | set(ts[n-i:i]) #Add new ts to set of anomalus ones
                        anomalus_names.add(self.__data[pid].name)
                        anomalus_pids.add(pid)
                        

                i = i+1
        # plt.legend()
        # plt.show()
        return (anomalus_names, anomalus_pids)

    def _plot_data(self, proc_pid=None):
        """
        Helper function to plot the memory usage of a process over time or all processes if proc_pid is None
        
        Args:
            proc_pid: Process id of process to plot default is None which plots all processes
        """
        procs_to_plot = self.pids if proc_pid is None else [proc_pid]

        for proc in procs_to_plot:
            plt.scatter(self[proc].times, np.array(self[proc].vmss) / 1e6, label=(self.__data[proc].name,proc))

        plt.legend()
        plt.xlabel("Time stamp")
        plt.ylabel("Memory usage (MB)")
        plt.tight_layout()
        plt.xticks(rotation=45)

    def plot_data_to_file(self, proc_pid=None, filename=None):
        """
        Plot the memory usage of a process over time or all processes if proc_pid is None and save to a file
        
        Args:
            proc_pid: Process id of process to plot default is None which plots all processes
            filename: If provided, the plot will be saved to this file
        """
        self._plot_data(proc_pid)
        
        if filename:
            plt.savefig(filename)
        plt.close()

    def plot_data_to_screen(self, proc_pid=None, block=False):
        """
        Plot the memory usage of a process over time or all processes if proc_pid is None and show on screen
        
        Args:
            proc_pid: Process id of process to plot default is None which plots all processes
            block: If True, plt.show() will be blocking
        """
        self._plot_data(proc_pid)
        
        plt.show(block=block)

    def export_to_csv(self, filename):
        """
        Export the memory usage data to a CSV file.

        Args:
            filename: The name of the file where the data will be saved
        """
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['Process ID', 'Process Name', 'Time', 'Memory Usage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for proc in self.pids:
                for time, memory in zip(self[proc].times, self[proc].vmss):
                    writer.writerow({
                        'Process ID': proc, 
                        'Process Name': self.__data[proc].name,
                        'Time': time, 
                        'Memory Usage': memory
                    })

class MemoryMonitor(MemorySnapper):
    """Class for continuous monitoring of processes memory usage """
    def __init__(self, time_interval=1, base_monitoring=True):
        super().__init__(existing_data_file=None, base_monitoring=base_monitoring)

        self.__time_interval = time_interval
        self.__monitoring=True
        self.__monitor_thread = threading.Thread(target=self.__monitor_loop)
        self.__monitor_thread.start()


    def __monitor_loop(self):
        while self.__monitoring:
            self.take_memory_snapshot()
            time.sleep(self.__time_interval)

    def stop_monitoring(self):
        self.__monitoring = False
        self.__monitor_thread.join()

    def is_monitoring(self):
        return self.__monitoring
