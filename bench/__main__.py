from argparse import ArgumentParser
from contextlib import contextmanager
from timeit import Timer
from diffutils.api import diff, parse_unified_diff
from diffutils.output import generate_unified_diff
from diffutils.engine import DiffEngine
from os.path import dirname
import textwrap
from sys import stderr, exit

test_data = [
    (
        "CraftServer_1710.java",  # CraftBukkit main server file 1.7.10
        "CraftServer_188.java"  # CraftBukkit main server file 1.8.8
    )
]

bench_methods = {
    "parse_diff": (
        """\
        patch = diff(original_lines, revised_lines)
        unified_diff = tuple(generate_unified_diff(
            "a/{}".format(original_name),
            "b/{}".format(revised_name),
            original_lines,
            patch
        ))
        """,
        """\
        parse_unified_diff(unified_diff)
        """
    ),
    "output_diff": (
        """\
        patch = diff(original_lines, revised_lines)
        """,
        """\
        # NOTE: Must use list to consume the generator's output
        list(generate_unified_diff(
            "a/{}".format(original_name),
            "b/{}".format(revised_name),
            original_lines,
            patch
        ))
        """
    ),
    "diff": (
        "pass",
        """\
        engine.diff(original_lines, revised_lines)
        """
    ),
    "patch": (
        """\
        patch = diff(original_lines, revised_lines)
        """,
        """\
        patch.apply_to(original_lines)
        """
    )
}
__cached_test_data_lines = {}


def test_data_lines(name, data_dir="data"):
    cache = __cached_test_data_lines
    try:
        return cache[name]
    except KeyError:
        result = []
        with open("{}/{}".format(data_dir, name), "rt") as f:
            for line in f:
                result.append(line.rstrip("\r\n"))
        cache[name] = result
        return result


def main():
    parser = ArgumentParser(description="Benchmarks DiffUtils")
    available_targets = frozenset(bench_methods.keys())
    parser.add_argument('targets', nargs='+', choices=[*available_targets, "all"], help="The items to benchmark")
    parser.add_argument('--iterations', '-i', default=10, help="The number of benchmark iterations to perform on each")
    parser.add_argument('--repeat', '-r', default=3, help="The number of times to repeat the benchmark")
    parser.add_argument('--data-dir', dest='data_dir', default="{}/data".format(dirname(__file__)), help="The location of the benchmarking data")
    args = parser.parse_args()
    iterations = args.iterations
    repeat = args.repeat
    targets = args.targets
    data_dir = args.data_dir
    if 'all' in targets:
        if len(targets) > 1:
            print("When the 'all' target is specfied, no other targets may be specified", file=stderr)
            exit(1)
        targets = available_targets
    max_target_length = max(len(target) for target in targets)
    for target in sorted(targets):
        padded_target = target.ljust(max_target_length)
        for (original_name, revised_name) in test_data:
            original_lines = test_data_lines(original_name, data_dir=data_dir)
            revised_lines = test_data_lines(revised_name, data_dir=data_dir)
            setup_code, bench_code = bench_methods[target]
            setup_code = textwrap.dedent(setup_code)
            bench_code = textwrap.dedent(bench_code)
            if target == 'diff':
                engines = DiffEngine.available_engines()
            else:
                engines = None
            bench_env = dict(globals())
            for local_param in ("original_name", "revised_name", "original_lines", "revised_lines"):
                existing_value = bench_env.get(local_param)
                if existing_value is not None:
                    raise AssertionError("{} already present: {}".format(local_param, repr(existing_value)))
                bench_env[local_param] = locals()[local_param]

            def run_bench(bench_env, engine_name=None):
                timer = Timer(setup=setup_code, stmt=bench_code, globals=bench_env)
                try:
                    result = min(timer.repeat(repeat=repeat, number=iterations))
                except Exception:
                    message = "Unable to run {} between {} and {}".format(target, original_name, revised_name)
                    if engine_name:
                        message += " with {}".format(engine_name)
                    print(message, file=stderr)
                    timer.print_exc()
                    exit(1)
                result *= 1000
                message = "{}  {:.3f} ms -- {} and {}".format(padded_target, result, original_name, revised_name)
                if engine_name:
                    message += " with {}".format(engine_name)
                print(message)

            assert 'engine' not in bench_env, "engine already present: " + repr(bench_env['engine'])
            if engines is not None:
                for engine in DiffEngine.available_engines():
                    bench_env['engine'] = engine
                    run_bench(bench_env, engine_name=repr(engine))
            else:
                run_bench(bench_env)


if __name__ == "__main__":
    main()
