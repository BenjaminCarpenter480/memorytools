import psutil as ps

WINDOW_MIN = 4 # Add in some form of smoothing
R_2_MIN = 0.8 #From paper
CRITICAL_TIME_MAX = 60*60*1 # 1 hours
CRITICAL_MEMORY_USAGE = ps.virtual_memory().total    R_2_MIN = 0.8 #From paper
CRITICAL_TIME_MAX = 60*60*1 # 1 hours
CRITICAL_MEMORY_USAGE = ps.virtual_memory().total