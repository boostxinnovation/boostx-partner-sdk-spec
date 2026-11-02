"""Checks the shape of the conformance vector files (FORMAT.md section 1).

Usage: python3 check_vectors.py [vectors-dir]
Exit 0 when every check passes; each failure is printed on its own line.
"""

import collections
import json
import os
import re
import sys

GROUP_FILES = ['keys', 'gidgp', 'inbound', 'settle', 'verifykeys', 'http']
REQUIRED = {'name', 'rules', 'op', 'input', 'want'}
ALLOWED = REQUIRED | {'needs', 'sigs', 'wantZeroValue', 'note'}
NEEDS = {
    'untyped-string', 'untyped-number', 'fixed-int', 'non-finite', 'missing-params', 'untyped-bool',
    'ill-formed-string',
}
NAME = re.compile(r'^[a-z0-9-]+$')


def uses_ill_formed(o):
    """Whether a JSON value holds a {"$illFormed": ...} input (FORMAT.md section 4)."""
    if isinstance(o, dict):
        return '$illFormed' in o or any(uses_ill_formed(v) for v in o.values())
    return isinstance(o, list) and any(uses_ill_formed(v) for v in o)


def main(argv):
    vec = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vectors')
    failures = []
    names = collections.Counter()
    for g in GROUP_FILES:
        f = g + '.json'
        data = json.load(open(os.path.join(vec, f), encoding='utf-8'))
        if not isinstance(data, dict) or set(data) != {'group', 'cases'} or data['group'] != g \
                or not isinstance(data['cases'], list):
            failures.append(f'{f}: must be {{"group": "{g}", "cases": [...]}}')
            continue
        for i, c in enumerate(data['cases']):
            if not isinstance(c, dict):
                failures.append(f'{f}: case {i} is not an object')
                continue
            n = c.get('name', '?')
            if isinstance(n, str):
                names[n] += 1
            else:
                n = f'#{i}'
            if not REQUIRED <= set(c):
                failures.append(f'{f}: case {n} lacks {", ".join(sorted(REQUIRED - set(c)))}')
            if set(c) - ALLOWED:
                failures.append(f'{f}: case {n} has unknown members {", ".join(sorted(set(c) - ALLOWED))}')
            if 'needs' in c and not (
                isinstance(c['needs'], list) and c['needs'] and all(isinstance(t, str) and t in NEEDS for t in c['needs'])
                and len(set(c['needs'])) == len(c['needs'])
            ):
                failures.append(f'{f}: case {n} has a needs that is not a non-empty list of distinct known tags')
            elif uses_ill_formed(c.get('input')) != ('ill-formed-string' in c.get('needs', [])):
                failures.append(f'{f}: case {n} must carry the needs tag ill-formed-string exactly when its input '
                                'uses $illFormed')
            if not (isinstance(n, str) and NAME.match(n) and n.startswith(g + '-')):
                failures.append(f'{f}: case name {n} is not lowercase and prefixed "{g}-"')
    failures += [f'case name {n} used {k} times' for n, k in names.items() if k > 1]
    for x in failures:
        print('FAIL', x)
    print('OK' if not failures else f'{len(failures)} failures')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
