import argparse
from concurrent.futures import thread
import csv
import logging
import pickle
import time
import matplotlib.pyplot as plt
import datetime
import numpy as np
import psutil as ps
import threading
from typing import List, Tuple
from .memoryanalysis import MemoryAnalysis

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

        def __init__(self, pid, name=None):
            """
            Base monitoring used to collect data that can be used to calculate the stdev of the memory usage for the entire environment
            """
            self.pid = pid
            if name is None:
                self.name = ps.Process(pid).name()
            else:
                self.name = name
            self._vmss = {}

        def __getitem__(self, time):
            return self._vmss[time]

        def __setitem__(self, time, full_memory):
            if(isinstance(full_memory,int)):
                self._vmss[time] = full_memory
            else:
                self._vmss[time] = full_memory.vms

        @property
        def vmss(self) ->List[int]:
            """Returns a List[int] of virtual memory sizes for a process over time"""
            return list(self._vmss.values())

        @property
        def times(self)->List[datetime.datetime]:
            """Returns a List[datetime.datetime] of times at which a memory snapshot was taken"""
            return list(self._vmss.keys())

    def __init__(self, existing_data_file=None):
        self.__proc_names = set()
        self.totals = {}
        if existing_data_file is None:
            self.__data_file = "memory_data_tmp.dat"
        else:
            self.__data_file = existing_data_file
        self.logger().debug("MEMORY DATA FILE: " + self.__data_file)
        # Check if file exists, if it does load it as a pickle file into a dictionary
        # If it doesn't, create an empty dictionary
        try:
            with open(self.__data_file, "rb") as f:
                loaded_data = pickle.load(f)
                self.__dict__.update(loaded_data)
                self.logger().debug("LOADING MEMORY DATA FROM FILE")

        except FileNotFoundError as err:
            self.__data = {}
            self.logger().error("NO MEMORY DATA FILE FOUND")

        self.analysis_module = MemoryAnalysis(self)

    def procs_by_name(self, name):
        """
        Return a list of Dict[datetime.datetime, int] of process data that match the passed name
        """
        procs=[]
        for pid in self.pids:
            if self.__data[pid].name == name:
                procs.append(self.__data[pid])
        return procs

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
    
    def logger(self):
        if CCSENV:
            return ccs.logger
        else:
            return logging.getLogger(__name__)

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
            if ccs.procName in env_procs:
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
        self.logger().info(f"Total memory usage: {total_mem}")
        self.totals[current_time]=total_mem

    def detect_leaks(self,algo="LBR")->Tuple[List[str],List[int]]:
        """ Detect memory leaks using a given algorithm

        Args:
            algo: Algorithm to use to detect memory leaks

        Returns:
            A set of names and pids of processes that are abnormally using memory
        """
        return self.analysis_module.detect_leaks(algo)

    def _plot_data(self, proc_pids:List[int]=None):
        """
        Helper function to plot the memory usage of a process over time or all processes if proc_pid is None
        
        Args:
            proc_pid: Process id of process to plot default is None which plots all processes
        """
        procs_to_plot = self.pids if proc_pids is [] else proc_pids
        for proc in procs_to_plot:
            plt.scatter(self[proc].times, np.array(self[proc].vmss) / 1e6, label=(self.__data[proc].name,proc))

        plt.legend()
        plt.xlabel("Time stamp")
        plt.ylabel("Memory usage (MB)")
        plt.tight_layout()
        plt.xticks(rotation=45)

    def plot_data_to_file(self, proc_pads=None, names=None, filename=None):
        """
        Plot the memory usage of a process over time or all processes if proc_pid is None and save to a file
        
        Args:
            proc_pid: Process id of process to plot default is None which plots all processes
            filename: If provided, the plot will be saved to this file
        """
        if names:
            proc_pads = []
            for name in names:
                for proc in self.procs_by_name(name):
                    proc_pads.append(proc.pid)
        self._plot_data(proc_pads)
        
        if filename:
            plt.savefig(filename)
        plt.close()

    def plot_data_to_screen(self, proc_pids=None, block=False, names:List[str]=None):
        """
        Plot the memory usage of a process over time or all processes if proc_pid is None and show on screen
        
        Args:
            proc_pid: Process id of process to plot default is None which plots all processes
            block: If True, plt.show() will be blocking
        """
        if names:
            proc_pids = []
            for name in names:
                for proc in self.procs_by_name(name):
                    proc_pids.append(proc.pid)
        self._plot_data(proc_pids)
        
        plt.show(block=block)
        return plt

    def export_to_csv(self, filename):
        """
        Export the memory usage data to a CSV file.

        Args:
            filename: The name of the file where the data will be saved
        """
        with open(filename, 'a', newline='') as csvfile:
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

    def import_from_csv(self, filename):
        """
        Import memory usage data from a CSV file.

        Args:
            filename: The name of the file to import data from
        """
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                proc_id = int(row['Process ID'])
                proc_name = row['Process Name']
                time = datetime.datetime.fromisoformat(row['Time'])  
                memory = int(row['Memory Usage'])
                if proc_id not in self.__data.keys():
                    self.__data[proc_id] = self.ProcMemData(proc_id, name=proc_name)
                    self.__proc_names.add(proc_name)
                self.__data[proc_id][time] = memory

class MemoryMonitor(MemorySnapper):
    """
        Class for continuous monitoring of processes memory usage
        Args:
            data_file: Path to the data file for persistence across instances
            time_interval: Time interval between snapshots monitoring in seconds
        

        Example usage::
            >>> mem_monitor = MemoryMonitor() #Create a memory monitor object
            >>> mem_monitor.start_monitoring() #Start monitoring memory usage
            >>> <Do some stuff while monitoring memory usage>
            >>> mem_monitor.stop_monitoring() #Stop monitoring memory usage
    """
    def __init__(self, data_file=None, time_interval:float=1):
        super().__init__(existing_data_file=data_file)

        self.__time_interval = time_interval
        #Setup but do not start monitoring thread
        self.__monitoring=False
        self.__monitor_thread = threading.Thread(target=self.__monitor_loop)
    
    def start_monitoring(self):
            """
            Starts the memory monitoring process.

            This method creates a monitor thread if it has not been created already,
            and starts the monitoring loop in a separate thread.

            """
            # If the monitor thread has not been created, create it
            try:
                self.__monitor_thread.name
            except AttributeError:
                self.__monitor_thread = threading.Thread(target=self.__monitor_loop)

            self.__monitoring=True
            self.__monitor_thread.start()

    def __monitor_loop(self):
        while self.__monitoring:
            self.take_memory_snapshot()
            time.sleep(self.__time_interval)

    def stop_monitoring(self):
            """
            Stops the monitoring of memory usage.

            This method sets the `__monitoring` flag to False, indicating that the monitoring should stop.
            If the monitor thread is currently running, it is joined to the main thread to ensure proper termination.
            If the monitor thread is not running, an error message is logged.

            """
            self.__monitoring = False
            if self.__monitor_thread.is_alive():
                self.__monitor_thread.join()
            else: 
                self.logger().error("Cannot stop thread as it is not running.")
            del self.__monitor_thread

    def is_monitoring(self):
        return self.__monitoring

    def close(self):
        if self.is_monitoring():
            self.stop_monitoring()
        super().close()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Memory Snapper Command Line Interface')
    parser.add_argument('command', choices=['snapshot', 'export','monitor'], help="Command to execute\n"
                                                                                        "snapshot: Take a memory snapshot\n"
                                                                                        "export: Export memory data to a CSV file\n"
                                                                                        "monitor: Start monitoring memory usage in the background")
    parser.add_argument('--data-file', help='Path to the data file for persistence across instances')
    parser.add_argument('--interval', type=int, help='Time interval for monitoring in seconds')
    parser.add_argument('--output-file',required=False,default="memorymonitor_out.csv", help='Path to the output file for exporting data')

    args = parser.parse_args()

    if args.command == 'snapshot':
        mem_snap = MemorySnapper(existing_data_file=args.data_file)
        mem_snap.take_memory_snapshot()
        mem_snap.close()
        print('Memory snapshot taken successfully.')

    elif args.command == 'export':
        mem_snap = MemorySnapper(existing_data_file=args.data_file)
        mem_snap.export_to_csv(args.output_file)
        print(f'Data exported to {args.output_file} successfully.')

    elif args.command == 'save':
        mem_snap = MemorySnapper(existing_data_file=args.data_file)
        mem_snap.close()
        print(f'Data saved to {args.data_file} successfully.')

    elif args.command == 'monitor':
        mem_monitor = MemoryMonitor(time_interval=args.interval)
        print('Memory monitoring started. Press Ctrl+C to stop.')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            mem_monitor.stop_monitoring()
            print('Memory monitoring stopped.')
