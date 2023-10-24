import pickle
import time
import matplotlib.pyplot as plt
import datetime
import numpy as np
import psutil as ps
import threading


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

            self.__stdev = 0

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

        # MEASURE TIME
        current_time = datetime.datetime.now()

        for p in ps.process_iter():
            p_pid = p.pid
            
            #'New' procs will be missing from stored info
            if p_pid not in self.__data.keys():
                self.__data[p_pid] = self.ProcMemData(p_pid)
                self.__proc_names.add(p.name())

            # Update memory usage
            self[p_pid][current_time] = p.memory_info()

    def plot_data(self, proc_name=None):
        if proc_name is None:
            procs_to_plot = self.pids

        else:
            procs_to_plot = [proc_name]

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

        self.__monitoring = True

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
