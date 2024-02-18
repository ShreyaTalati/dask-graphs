import time
import numpy as np
import dask
from concurrent.futures import ThreadPoolExecutor
from dask.threaded import get


from parla import sleep_nogil, sleep_gil
import argparse

free_sleep = sleep_nogil
lock_sleep = sleep_gil

parser = argparse.ArgumentParser()
parser.add_argument(
    "-workers",
    type=int,
    default=1,
    help="How many workers to use. This will perform a sample of 1 to workers by powers of 2",
)
parser.add_argument(
    "-width",
    type=int,
    default=0,
    help="The width of the task graph. If not set this is equal to nworkers.",
)
parser.add_argument("-steps", type=int, default=4, help="The depth of the task graph.")
parser.add_argument(
    "-d", type=int, default=7, help="The size of the data if using numba busy kernel"
)
parser.add_argument(
    "-n",
    type=int,
    default=2**23,
    help="The size of the data if using numba busy kernel",
)
parser.add_argument(
    "-isync",
    type=int,
    default=0,
    help="Whether to synchronize (internally) using await at every timestep.",
)
parser.add_argument(
    "-vcus",
    type=int,
    default=1,
    help="Whether tasks use vcus to restrict how many can run on a single device",
)
parser.add_argument(
    "-deps",
    type=int,
    default=1,
    help="Whether tasks have dependencies on the prior iteration",
)
parser.add_argument("-verbose", type=int, default=0, help="Verbose!")

parser.add_argument(
    "-t",
    type=int,
    default=10,
    help="The task time in microseconds. These are hardcoded in this main.",
)
parser.add_argument(
    "-accesses",
    type=int,
    default=1,
    help="How many times the task stops busy waiting and accesses the GIL",
)
parser.add_argument(
    "-frac",
    type=float,
    default=0,
    help="The fraction of the total task time that the GIL is held",
)

parser.add_argument(
    "-strong",
    type=int,
    default=0,
    help="Whether to use strong (1) or weak (0) scaling of the task time",
)
parser.add_argument(
    "-sleep",
    type=int,
    default=1,
    help="Whether to use the synthetic sleep (1) or the numba busy kernel (0)",
)
parser.add_argument(
    "-restrict",
    type=int,
    default=0,
    help="This does two separate things. If using isync it restricts to only waiting on the prior timestep. If using deps, it changes the dependencies from being a separate chain to depending on all tasks in the prior timestep",
)

args = parser.parse_args()

kernel_time = args.t / args.accesses
free_time = kernel_time * (1 - args.frac)
lock_time = kernel_time * (args.frac)


def waste_time(id, deps):
    if args.verbose:
        inner_start_t = time.perf_counter()
        print("Task", id, deps, " | Start", flush=True)

    for k in range(args.accesses):
        free_sleep(free_time)
        lock_sleep(lock_time)

    if args.verbose:
        inner_end_t = time.perf_counter()
        print(
            "Task", id, deps, " | Inner Time: ", inner_end_t - inner_start_t, flush=True
        )

    return id


def create_graph(steps, width):
    dsk = {}
    for t in range(steps + 1):
        for i in range(width):
            step = 2 ** (steps - t)
            dependency_idx = [i - step, i, i + step]
            print("Level: ", t, "Step: ", step)
            if t > 0:
                dependencies = [
                    f"T_{t-1}_{j}" for j in dependency_idx if 0 <= j < width
                ]
            else:
                dependencies = []

            id = (t, i)
            sid = f"T_{t}_{i}"

            dsk[sid] = (waste_time, id, dependencies)

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
        steps = int(np.log2(args.width) + 1)
        start_t = time.perf_counter()
        dsk = create_graph(steps, args.width)
        result = get(dsk, [f"T_{steps}_{k}" for k in range(args.width)])
        end_t = time.perf_counter()
        elapsed_t = end_t - start_t
        print(
            ", ".join(
                [
                    str(args.workers),
                    str(steps),
                    str(args.t),
                    str(args.accesses),
                    str(args.frac),
                    str(elapsed_t),
                ]
            ),
            flush=True,
        )
