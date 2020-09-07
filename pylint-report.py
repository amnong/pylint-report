#!/usr/bin/env python3

import sys
import subprocess
import re
import time
from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path


IGNORED_DIRS = (
    '__pycache__',
)


def main():
    parser = ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('-e', '--exclude', action='append', metavar='PATH',
                        help='Exclude this path (can be specified multiple times)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Do not show progress information')
    args = parser.parse_args()
    run(args)


def walk(path, excludes=None):
    path = Path(path)
    if not path.is_dir():
        if path.name.endswith('.py'):
            yield path
        return
    for p in sorted(Path(path).iterdir(), key=lambda _p: (_p.is_dir(), str(_p))):
        if p.is_dir():
            if p.name in IGNORED_DIRS:
                continue
        yield from walk(p)


def run(args):
    num_files_with_no_errors, num_total_files = 0, 0
    files = defaultdict(lambda: 0)
    errors = defaultdict(lambda: 0)
    messages = {}

    file_paths = []
    for path in walk(args.target):
        if any(str(path).startswith(exclude) for exclude in args.exclude or ()):
            continue
        file_paths.append(path)

    print('Linting {} files...'.format(len(file_paths)))

    for n, path in enumerate(file_paths, 1):
        if not args.quiet:
            print('{:>3}% '.format(n * 100 // len(file_paths)), '{} '.format(path).ljust(79, '.'), end='')
            sys.stdout.flush()
            sys.stdout.write(' ')
        num_total_files += 1
        filename = str(path)
        found_errors = False
        pylint_problem = False
        start_time = time.time()
        p = subprocess.Popen('pylint -f parseable {}'.format(path), shell=True, universal_newlines=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in iter(p.stdout.readline, ''):
            match = re.match(r'(?P<file>.+):\d+: \[(?P<code>.\d+)\((?P<message>.+)\), .+\] (?P<description>.+)', line)
            if not match:
                continue
            found_errors = True
            files[filename] += 1
            errors[match.group('code')] += 1
            messages[match.group('code')] = '{:<34}{}'.format(match.group('message'), match.group('description'))
        if p.stderr.read().strip():
            pylint_problem = True
        if not found_errors:
            num_files_with_no_errors += 1
        if not args.quiet:
            print('DONE in {:.01g} seconds{}'.format(
                round(time.time() - start_time, 1),
                ' (pylint error occurred)' if pylint_problem else '',
                ))

    if files:
        print('\nTop files:')
        for file, num_errors in sorted(files.items(), key=lambda item: -item[1]):
            print('', num_errors, file, sep='\t')
    if num_files_with_no_errors:
        if files:
            print()
        print(num_files_with_no_errors, 'out of', num_total_files, 'files are clean.')

    if errors:
        print('\nTop errors:')
        for code, num_occurrences in sorted(errors.items(), key=lambda item: -item[1]):
            print('', num_occurrences, code, messages[code], sep='\t')


if __name__ == '__main__':
    sys.exit(main())
