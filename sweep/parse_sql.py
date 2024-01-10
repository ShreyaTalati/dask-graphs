import sqlite3
import pandas as pd
import sys
import numpy as np

from dataclasses import dataclass 

@dataclass(slots=True) 
class Result:
    kernel_total: float = 0
    kernel_average: float = 0
    kernel_median: float = 0

    task_cleanup_total: float = 0
    task_cleanup_average: float = 0
    task_cleanup_median: float = 0

    task_spawn_total: float = 0


def get_sleep_difference(file_name):
    db = sqlite3.connect(file_name)

    df_cpp = pd.read_sql(
        "SELECT start, end, globalTid from 'NVTX_EVENTS' where (text='Parla::cpp::cpu_busy_sleep' or text='Parla::cpp:cpu_busy_sleep')",
        db,
    )

    df_python = pd.read_sql(
        "SELECT start, end, globalTid from 'NVTX_EVENTS' where (text='Parla::python::cpu_busy_sleep' or text='Parla::python:cpu_busy_sleep')",
        db,
    )

    stats = Result()

    diff_list = []
    for tid in df_cpp["globalTid"].unique():
        cpp_times = df_cpp[df_cpp["globalTid"] == tid]
        python_times = df_python[df_python["globalTid"] == tid]

        cpp_duration = cpp_times["end"] - cpp_times["start"]
        python_duration = python_times["end"] - python_times["start"]

        difference = python_duration - cpp_duration
        diff_list.append(difference)

    difference_df = pd.concat(diff_list)
    # average = np.mean(np.asarray([d.mean() for d in diff_list]))

    stats.kernel_total = difference_df.sum()
    stats.kernel_average = difference_df.mean() 
    stats.kernel_median = difference_df.median()
    #
    if 'task_cleanup_total' in stats.__slots__:
        df_cleanup = pd.read_sql(
            "SELECT start, end, globalTid from 'NVTX_EVENTS' where (text='Parla::python::task_cleanup')", 
            db
        )
        df_cleanup = df_cleanup['end'] - df_cleanup['start']
        stats.task_cleanup_total = df_cleanup.sum()
        stats.task_cleanup_average = df_cleanup.mean()
        stats.task_cleanup_median = df_cleanup.median()

    if 'task_spawn_total' in stats.__slots__:
        df_spawn = pd.read_sql(
            "SELECT start, end, globalTid from 'NVTX_EVENTS' where (text='Parla::app::launch_tasks')", 
            db
        )
        df_spawn = df_spawn['end'] - df_spawn['start']
        stats.task_spawn_total = df_spawn.sum()

    return stats


def main():
    r = Result()
    fields = ', '.join(r.__slots__)
    print("n, t, workers, frac, accesses, "+fields)
    for frac in [0, 0.0125, 0.025, 0.05, 0.1]:
        for n in [100, 500, 1000]:
            for t in [500, 1000, 2000, 4000, 8000, 16000, 32000, 64000]:
                for acc in [1, 5, 10]:
                    for workers in [1, 2, 4, 8, 15]:
                        try:
                            file_name = f"profile/_workers_{workers}__sleep_1__strong_0__steps_{n}__isync_0__restrict_0__t_{t}__deps_1__frac_{frac}__accesses_{acc}.sqlite"
                            stats = get_sleep_difference(file_name)
                            result_string = ", ".join([str(getattr(stats, r)) for r in stats.__slots__])
                            print(f"{n}, {t}, {workers}, {frac}, {acc}, "+result_string)
                        except:
                            pass

main()
