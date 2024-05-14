from datetime import timedelta
import datetime
import logging
from typing import List, Tuple

from matplotlib import pyplot as plt
from matplotlib.dates import date2num
import numpy as np
import psutil as ps
import scipy
import ruptures as rpt
import ruptures.show
import scipy.interpolate
import scipy.stats


try:
    import ccs
    CCSENV=True
except ImportError:
    CCSENV=False


DEBUG_PLOTTING = False
WIN_MIN_NUM_POINTS_DETECT =  int(200) # points = 1s
WIN_MIN_NUM_POINTS_RESAMPLE = 10 #Number of points required to do a resample/any further analysis 
RESAMPLE_MIN_WIN = timedelta(seconds=0.005).total_seconds() # 5ms
R_SQR_MIN = 0.9 #From paper
CRITICAL_TIME_MAX = 60*60*1 # 1 hours
CRITICAL_MEMORY_USAGE = ps.virtual_memory().total
MAX_TIME_DIFF = 0.5 #Time between data points to be considered a gap
CPD_THRESHOLD = 3 # 3 times the standard deviation, from paper
        
class MemoryAnalysis():
    """Class to analyse memory data to be used in conjunction with MemorySnapper/MemoryMonitor"""

    def __init__(self, memory_data=None) -> None:
        self.__memory_data = memory_data

    def resample_data(self, times, vmss):
        """Resample the memory data to a fixed time interval"""

        if len(times) <= WIN_MIN_NUM_POINTS_RESAMPLE:
            self.logger().info("Not enough data to resample")
            raise ValueError("Not enough data to resample")

        times  = np.array(times, dtype=float)

        #Do resample
        ts_new = np.arange(min(times),max(times),RESAMPLE_MIN_WIN)
        vmss_new = np.interp(ts_new,times,vmss)

        return ts_new, vmss_new

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

        for pid in abnorm_pids:
            self.logger().warning(f"Abnormal memory usage detected in process: {self.__memory_data[pid].name}"
                            f"with pid {pid}")

        return (abnorm_names, abnorm_pids)

    def logger(self):
        if CCSENV:
            return ccs.logger
        else:            
            return logging.getLogger(__name__)


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
        #Init counters for how well we have been able to process a dataset
        unable_to_process = 0
        attempts_to_process = 0

        for pid in self.__memory_data.pids:
            self.logger().info(f"Processing {self.__memory_data[pid].name}-{pid}")
            # DEBUG INFO COUNTERS
            attempts_to_process = attempts_to_process + 1 
            attempts_to_resample = 0 # Local number of resamplings we have attempted
            unable_to_resample = 0 # Local number of resamplings we have been unable to do
            processed = False #Flag to indicate if we have processed this PID
            
            ##PREPROCESSING

            #Storing locally data
            input_data = self.__memory_data[pid]
            #Get time as a float, only care about number at this point
            ts_full = list(map(datetime.datetime.timestamp, input_data.times))
            vmss_full = input_data.vmss
            
            ## GAP ANALYSIS AND FILTERING ##
            #We need to ensure that we are not creating windows which includes a large gap in input_data.times
            # data with such gaps is not reliable when resampled and should be considered a separate data set in the below case
            # We will do this by finding gaps above a threshold in the data and splitting the data into separate data sets on these
            # gaps
            ts_diff = np.diff(ts_full)
            ts_diff = np.insert(ts_diff,0,0) #Insert a 0 at the start to keep the array the same length

            #Find the gaps
            gaps = np.where(ts_diff>MAX_TIME_DIFF)[0]
            self.logger().debug(f"{input_data.name}-{pid}: Found {len(gaps)} gaps in data")
            if len(gaps) != 0:
                #We have gaps, we need to split the data
                ts_splits = np.split(ts_full,gaps)
                vmss_splits = np.split(vmss_full,gaps)
            else:
                ts_splits = [ts_full]
                vmss_splits = [vmss_full]

            ## RESAMPLING ##
            for i in range(len(ts_splits)):
                ts = ts_splits[i]
                ys = vmss_splits[i]
                
                #Now we need to resample the data   
                try:
                    attempts_to_resample = attempts_to_resample + 1
                    ts_rsampl, vmss_rsampl = self.resample_data(ts, ys)
                except ValueError:
                    unable_to_resample = unable_to_resample + 1
                    continue
                processed = True 

                ###LINEAR REGRESSION ###
                # Now we do the linear regression
                i = WIN_MIN_NUM_POINTS_DETECT
                window_max = len(ts_rsampl)
                n = len(ts_rsampl)
                while(i<= n and i<=window_max):
                    self.logger().debug(f"{input_data.name}-{pid}: Processing window {n-i}/{n}")
                    ts = ts_rsampl[n-i:n]
                    ys = vmss_rsampl[n-i:n]
                        
                    m,c,r_pcc,*_ =scipy.stats.linregress(ts,ys) #Gives us Pearson correlation coeff unlike np.polyfit
                    #Now we do some more inteligent stuff compared to linefit
                    r2 = r_pcc**2 #Rsquare is the square of the pearson correlation coefficient
                    if m == 0:
                        t_crit = np.Infinity # No memory leak, gradient flat
                    else:
                        t_crit = (CRITICAL_MEMORY_USAGE - c)/m

                    if (r2>=R_SQR_MIN and t_crit > CRITICAL_TIME_MAX):
                        print(r2)
                        if (DEBUG_PLOTTING):
                            plt.scatter(input_data.times,input_data.vmss, label="Original")
                            plt.scatter(list(map(datetime.datetime.fromtimestamp,ts)),ys, label="Resampled")
                            plt.legend()
                            plt.show()
                        anomalus_names.add(self.__memory_data[pid].name)
                        anomalus_pids.add(pid)
                        break #Proc has issues, escape    

                    i = i+1
            if (processed  == False):
                #We were unable to process this PID due to it not being well formed enough, report this
                unable_to_process = unable_to_process + 1
                self.logger().warning(f"{input_data.name}-{pid}: Insufficient data for process {input_data.name} with pid {pid}")
                self.logger().warning(f"{input_data.name}-{pid}: Unable to resample {unable_to_resample}/{attempts_to_resample}")
            else:
                self.logger().info(f"{input_data.name}-{pid}: Unable to resample {unable_to_resample}/{attempts_to_resample}")
        if (unable_to_process > 0 and attempts_to_process > 0):
            self.logger().warning("Unable to process %d/%d",unable_to_process, attempts_to_process)
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


        attempts_to_process = 0 
        unable_to_process = 0
        for pid in self.__memory_data.pids:

            attempts_to_process = attempts_to_process + 1
            
            #Resample data
            input_data = self.__memory_data[pid]
            try:
                ts_f, ys_f = self.resample_data(input_data.times, input_data.vmss)
                # if (self.__memory_data[pid].name == "python3"):
                #     # plt.scatter(input_data.times,input_data.vmss, label="Original")
                #     # plt.scatter(list(map(datetime.datetime.fromtimestamp,ts_full)),vmss_full, label="Resampled")
                #     # plt.legend()
                #     # plt.show()
            except ValueError:
                self.logger().warning(f"Insufficient data to resample for process {input_data.name} with pid {pid}")
                unable_to_process = unable_to_process + 1
                continue
            

            change_points = self.change_points_detection(ts_f,ys_f)
            if(change_points==[]):
                #No change points so presumably no memory leak
                continue
            num_change_points = len(change_points)
            i = 0
            while (i <= num_change_points):
                
            # for i in range(num_change_points):
                p1 = np.where(ts_f==change_points[num_change_points-i])
                p2 = np.where(ts_f==change_points[num_change_points])
                ts = ts_f[p1:p2]
                ys = ys_f[p1:p2]

                #Do typical linear analysis
                m,c,r_pcc,*_ =scipy.stats.linregress(ts,ys)
                r2 = r_pcc**2 #Rsquare is the square of the pearson correlation coefficient
                if m == 0:
                    t_crit = np.Infinity # No memory leak, gradient flat
                else:
                    t_crit = (CRITICAL_MEMORY_USAGE - c)/m

                if (r2>=R_SQR_MIN and t_crit > CRITICAL_TIME_MAX):
                    anomalus_names.add(self.__memory_data[pid].name)
                    anomalus_pids.add(pid)
                    break #Proc has issues, escape

                i = i+1
