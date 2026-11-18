"""Repeatable, headless timings: python -m raetselkalender.benchmark."""
import argparse
import json
import platform
import statistics
import time

from raetselkalender.catalog import CATALOG, generate


def main():
    parser = argparse.ArgumentParser(description='Generierungszeiten auf diesem Rechner messen')
    parser.add_argument('--type', action='append', choices=[p.id for p in CATALOG])
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--difficulty', choices=('mittel', 'schwer'), default='schwer')
    parser.add_argument('--repeat', type=int, default=3)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat muss mindestens 1 sein')
    cases = []
    for kind in args.type or [p.id for p in CATALOG if p.available]:
        durations = []
        for _ in range(args.repeat):
            start = time.perf_counter()
            puzzle = generate(kind, args.seed, args.difficulty)
            durations.append(time.perf_counter()-start)
        cases.append(dict(type=kind, median_seconds=statistics.median(durations),
                          runs_seconds=durations, unique=puzzle.analysis['unique'],
                          logical_solvable=puzzle.analysis.get('logical_solvable', False),
                          optimality_verified=puzzle.analysis.get('optimality_verified', False),
                          engine_verified=puzzle.analysis.get('engine_verified',False)))
    print(json.dumps(dict(python=platform.python_version(), platform=platform.system(),
                          seed=args.seed, difficulty=args.difficulty, repeat=args.repeat,
                          total_median_seconds=sum(c['median_seconds'] for c in cases), cases=cases),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
