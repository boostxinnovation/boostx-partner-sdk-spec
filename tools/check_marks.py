"""Checks the SDK spec's vector marks, anchors, links and 12.3 counts against the vector files.

Usage: python3 check_marks.py [--catalogue] [--docs-pointers] [--platform-notes] [--agents] [spec.md] [vectors-dir]
--catalogue       also require a `#### <op>` entry in section 3 for every operation a vector case uses.
--docs-pointers   also require that no paragraph pointing at the partner docs holds MUST, SHOULD or MAY.
--platform-notes  also require section 14, every case name it cites in backticks to exist, and every note
                  (a top-level list item) to cite at least one.
--agents          also require the "Rules no vector covers" list of AGENTS.md (next to spec.md) to name exactly the
                  normative rule ids whose mark reads "(No vector" or "none", each linked to its own anchor.
Exit 0 when every check passes; each failure is printed on its own line.
"""

import collections
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + os.sep
FLAGS = ('--catalogue', '--docs-pointers', '--platform-notes', '--agents')
ARGS = [a for a in sys.argv[1:] if a not in FLAGS]
CATALOGUE, DOCS_POINTERS, PLATFORM_NOTES, AGENTS = (f in sys.argv[1:] for f in FLAGS)
SPEC = ARGS[0] if ARGS else ROOT + 'SPEC.md'
VEC = ARGS[1] if len(ARGS) > 1 else ROOT + 'vectors'
GROUP_FILES = ['keys.json', 'gidgp.json', 'inbound.json', 'settle.json', 'verifykeys.json', 'http.json']
RULE_ID = re.compile(r'^(KEYS|GID|GAMEPASS|INBOUND|SETTLE|VERIFYKEYS|HTTP)-\d+$')
# A mark that names a group file in which no case cites the rule must say how the rule is pinned there instead.
INDIRECT = re.compile(r'\b(indirectly|pinned (by|under)|through|every accepted|every file|the two files themselves)\b')

text = open(SPEC, encoding='utf-8').read()
lines = text.split('\n')
failures = []
fail = failures.append

# Anchors: unique, and every intra-document link resolves.
anchors = collections.Counter(re.findall(r'<a id="([^"]+)"></a>', text))
for a, n in anchors.items():
    if n > 1:
        fail(f'anchor #{a} defined {n} times')
for target in sorted(set(re.findall(r'\]\(#([^)\s]+)\)', text))):
    if target not in anchors:
        fail(f'link #{target} has no anchor')

# Rule paragraphs: from a line opening with an anchor to the next such line or heading. A mark belongs to every
# anchor of the paragraph it ends.
blocks = []  # (ids, body lines, line number, heading)
informative = set()  # anchors of paragraphs that state no requirement
cur = None
heading = ''
for i, line in enumerate(lines, 1):
    m = re.match(r'^((?:<a id="[^"]+"></a>)+)(?:\*\*|$)', line)
    if line.startswith('#'):
        heading = line
    if m or line.startswith('#'):
        if cur:
            blocks.append(cur)
        cur = (re.findall(r'<a id="([^"]+)"', m.group(1)), [line], i) if m else None
    elif cur:
        cur[1].append(line)
    if m:
        cur = cur + (heading,)
if cur:
    blocks.append(cur)
# A paragraph under an informative heading is informative unless it states a requirement itself.
for ids, body, ln, *h in blocks:
    if h and 'informative' in h[0] and not re.search(r'\b(MUST|SHOULD|MAY)\b', ' '.join(body)):
        informative.update(ids)

mark_of = {}  # anchor -> (files named, mark text, line)
for ids, body, ln, *_ in blocks:
    joined = ' '.join(' '.join(body).split())
    marks = re.findall(r'\(Vectors:(.*?)\)(?=\s|$)', joined)
    files = set()
    for mk in marks:
        files |= set(re.findall(r'([a-z-]+\.json)', mk))
    other = re.search(r'\((No vector|Informative)', joined)
    for a in ids:
        mark_of[a] = (files, ' | '.join(marks), ln)
        if other and not marks:
            mark_of[a] = (files, other.group(0), ln)
            if other.group(1) == 'Informative':
                informative.add(a)

# Cases: unique names, every cited id resolves to exactly one anchor.
citing = collections.defaultdict(set)  # anchor -> files whose cases cite it
counts = {}
names = collections.Counter()
ops = set()
for f in GROUP_FILES:
    cases = json.load(open(os.path.join(VEC, f), encoding='utf-8'))['cases']
    counts[f] = len(cases)
    for c in cases:
        names[c['name']] += 1
        ops.add(c['op'])
        if not c.get('rules'):
            fail(f'{f}: case {c["name"]} cites no rule')
        for r in c['rules']:
            if anchors.get(r.lower(), 0) != 1:
                fail(f'{f}: case {c["name"]} cites {r}, which has {anchors.get(r.lower(), 0)} anchors')
            citing[r.lower()].add(f)
for n, k in names.items():
    if k > 1:
        fail(f'case name {n} used {k} times')

# Marks against citing files.
for a in sorted(anchors):
    if not RULE_ID.match(a.upper()):
        continue
    files, mk, ln = mark_of.get(a, (set(), '', 0))
    missing = citing[a] - files
    if missing:
        fail(f'{a.upper()} (line {ln}): cited in {", ".join(sorted(missing))}, not named in its mark ({mk.strip() or "no mark"})')
seen = set()
for ids, body, ln, *_ in blocks:
    files, mk, _ = mark_of[ids[0]]
    group_files = files & set(GROUP_FILES)
    if not group_files or ln in seen:
        continue
    seen.add(ln)
    uncited = group_files - set().union(*(citing[a] for a in ids))
    if uncited and not INDIRECT.search(mk):
        fail(f'{ids[0].upper()} (line {ln}): mark names {", ".join(sorted(uncited))}, where no case cites it, and says nothing indirect ({mk.strip()})')

# Section 3 catalogue: one `#### <op>` entry per operation the vectors use.
if CATALOGUE:
    m = re.search(r'^## 3\..*?(?=^## 4\.)', text, re.M | re.S)
    entries = set(re.findall(r'^#### ([\w.]+)$', m.group(0) if m else '', re.M))
    for op in sorted(ops - entries):
        fail(f'operation {op} has no "#### {op}" entry in section 3')

# Docs pointers: the partner docs sit behind a login, so a paragraph that points at them states no rule.
DOCS = re.compile(r'(?i:partner docs|\bthe docs\b)|\b[a-z][a-z-]*\.md\b')
if DOCS_POINTERS:
    for m in re.finditer(r'(?:^[ \t]*\S.*(?:\n|$))+', text, re.M):
        word, ptr = re.search(r'\b(MUST|SHOULD|MAY)\b', m.group(0)), DOCS.search(m.group(0))
        if word and ptr:
            line = text.count('\n', 0, m.start()) + 1
            fail(f'docs pointer in a normative paragraph (line {line}, {ptr.group(0)!r} with {word.group(1)})')

# Section 14: platform notes cite vector cases that exist, every note at least one.
CASE = re.compile(r'^(keys|gidgp|inbound|settle|verifykeys|http)-[a-z0-9-]+$')
if PLATFORM_NOTES:
    m = re.search(r'^## 14\. Platform notes.*?(?=^## |\Z)', text, re.M | re.S)
    if not m:
        fail('section 14 "Platform notes" is missing')
    else:
        cited = {c for c in re.findall(r'`([^`\n]+)`', m.group(0)) if CASE.match(c)}
        for c in sorted(cited - set(names)):
            fail(f'section 14 cites `{c}`, which is no vector case')
        for item in re.findall(r'^- .*(?:\n {2,}\S.*)*', m.group(0), re.M):
            if not any(CASE.match(c) for c in re.findall(r'`([^`\n]+)`', item)):
                fail(f'section 14 note cites no vector case: {item[:70]!r}')

# AGENTS.md: its list of rules no vector covers matches the marks.
if AGENTS:
    agents = open(os.path.join(os.path.dirname(SPEC), 'AGENTS.md'), encoding='utf-8').read()
    m = re.search(r'^## Rules no vector covers\n.*?(?=^## |\Z)', agents, re.M | re.S)
    listed = set()
    for rid, anchor in re.findall(r'^- \[([A-Z]+-\d+)\]\(SPEC\.md#([^)]+)\)', m.group(0) if m else '', re.M):
        listed.add(rid)
        if anchor != rid.lower():
            fail(f'AGENTS.md links {rid} to #{anchor}')
    unvectored = {a.upper() for a in anchors if RULE_ID.match(a.upper()) and a not in informative
                  and re.match(r'\(No vector|none\b', mark_of.get(a, (0, ''))[1].strip())}
    for rid in sorted(unvectored - listed):
        fail(f'AGENTS.md "Rules no vector covers" leaves out {rid}')
    for rid in sorted(listed - unvectored):
        fail(f'AGENTS.md "Rules no vector covers" lists {rid}, which has a vector or is informative')

# Section 12.3 counts.
for f in GROUP_FILES:
    m = re.search(r'^\| `' + re.escape(f) + r'` \| (\d+) \|', text, re.M)
    if not m:
        fail(f'12.3 has no row for {f}')
    elif int(m.group(1)) != counts[f]:
        fail(f'12.3 says {f} has {m.group(1)} cases, the file has {counts[f]}')

rules = [a for a in anchors if RULE_ID.match(a.upper())]
unmarked = sorted(a.upper() for a in rules if not mark_of.get(a, (0, ''))[1] and a not in informative)
cited = [a for a in citing if citing[a]]
print(f'{len(anchors)} anchors ({len(rules)} rule ids, {len([a for a in rules if a in informative])} informative), '
      f'{sum(counts.values())} cases ({", ".join(f"{f} {n}" for f, n in counts.items())}), {len(cited)} distinct cited ids')
print(f'normative rule ids with no vector mark at all: {len(unmarked)}' + (f' ({", ".join(unmarked)})' if unmarked else ''))
for a in sorted(a for a in cited if a in informative):
    fail(f'{a.upper()} is informative but cited by cases in {", ".join(sorted(citing[a]))}')
for x in failures:
    print('FAIL', x)
print('OK' if not failures else f'{len(failures)} failures')
sys.exit(1 if failures else 0)
