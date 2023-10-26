import logging
import pickle
import time
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import datetime
import numpy as np
import psutil as ps
import threading

try:
    import ccs
    CCSENV=True
except ImportError:
    CCSENV=False
    

class MemorySnapper:

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
        def vmss(self):
            return list(self._vmss.values())

        @property
        def times(self):
            return list(self._vmss.keys())

    def __init__(self, existing_data_file=None, base_monitoring=False):
        self._base_monitoring = base_monitoring
        self.__proc_names = set()
        self.totals = {}
        if existing_data_file == None:
            self.__data_file = "memory_data_tmp.dat"
        else:
            self.__data_file = existing_data_file

        # Check if file exists, if it does load it as a pickle file into a dictionary
        # If it doesn't, create an empty dictionary
        try:
            with open(self.__data_file, "rb") as f:
                loaded_data = pickle.load(f)
                self.__dict__.update(loaded_data)

        except FileNotFoundError as err:
            self.__data = {}

    def proc_by_name(self, name):
        for pid in self.pids:
            if self.__data[pid].name == name:
                return self.__data[pid]

    def __getitem__(self, pid):
        return self.__data[pid]

    @property
    def processes(self):
        return self.__proc_names

    @property
    def pids(self):
        return self.__data.keys()

    def __enter__(self):
        return self

    def close(self):
        with open(self.__data_file, "wb") as fp:
            pickle.dump(self.__dict__, fp)

    def take_memory_snapshot(self):

        # SETUP TIME
        if CCSENV:
            total = 0
            env_procs = ccs.GetEnvProcs(
                full_report=True
            )  # Whilst process_iter might be as thread safe as can be this definetly isn't
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
        print(f"Total memory usage: {total_mem}")
        self.totals[current_time]=total_mem

    def detect_leaks(self,algo="linefit"):
        """ Detect memory leaks using a given algorithm
        
        Args:
            algo: Algorithm to use to detect memory leaks
        
        Returns: A set of process names that are abnormally using memory
        """
        if algo=="linefit":
            return self.detect_leaks_line_fit()
        else:
            raise NotImplementedError()

    def detect_leaks_line_fit(self):
        grads = []
        abnorm_names = set()
        abnorm_pids = set()
        for proc in self.pids:
            m,c  = np.polyfit(date2num(self[proc].times), self[proc].vmss, 1) #Fit a straight line to the data
            if m>0.1:
                abnorm_names.add(self.__data[proc].name)
                abnorm_pids.add(proc)
            grads.append(m) 
        logging.warning(type((abnorm_names, abnorm_pids)))
        return (abnorm_names, abnorm_pids)

    def plot_data(self, proc_pid=None):
        if proc_pid is None:
            procs_to_plot = self.pids

        else:
            procs_to_plot = [proc_pid]

        for proc in procs_to_plot:
            plt.scatter(self[proc].times, np.array(self[proc].vmss) / 1e6, label=self.__data[proc].name)

        plt.legend()
        plt.xlabel("Time stamp")
        plt.ylabel("Memory usage (MB)")
        plt.tight_layout()
        plt.xticks(rotation=45)
        plt.show()

class MemoryMonitor(MemorySnapper):
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
