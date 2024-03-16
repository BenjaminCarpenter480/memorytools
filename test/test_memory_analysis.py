import numpy as np
import pytest

from memorytools.memoryanalysis import MemoryAnalysis


def test_change_points_detection_empty_dataset():
    memory_analysis = MemoryAnalysis()
    ts = []
    ys = []
    expected_result = []
    x = memory_analysis.change_points_detection(ts, ys)
    print(x)
    assert list(x) == expected_result


def test_change_points_detection_single_data_point():
    memory_analysis = MemoryAnalysis()
    ts = [0]
    ys = [10]
    expected_result = []
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_constant_dataset():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4]
    ys = [10, 10, 10, 10, 10]
    expected_result = []
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_increasing_dataset():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4]
    ys = [10, 20, 30, 40, 50]
    expected_result = []
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_decreasing_dataset():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4]
    ys = [50, 40, 30, 20, 10]
    expected_result = []
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_dataset_with_change_points():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ys = [10, 20, 30, 40, 50, 10, 20, 30, 40, 50]
    expected_result = [5]
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_dataset_with_noise():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ys = [10, 20, 30, 40, 50, 11, 19, 31, 39, 50]
    expected_result = [5]
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_dataset_with_negative_values():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ys = [-10, -20, -30, -40, -50, -10, -20, -30, -40, -50]
    expected_result = [5]
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_dataset_with_large_values():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ys = [1000, 2000, 3000, 4000, 5000, 1000, 2000, 3000, 4000, 5000]
    expected_result = [5 ]
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

def test_change_points_detection_dataset_with_random_values():
    memory_analysis = MemoryAnalysis()
    ts = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ys = np.random.randint(0, 100, size=10)
    expected_result = []
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result

@pytest.mark.skip
def test_change_points_detection_dataset_with_random_values():
    memory_analysis = MemoryAnalysis()
    ts = np.arange(0,1000,1)
    ys = np.random.randint(0, 100, size=1000)
    expected_result = []
    assert list(memory_analysis.change_points_detection(ts, ys)) == expected_result
