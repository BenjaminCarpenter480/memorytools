import logging
from typing import List, Tuple

from matplotlib.dates import date2num
import numpy as np
import psutil as ps
import scipy


class MemoryAnalysis():
    """Class to analyse memory data"""

    def __init__(self, memory_data) -> None:
        self.__memory_data = memory_data

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
        for proc in self.__memory_data.pids:
            m,c  = np.polyfit(date2num(self.__memory_data[proc].times), self.__memory_data[proc].vmss, 1) #Fit a straight line to the data
            if m>0.1:
                abnorm_names.add(self.__memory_data[proc].name)
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
        R_SQR_MIN = 0.8 #From paper
        CRITICAL_TIME_MAX = 60*60*1 # 1 hours
        CRITICAL_MEMORY_USAGE = ps.virtual_memory().total
        
        for pid in self.__memory_data.pids:
            # if self[pid].name != "python3":
            #     continue #TODO bcarpent Need to remove later
            input_data = self.__memory_data[pid]
            anomalus_ts = set()#type :set(datetimes) #Anomalus data points
            
            i = WINDOW_MIN
            window_max= len(input_data.times)
            n = len(input_data.times)
            while(i<= n and i<=window_max):
                ts = date2num(input_data.times[n-i:n])
                ys = input_data.vmss[n-i:n]
                # plt.scatter(ts,ys, label=i)
                m,c,r_pcc,*_ =scipy.stats.linregress(ts,ys) #Gives us Pearson correlation coeff unlike np.polyfit
                r2 = r_pcc**2 #Rsquare is the square of the pearson correlation coefficient
                if m == 0:
                    t_crit = np.Infinity # No memory leak, gradient flat
                else:
                    t_crit = (CRITICAL_MEMORY_USAGE - c)/m

                if (r2>=R_SQR_MIN):
                    print("-------------------------------------------")
                    # print(f"Data with good fit {self.__data[pid].name} pid {pid}")
                    # print(f"m: {m}, c: {c}, r2: {r2}")
                    # print(f"t_crit: {t_crit}")
                    # print("-------------------------------------------")
                    if(t_crit > CRITICAL_TIME_MAX):
                        #Add ts to the erronus stamps (unpack)
                        # anomalus_ts = anomalus_ts | set(ts[n-i:i]) #Add new ts to set of anomalus ones
                        anomalus_names.add(self.__memory_data[pid].name)
                        anomalus_pids.add(pid)
                        

                i = i+1
        # plt.legend()
        # plt.show()
        return (anomalus_names, anomalus_pids)
