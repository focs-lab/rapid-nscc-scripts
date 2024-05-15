import os
import subprocess
import sys
import yaml
import csv
import statistics

from dataclasses import dataclass
from typing import List
from datetime import datetime

from multiprocessing import Pool, cpu_count
from itertools import product


TRACES_LIST_YAML = "traces.yaml"
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
            "num_warnings_max"
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
                self.num_warnings_max
            ]
        )

# aggregates the stats after running a test case N times
def aggregate_test_stats(tests_stats: List[TestStats]):
    duration_list = list(map(lambda ts: ts.duration, tests_stats))
    num_warnings_list = list(map(lambda ts: ts.num_warnings, tests_stats))

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
                        num_warnings_max=num_warnings_max)

def output_aggregate_stats(test_agg_stats: TestAggStats):
    with open(REPORT_FILE_PATH, "a") as f:
        writer = csv.writer(f)
        writer.writerow(test_agg_stats.as_row())

def parse_rapid_output(output: str) -> TestStats:
    lines = output.splitlines()

    for line in lines:
        if "Number of 'racy' events" in line:
            num_warnings = int(line.split(" = ")[1])
        if "Time for analysis" in line:
            duration = int(line.split(" ")[4])

    return TestStats(test_name="", test_engine="", test_sampling_rate=0, duration=duration, num_warnings=num_warnings)

def run_test(trace_path: str, engine: str, sampling_rate: float):
    global DATETIME_STR, REPORT_FILE_PATH, OUTPUT_FILE_PATH
    name = trace_path.replace("/", "_")

    print("[+] Analysing", trace_path, "with", engine, "engine")

    tests_stats = []
    num_iters = NUM_TEST_ITERS if sampling_rate != 1 else 10
    for _ in range(num_iters):
        output = subprocess.check_output(["java", "-cp", "rapid.jar:./lib/*:./lib/jgrapht/*", engine, "-f", "std", "-p", trace_path, "-r", str(sampling_rate)])
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

    DATETIME_STR = datetime.now().strftime("%d-%b-%Y-%H-%M-%S")
    REPORT_FILE_PATH = f"report-{DATETIME_STR}.csv"
    OUTPUT_FILE_PATH = f"output-{DATETIME_STR}.txt"

    if os.path.exists(REPORT_FILE_PATH):
        os.unlink(REPORT_FILE_PATH)
    with open(REPORT_FILE_PATH, "w") as f:
        writer = csv.writer(f)
        writer.writerow(TestAggStats.header())

    trace_paths = yaml.load(open(TRACES_LIST_YAML), Loader=yaml.FullLoader)
    args = product(trace_paths, ENGINES, SAMPLING_RATES)
    # for trace_path in trace_paths:
    #     for sr in SAMPLING_RATES:
    #         for eng in ENGINES:
    #             run_test(trace_path, eng, sr)
                # args = (trace_path, eng, sr)

    # cpu_count() on NSCC returns 256, which may not actually be the number of cpus allocated to the job
    # now it is hardcoded to 63 for simplicity
    with Pool(processes=63) as pool:
        pool.starmap(run_test, args)



if __name__ == "__main__":
    main()
