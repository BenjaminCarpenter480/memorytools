from datetime import timedelta
import psutil as ps
from typing import Annotated


DEBUG_PLOTTING: Annotated[bool, "Whether to enable debug plotting."] = False

WIN_MIN_NUM_POINTS_RESAMPLE: Annotated[
    int,
    "Number of points in a dataset required to do a resample or any further analysis. Filters out very short running processes.",
] = 10

RESAMPLE_MIN_WIN: Annotated[
    float,
    "Minimum window size for resampling in seconds. Should be an increase on the recorded delta time.",
] = timedelta(seconds=0.5).total_seconds()

WIN_MIN_NUM_POINTS_DETECT: Annotated[
    int,
    "Minimum number of points required for detection. 10s is the smallest window size.",
] = int(20)

R_SQR_MIN: Annotated[
    float,
    "Minimum R-squared value required. Increased confidence from the paper's default of 0.8 since " 
    "we are using a significantly smaller window size.",
] = 0.9

CRITICAL_TIME_MAX: Annotated[int, "Maximum critical time in seconds."] = (
    60 * 60 * 1
)  # 1 hour

CRITICAL_MEMORY_USAGE: Annotated[int, "Critical memory usage in bytes."] = (
    ps.virtual_memory().total
)

MAX_TIME_DIFF: Annotated[
    float,
    "Maximum time difference between data points to be considered a gap in seconds.",
] = 0.5

CPD_THRESHOLD: Annotated[
    int,
    "Threshold for change point detection. 3 times the standard deviation, as suggested by the paper.",
] = 3
