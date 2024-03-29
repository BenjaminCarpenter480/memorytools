import logging
from typing import List, Tuple

from matplotlib.dates import date2num
import numpy as np
import psutil as ps
import scipy
import ruptures as rpt
import ruptures.show
import scipy.stats

WINDOW_MIN = 4 # Add in some form of smoothing
R_SQR_MIN = 0.8 #From paper
CRITICAL_TIME_MAX = 60*60*1 # 1 hours
CRITICAL_MEMORY_USAGE = ps.virtual_memory().total

CPD_THRESHOLD = 3 # 3 times the standard deviation, from paper
        
class MemoryAnalysis():
    """Class to analyse memory data to be used in conjunction with MemorySnapper/MemoryMonitor"""

    def __init__(self, memory_data=None) -> None:
        self.__memory_data = memory_data

    def detect_leaks(self,algo="linefit")->Tuple[List[str],List[int]]:
        """ Detect memory leaks using a given algorithm

        Args:
            algo: Algorithm to use to detect memory leaks

        Returns:
            A set of names and pids of processes that are abnormally using memory
        """
        if algo=="linefit":
            __algo = self.detect_leaks_line_fit
        elif algo=="LBR":
            __algo = self.detect_leaks_linear_backward_regression
        elif algo=="LBRCPD":
            __algo = self.linear_backward_regression_with_change_points    
        else:
            raise NotImplementedError()

        abnorm_names, abnorm_pids = __algo()
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
        abnorm_names = set()
        abnorm_pids = set()
        for proc in self.__memory_data.pids:
            m,c  = np.polyfit(date2num(self.__memory_data[proc].times),
                                self.__memory_data[proc].vmss,
                                1) #Fit a straight line to the data
            if m>0.1:
                abnorm_names.add(self.__memory_data[proc].name)
                abnorm_pids.add(proc)
        return (abnorm_names, abnorm_pids)

    def detect_leaks_linear_backward_regression(self)->Tuple[List[str],List[int]]:
        """Detect memory leaks using the linear backward regression algorithm
        """
        anomalus_names = set()
        anomalus_pids = set()
        
        for pid in self.__memory_data.pids:
            input_data = self.__memory_data[pid]
            
            i = WINDOW_MIN
            window_max= len(input_data.times)
            n = len(input_data.times)
            while(i<= n and i<=window_max):
                ts = date2num(input_data.times[n-i:n])
                ys = input_data.vmss[n-i:n]
                m,c,r_pcc,*_ =scipy.stats.linregress(ts,ys) #Gives us Pearson correlation coeff unlike np.polyfit
                #Now we do some more inteligent stuff compared to linefit
                r2 = r_pcc**2 #Rsquare is the square of the pearson correlation coefficient
                if m == 0:
                    t_crit = np.Infinity # No memory leak, gradient flat
                else:
                    t_crit = (CRITICAL_MEMORY_USAGE - c)/m

                if (r2>=R_SQR_MIN and t_crit > CRITICAL_TIME_MAX):
                    anomalus_names.add(self.__memory_data[pid].name)
                    anomalus_pids.add(pid)
                        

                i = i+1
        return (anomalus_names, anomalus_pids)


    def change_points_detection(self, times, values, model="l2")->List[int]:
        """Calculate change points for the data set provided using the ruptures package

        Parameters:
            times (list): List of timestamps.
            values (list): List of corresponding values.
            model (str): Name of the model for detecting changes. Options are "l1", "l2", "rbf", "linear", "normal", "ar".

        Uses Ruptures, cite Truong, L. Oudre, N. Vayatis. Selective review of offline change 
        point detection methods. Signal Processing, 167:107299, 2020. [journal] [pdf]

    
        
        Returns:
            list: List of timestamps at which a change is detected.
    """
        # Combine times and values into a 2D array
        data = np.column_stack((times, values))
        try:
            # Fit the model with the data
            algo = rpt.Pelt(model=model).fit(data)

            # Retrieve the change points
            change_points = algo.predict(pen=CPD_THRESHOLD)
        except ruptures.exceptions.BadSegmentationParameters:
            return []

        return change_points[:-1] 

        


    def linear_backward_regression_with_change_points(self) -> Tuple[List[str],List[int]]:
        """ 
        More efficient version of linear_backward_regression, which uses the change points to reduce
        the number of iterations overwhich to do the linear regression.
        
        """
        anomalus_names = set()
        anomalus_pids = set()
        
        for pid in self.__memory_data.pids:
            input_data = self.__memory_data[pid]
            
            ts_f = date2num(input_data.times)
            ys_f = input_data.vmss    
            change_points = self.change_points_detection(ts_f,ys_f)
            print(change_points)
            num_change_points = len(change_points)
            for i in range(num_change_points):
                ts = ts_f[num_change_points-i:num_change_points]
                ys = ys_f[num_change_points-i:num_change_points]
                m,c,r_pcc,*_ =scipy.stats.linregress(ts,ys)
                r2 = r_pcc**2 #Rsquare is the square of the pearson correlation coefficient
                if m == 0:
                    t_crit = np.Infinity # No memory leak, gradient flat
                else:
                    t_crit = (CRITICAL_MEMORY_USAGE - c)/m

                if (r2>=R_SQR_MIN and t_crit > CRITICAL_TIME_MAX):
                    anomalus_names.add(self.__memory_data[pid].name)
                    anomalus_pids.add(pid)
                        
