import time
import dask
from dask.distributed import Client, LocalCluster
from concurrent.futures import ThreadPoolExecutor
from dask.delayed import Delayed
from dask.threaded import get


from parla import sleep_nogil, sleep_gil
import argparse

free_sleep = sleep_nogil
lock_sleep = sleep_gil

parser = argparse.ArgumentParser()
parser.add_argument("-b", type=int, default=14)
parser.add_argument("-workers", default=4, type=int)
parser.add_argument("-t", type=int, default=1000)
parser.add_argument("-accesses", type=int, default=1)
parser.add_argument("-verbose", type=int, default=0)
parser.add_argument("-frac", type=float, default=0)
args = parser.parse_args()


kernel_time = args.t / args.accesses
free_time = kernel_time * (1 - args.frac)
lock_time = kernel_time * (args.frac)


def waste_time(i, deps):
    if args.verbose:
        inner_start_t = time.perf_counter()
        print("Task", i, deps, " | Start", flush=True)

    for k in range(args.accesses):
        free_sleep(free_time)
        lock_sleep(lock_time)

    if args.verbose:
        inner_end_t = time.perf_counter()
        print(
            "Task", i, deps, " | Inner Time: ", inner_end_t - inner_start_t, flush=True
        )


def create_graph(n):
    dsk = {}
    for j in range(n):
        for k in range(j):
            syrk_deps = [f"syrk_{j}_{_}" for _ in range(k)]
            syrk_deps += [f"solve_{j}_{k}"]
            dsk[f"syrk_{j}_{k}"] = (waste_time, (j, k), syrk_deps)

        potrf_deps = [f"syrk_{j}_{_}" for _ in range(j)]
        dsk[f"potrf_{j}"] = (waste_time, j, potrf_deps)

        for i in range(j + 1, n):
            for k in range(j):
                gemm_deps = [f"solve_{j}_{k}", f"solve_{i}_{k}"]
                gemm_deps += [f"gemm_{i}_{j}_{_}" for _ in range(k)]
                dsk[f"gemm_{i}_{j}_{k}"] = (waste_time, (i, j, k), gemm_deps)

            solve_deps = [f"gemm_{i}_{j}_{_}" for _ in range(j)]
            solve_deps += [f"potrf_{j}"]
            dsk[f"solve_{i}_{j}"] = (waste_time, (i, j), solve_deps)

    return dsk


if __name__ == "__main__":
    print(
        ", ".join(
            [
                str("workers"),
                str("n"),
                str("task_time"),
                str("accesses"),
                str("frac"),
                str("total_time"),
            ]
        ),
        flush=True,
    )
    with dask.config.set(pool=ThreadPoolExecutor(args.workers)):
        start_t = time.perf_counter()
        dsk = create_graph(args.b)
        get(dsk, f"potrf_{args.b-1}")
        end_t = time.perf_counter()
        elapsed_t = end_t - start_t

        print(
            ", ".join(
                [
                    str(args.workers),
                    str(args.b),
                    str(args.t),
                    str(args.accesses),
                    str(args.frac),
                    str(elapsed_t),
                ]
            ),
            flush=True,
        )
