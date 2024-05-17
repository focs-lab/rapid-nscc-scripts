import os
import subprocess
import sys
import yaml
import csv
import statistics

from dataclasses import dataclass
from typing import List
from datetime import datetime

from multiprocessing import Pool
from itertools import product
from subprocess import check_output


TRACES_LIST_YAML = "traces.yaml"
CONFIG_LIST_YAML = "config.yaml"
# CMD_PREFIX = 'java -cp "rapid.jar:./lib/*:./lib/jgrapht/*" Minjian -f std -p '
NUM_TEST_ITERS = 50

# ENGINES = ["HB", "UClock", "HBEpoch", "UClockEpoch"]
ENGINES = ["HBEpoch", "UClockEpoch"]
SAMPLING_RATES = [0.03, 0.05, 0.1, 0.2, 1]


@dataclass
class TestStats:
    test_name: str
    test_engine: str
    test_sampling_rate: float
    duration: int
    num_warnings: int

    num_original_acquires: int
    num_uclock_acquires: int
    uclock_acquires_rate: float

    num_original_releases: int
    num_uclock_releases: int
    uclock_releases_rate: float

    num_original_joins: int
    num_uclock_joins: int
    uclock_joins_rate: float

@dataclass
class TestAggStats:
    test_name: str
    test_engine: str
    test_sampling_rate: float

    duration: int
    duration_stdev: float
    duration_median: float
    duration_min: int
    duration_max: int

    num_warnings: int
    num_warnings_stdev: float
    num_warnings_median: float
    num_warnings_min: int
    num_warnings_max: int

    num_original_acquires: int
    num_original_acquires_stdev: float
    num_original_acquires_median: float
    num_original_acquires_min: int
    num_original_acquires_max: int

    num_uclock_acquires: int
    num_uclock_acquires_stdev: float
    num_uclock_acquires_median: float
    num_uclock_acquires_min: int
    num_uclock_acquires_max: int

    uclock_acquires_rate: float
    uclock_acquires_rate_stdev: float
    uclock_acquires_rate_median: float
    uclock_acquires_rate_min: float
    uclock_acquires_rate_max: float

    num_original_releases: int
    num_original_releases_stdev: float
    num_original_releases_median: float
    num_original_releases_min: int
    num_original_releases_max: int

    num_uclock_releases: int
    num_uclock_releases_stdev: float
    num_uclock_releases_median: float
    num_uclock_releases_min: int
    num_uclock_releases_max: int

    uclock_releases_rate: float
    uclock_releases_rate_stdev: float
    uclock_releases_rate_median: float
    uclock_releases_rate_min: float
    uclock_releases_rate_max: float

    num_original_joins: int
    num_original_joins_stdev: float
    num_original_joins_median: float
    num_original_joins_min: int
    num_original_joins_max: int

    num_uclock_joins: int
    num_uclock_joins_stdev: float
    num_uclock_joins_median: float
    num_uclock_joins_min: int
    num_uclock_joins_max: int

    uclock_joins_rate: float
    uclock_joins_rate_stdev: float
    uclock_joins_rate_median: float
    uclock_joins_rate_min: float
    uclock_joins_rate_max: float

    def header():
        return [
            "name",
            "engine",
            "sampling_rate",

            "duration",
            "duration_stdev",
            "duration_median",
            "duration_min",
            "duration_max",

            "num_warnings",
            "num_warnings_stdev",
            "num_warnings_median",
            "num_warnings_min",
            "num_warnings_max",

            "num_original_acquires",
            "num_original_acquires_stdev",
            "num_original_acquires_median",
            "num_original_acquires_min",
            "num_original_acquires_max",

            "num_uclock_acquires",
            "num_uclock_acquires_stdev",
            "num_uclock_acquires_median",
            "num_uclock_acquires_min",
            "num_uclock_acquires_max",

            "uclock_acquires_rate",
            "uclock_acquires_rate_stdev",
            "uclock_acquires_rate_median",
            "uclock_acquires_rate_min",
            "uclock_acquires_rate_max",

            "num_original_releases",
            "num_original_releases_stdev",
            "num_original_releases_median",
            "num_original_releases_min",
            "num_original_releases_max",

            "num_uclock_releases",
            "num_uclock_releases_stdev",
            "num_uclock_releases_median",
            "num_uclock_releases_min",
            "num_uclock_releases_max",

            "uclock_releases_rate",
            "uclock_releases_rate_stdev",
            "uclock_releases_rate_median",
            "uclock_releases_rate_min",
            "uclock_releases_rate_max",

            "num_original_joins",
            "num_original_joins_stdev",
            "num_original_joins_median",
            "num_original_joins_min",
            "num_original_joins_max",

            "num_uclock_joins",
            "num_uclock_joins_stdev",
            "num_uclock_joins_median",
            "num_uclock_joins_min",
            "num_uclock_joins_max",

            "uclock_joins_rate",
            "uclock_joins_rate_stdev",
            "uclock_joins_rate_median",
            "uclock_joins_rate_min",
            "uclock_joins_rate_max"
        ]

    def as_row(self):
        return iter(
            [
                self.test_name,
                self.test_engine,
                self.test_sampling_rate,

                self.duration,
                self.duration_stdev,
                self.duration_median,
                self.duration_min,
                self.duration_max,

                self.num_warnings,
                self.num_warnings_stdev,
                self.num_warnings_median,
                self.num_warnings_min,
                self.num_warnings_max,

                self.num_original_acquires,
                self.num_original_acquires_stdev,
                self.num_original_acquires_median,
                self.num_original_acquires_min,
                self.num_original_acquires_max,

                self.num_uclock_acquires,
                self.num_uclock_acquires_stdev,
                self.num_uclock_acquires_median,
                self.num_uclock_acquires_min,
                self.num_uclock_acquires_max,

                self.uclock_acquires_rate,
                self.uclock_acquires_rate_stdev,
                self.uclock_acquires_rate_median,
                self.uclock_acquires_rate_min,
                self.uclock_acquires_rate_max,

                self.num_original_releases,
                self.num_original_releases_stdev,
                self.num_original_releases_median,
                self.num_original_releases_min,
                self.num_original_releases_max,

                self.num_uclock_releases,
                self.num_uclock_releases_stdev,
                self.num_uclock_releases_median,
                self.num_uclock_releases_min,
                self.num_uclock_releases_max,

                self.uclock_releases_rate,
                self.uclock_releases_rate_stdev,
                self.uclock_releases_rate_median,
                self.uclock_releases_rate_min,
                self.uclock_releases_rate_max,

                self.num_original_joins,
                self.num_original_joins_stdev,
                self.num_original_joins_median,
                self.num_original_joins_min,
                self.num_original_joins_max,

                self.num_uclock_joins,
                self.num_uclock_joins_stdev,
                self.num_uclock_joins_median,
                self.num_uclock_joins_min,
                self.num_uclock_joins_max,

                self.uclock_joins_rate,
                self.uclock_joins_rate_stdev,
                self.uclock_joins_rate_median,
                self.uclock_joins_rate_min,
                self.uclock_joins_rate_max
            ]
        )

# aggregates the stats after running a test case N times
def aggregate_test_stats(tests_stats: List[TestStats]):
    duration_list = list(map(lambda ts: ts.duration, tests_stats))
    num_warnings_list = list(map(lambda ts: ts.num_warnings, tests_stats))

    num_original_acquires_list = list(map(lambda ts: ts.num_original_acquires, tests_stats))
    num_uclock_acquires_list = list(map(lambda ts: ts.num_uclock_acquires, tests_stats))
    uclock_acquires_rate_list = list(map(lambda ts: ts.uclock_acquires_rate, tests_stats))
    num_original_releases_list = list(map(lambda ts: ts.num_original_releases, tests_stats))
    num_uclock_releases_list = list(map(lambda ts: ts.num_uclock_releases, tests_stats))
    uclock_releases_rate_list = list(map(lambda ts: ts.uclock_releases_rate, tests_stats))
    num_original_joins_list = list(map(lambda ts: ts.num_original_joins, tests_stats))
    num_uclock_joins_list = list(map(lambda ts: ts.num_uclock_joins, tests_stats))
    uclock_joins_rate_list = list(map(lambda ts: ts.uclock_joins_rate, tests_stats))

    duration_mean = statistics.mean(duration_list)
    duration_stdev = statistics.stdev(duration_list)
    duration_median = statistics.median(duration_list)
    duration_min = min(duration_list)
    duration_max = max(duration_list)

    num_warnings_mean = statistics.mean(num_warnings_list)
    num_warnings_stdev = statistics.stdev(num_warnings_list)
    num_warnings_median = statistics.median(num_warnings_list)
    num_warnings_min = min(num_warnings_list)
    num_warnings_max = max(num_warnings_list)

    num_original_acquires_mean = statistics.mean(num_original_acquires_list)
    num_original_acquires_stdev = statistics.stdev(num_original_acquires_list)
    num_original_acquires_median = statistics.median(num_original_acquires_list)
    num_original_acquires_min = min(num_original_acquires_list)
    num_original_acquires_max = max(num_original_acquires_list)

    num_uclock_acquires_mean = statistics.mean(num_uclock_acquires_list)
    num_uclock_acquires_stdev = statistics.stdev(num_uclock_acquires_list)
    num_uclock_acquires_median = statistics.median(num_uclock_acquires_list)
    num_uclock_acquires_min = min(num_uclock_acquires_list)
    num_uclock_acquires_max = max(num_uclock_acquires_list)

    uclock_acquires_rate_mean = statistics.mean(uclock_acquires_rate_list)
    uclock_acquires_rate_stdev = statistics.stdev(uclock_acquires_rate_list)
    uclock_acquires_rate_median = statistics.median(uclock_acquires_rate_list)
    uclock_acquires_rate_min = min(uclock_acquires_rate_list)
    uclock_acquires_rate_max = max(uclock_acquires_rate_list)

    num_original_releases_mean = statistics.mean(num_original_releases_list)
    num_original_releases_stdev = statistics.stdev(num_original_releases_list)
    num_original_releases_median = statistics.median(num_original_releases_list)
    num_original_releases_min = min(num_original_releases_list)
    num_original_releases_max = max(num_original_releases_list)

    num_uclock_releases_mean = statistics.mean(num_uclock_releases_list)
    num_uclock_releases_stdev = statistics.stdev(num_uclock_releases_list)
    num_uclock_releases_median = statistics.median(num_uclock_releases_list)
    num_uclock_releases_min = min(num_uclock_releases_list)
    num_uclock_releases_max = max(num_uclock_releases_list)

    uclock_releases_rate_mean = statistics.mean(uclock_releases_rate_list)
    uclock_releases_rate_stdev = statistics.stdev(uclock_releases_rate_list)
    uclock_releases_rate_median = statistics.median(uclock_releases_rate_list)
    uclock_releases_rate_min = min(uclock_releases_rate_list)
    uclock_releases_rate_max = max(uclock_releases_rate_list)

    num_original_joins_mean = statistics.mean(num_original_joins_list)
    num_original_joins_stdev = statistics.stdev(num_original_joins_list)
    num_original_joins_median = statistics.median(num_original_joins_list)
    num_original_joins_min = min(num_original_joins_list)
    num_original_joins_max = max(num_original_joins_list)

    num_uclock_joins_mean = statistics.mean(num_uclock_joins_list)
    num_uclock_joins_stdev = statistics.stdev(num_uclock_joins_list)
    num_uclock_joins_median = statistics.median(num_uclock_joins_list)
    num_uclock_joins_min = min(num_uclock_joins_list)
    num_uclock_joins_max = max(num_uclock_joins_list)

    uclock_joins_rate_mean = statistics.mean(uclock_joins_rate_list)
    uclock_joins_rate_stdev = statistics.stdev(uclock_joins_rate_list)
    uclock_joins_rate_median = statistics.median(uclock_joins_rate_list)
    uclock_joins_rate_min = min(uclock_joins_rate_list)
    uclock_joins_rate_max = max(uclock_joins_rate_list)

    return TestAggStats(tests_stats[0].test_name,
                        tests_stats[0].test_engine,
                        tests_stats[0].test_sampling_rate,

                        duration=duration_mean,
                        duration_stdev=duration_stdev,
                        duration_median=duration_median,
                        duration_min=duration_min,
                        duration_max=duration_max,

                        num_warnings=num_warnings_mean,
                        num_warnings_stdev=num_warnings_stdev,
                        num_warnings_median=num_warnings_median,
                        num_warnings_min=num_warnings_min,
                        num_warnings_max=num_warnings_max,

                        num_original_acquires=num_original_acquires_mean,
                        num_original_acquires_stdev=num_original_acquires_stdev,
                        num_original_acquires_median=num_original_acquires_median,
                        num_original_acquires_min=num_original_acquires_min,
                        num_original_acquires_max=num_original_acquires_max,

                        num_uclock_acquires=num_uclock_acquires_mean,
                        num_uclock_acquires_stdev=num_uclock_acquires_stdev,
                        num_uclock_acquires_median=num_uclock_acquires_median,
                        num_uclock_acquires_min=num_uclock_acquires_min,
                        num_uclock_acquires_max=num_uclock_acquires_max,

                        uclock_acquires_rate=uclock_acquires_rate_mean,
                        uclock_acquires_rate_stdev=uclock_acquires_rate_stdev,
                        uclock_acquires_rate_median=uclock_acquires_rate_median,
                        uclock_acquires_rate_min=uclock_acquires_rate_min,
                        uclock_acquires_rate_max=uclock_acquires_rate_max,

                        num_original_releases=num_original_releases_mean,
                        num_original_releases_stdev=num_original_releases_stdev,
                        num_original_releases_median=num_original_releases_median,
                        num_original_releases_min=num_original_releases_min,
                        num_original_releases_max=num_original_releases_max,

                        num_uclock_releases=num_uclock_releases_mean,
                        num_uclock_releases_stdev=num_uclock_releases_stdev,
                        num_uclock_releases_median=num_uclock_releases_median,
                        num_uclock_releases_min=num_uclock_releases_min,
                        num_uclock_releases_max=num_uclock_releases_max,

                        uclock_releases_rate=uclock_releases_rate_mean,
                        uclock_releases_rate_stdev=uclock_releases_rate_stdev,
                        uclock_releases_rate_median=uclock_releases_rate_median,
                        uclock_releases_rate_min=uclock_releases_rate_min,
                        uclock_releases_rate_max=uclock_releases_rate_max,

                        num_original_joins=num_original_joins_mean,
                        num_original_joins_stdev=num_original_joins_stdev,
                        num_original_joins_median=num_original_joins_median,
                        num_original_joins_min=num_original_joins_min,
                        num_original_joins_max=num_original_joins_max,

                        num_uclock_joins=num_uclock_joins_mean,
                        num_uclock_joins_stdev=num_uclock_joins_stdev,
                        num_uclock_joins_median=num_uclock_joins_median,
                        num_uclock_joins_min=num_uclock_joins_min,
                        num_uclock_joins_max=num_uclock_joins_max,

                        uclock_joins_rate=uclock_joins_rate_mean,
                        uclock_joins_rate_stdev=uclock_joins_rate_stdev,
                        uclock_joins_rate_median=uclock_joins_rate_median,
                        uclock_joins_rate_min=uclock_joins_rate_min,
                        uclock_joins_rate_max=uclock_joins_rate_max)

def output_aggregate_stats(test_agg_stats: TestAggStats):
    with open(REPORT_FILE_PATH, "a") as f:
        writer = csv.writer(f)
        writer.writerow(test_agg_stats.as_row())

def parse_rapid_output(output: str) -> TestStats:
    lines = output.splitlines()

    num_original_acquires = 0
    num_uclock_acquires = 0
    uclock_acquires_rate = 0
    num_original_releases = 0
    num_uclock_releases = 0
    uclock_releases_rate = 0
    num_original_joins = 0
    num_uclock_joins = 0
    uclock_joins_rate = 0

    for line in lines:
        if "Number of 'racy' events" in line:
            num_warnings = int(line.split(" = ")[1])
        if "Time for analysis" in line:
            duration = int(line.split(" ")[4])

        if "Num original acquires: " in line:
            num_original_acquires = int(line.split(": ")[1])
        if "Num uclock acquires: " in line:
            num_uclock_acquires = int(line.split(": ")[1])

        if "Num original releases: " in line:
            num_original_releases = int(line.split(": ")[1])
        if "Num uclock releases: " in line:
            num_uclock_releases = int(line.split(": ")[1])

        if "Num original joins: " in line:
            num_original_joins = int(line.split(": ")[1])
        if "Num uclock joins: " in line:
            num_uclock_joins = int(line.split(": ")[1])

    if num_original_acquires != 0:
        uclock_acquires_rate = num_uclock_acquires / num_original_acquires
    if num_original_releases != 0:
        uclock_releases_rate = num_uclock_releases / num_original_releases
    if num_original_joins != 0:
        uclock_joins_rate = num_uclock_joins / num_original_joins

    return TestStats(test_name="", test_engine="", test_sampling_rate=0, duration=duration, num_warnings=num_warnings,
                     num_original_acquires=num_original_acquires,
                     num_uclock_acquires=num_uclock_acquires,
                     uclock_acquires_rate=uclock_acquires_rate,
                     num_original_releases=num_original_releases,
                     num_uclock_releases=num_uclock_releases,
                     uclock_releases_rate=uclock_releases_rate,
                     num_original_joins=num_original_joins,
                     num_uclock_joins=num_uclock_joins,
                     uclock_joins_rate=uclock_joins_rate)

def run_test(trace_path: str, engine: str, sampling_rate: float, num_iters: int):
    global DATETIME_STR, REPORT_FILE_PATH, OUTPUT_FILE_PATH
    name = trace_path.replace("/", "_")

    print("[+] Analysing", trace_path, "with", engine, "engine")

    tests_stats = []
    # num_iters = NUM_TEST_ITERS if sampling_rate != 1 else 10
    for _ in range(num_iters):
        output = subprocess.check_output(["java", "-Xmx8g", "-cp", "rapid.jar:./lib/*:./lib/jgrapht/*", engine, "-f", "std", "-p", trace_path, "-r", str(sampling_rate)])
        test_stats = parse_rapid_output(output.decode())
        test_stats.test_name = trace_path
        test_stats.test_engine = engine
        test_stats.test_sampling_rate = sampling_rate

        tests_stats.append(test_stats)
        print(f"Duration: {test_stats.duration}ms\tNum Races: {test_stats.num_warnings}")

        open(OUTPUT_FILE_PATH, "a").write(f"=== {trace_path} {engine} {sampling_rate}\n{output.decode()}\n")

    tests_agg_stats = aggregate_test_stats(tests_stats)
    output_aggregate_stats(tests_agg_stats)


def main():
    global DATETIME_STR, REPORT_FILE_PATH, OUTPUT_FILE_PATH

    if len(sys.argv) != 2:
        print(f"[!] Usage: python3 {sys.argv[0]} <config>")
        sys.exit(1)

    trace_paths = yaml.load(open(TRACES_LIST_YAML), Loader=yaml.FullLoader)
    configs = yaml.load(open(CONFIG_LIST_YAML), Loader=yaml.FullLoader)

    config_name = sys.argv[1]
    config = next((cfg for cfg in configs if cfg["name"] == config_name), None)
    if config is None:
        print(f"[!] {config_name} is not a valid config in config.yaml")
        sys.exit(1)

    DATETIME_STR = datetime.now().strftime("%d-%b-%Y-%H-%M-%S")
    REPORT_FILE_PATH = f"results/report-{DATETIME_STR}-{config_name}.csv"
    OUTPUT_FILE_PATH = os.path.expanduser(f"~/scratch/rapid/outputs/output-{DATETIME_STR}-{config_name}.txt")

    if not os.path.exists("results"):
        os.mkdir("results")

    if not os.path.exists(os.path.expanduser("~/scratch/rapid/outputs")):
        os.mkdir(os.path.expanduser("~/scratch/rapid/outputs"))

    with open(REPORT_FILE_PATH, "w") as f:
        writer = csv.writer(f)
        writer.writerow(TestAggStats.header())

    engines = config["engines"]
    sampling_rate = float(config["sampling_rate"])
    num_iters = int(config["iterations"])

    args = product(trace_paths, engines, [sampling_rate], [num_iters])
    # for trace_path in trace_paths:
    #     for sr in SAMPLING_RATES:
    #         for eng in ENGINES:
    #             run_test(trace_path, eng, sr)
                # args = (trace_path, eng, sr)

    # Somehow cpu_count() on NSCC returns 256, which may not actually be the number of cpus allocated to the job
    nprocs = int(check_output("nproc"))
    with Pool(processes=nprocs-1) as pool:
        pool.starmap(run_test, args)



if __name__ == "__main__":
    main()
