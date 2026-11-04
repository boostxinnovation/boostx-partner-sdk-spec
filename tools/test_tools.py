import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import check_vectors  # noqa: E402


def quiet_check_vectors(vec):
    """Runs check_vectors.main on vec without printing its FAIL lines; returns (exit code, output)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_vectors.main([vec])
    return code, out.getvalue()


def edited_vectors(tmp, edit):
    """Copies the vectors into tmp, applies edit(keys.json data) and returns the copy's path."""
    vec = os.path.join(tmp, 'vectors')
    shutil.copytree(os.path.join(ROOT, 'vectors'), vec)
    path = os.path.join(vec, 'keys.json')
    data = json.load(open(path, encoding='utf-8'))
    edit(data)
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return vec


SKIPPABLE = [
        'gidgp-gamepass-amount-string',
        'gidgp-gamepass-bet-number',
        'gidgp-gamepass-currency-number',
        'gidgp-gamepass-demo-number',
        'gidgp-gamepass-demo-string',
        'gidgp-gamepass-event-title-number',
        'gidgp-gamepass-order-demo-type-before-ill-formed-id',
        'gidgp-gamepass-order-event-title-type-before-demo-type',
        'gidgp-gamepass-order-id-type-before-ill-formed-id',
        'gidgp-gamepass-order-id-type-before-later-presence',
        'gidgp-gamepass-order-key-before-null-params',
        'gidgp-gamepass-order-xdecimals-before-event-title-type',
        'gidgp-gamepass-params-left-out',
        'gidgp-gamepass-params-not-object',
        'gidgp-gamepass-params-null',
        'gidgp-gamepass-x-string',
        'gidgp-gamepass-xdecimals-fraction',
        'gidgp-gamepass-xdecimals-nan',
        'gidgp-gamepass-xdecimals-string',
        'gidgp-gamepass-xmin-string',
        'gidgp-gid-build-bet-number',
        'gidgp-gid-build-bet-number-zero',
        'gidgp-gid-build-order-type-before-later-presence',
        'gidgp-gid-build-order-type-before-well-formedness',
        'gidgp-gid-build-user-boolean',
        'gidgp-x-floor-decimals-fraction',
        'http-check-bet-verdict-null',
        'http-check-bet-verdict-number',
        'http-check-bet-verdict-string',
        'keys-private-number-refused',
        'keys-window-nan',
        'settle-client-timeout-infinity',
        'settle-client-timeout-nan',
        'settle-create-amount-string',
        'settle-create-bet-number',
        'settle-create-currency-number',
        'settle-create-params-null',
        'settle-create-partner-number',
        'settle-create-settled-at-fraction',
        'settle-create-settled-at-nan',
        'settle-create-settled-at-string',
        'settle-create-status-number',
        'settle-create-user-boolean',
        'settle-create-version-fraction',
        'settle-create-version-infinity',
        'settle-create-version-nan',
        'settle-create-version-string',
        'settle-create-xsettle-string',
        'verifykeys-create-response-nonce-above-max',
        'verifykeys-create-response-nonce-fraction',
        'verifykeys-create-response-nonce-nan',
        'verifykeys-create-response-nonce-string',
        'verifykeys-request-window-infinity',
        'verifykeys-request-window-nan',
        'verifykeys-request-window-negative-infinity',
]


class ToolsTest(unittest.TestCase):
    def test_check_vectors_passes_on_repo(self):
        self.assertEqual(quiet_check_vectors(os.path.join(ROOT, 'vectors'))[0], 0)

    def test_check_vectors_rejects_duplicate_name(self):
        def edit(d):
            d['cases'][1]['name'] = d['cases'][0]['name']
        with tempfile.TemporaryDirectory() as tmp:
            code, out = quiet_check_vectors(edited_vectors(tmp, edit))
        self.assertEqual(code, 1)
        self.assertIn('used 2 times', out)

    def test_check_vectors_rejects_bad_shapes(self):
        for edit, want in (
            (lambda d: d.update(cases={}), 'keys.json: must be'),
            (lambda d: d['cases'].append([]), 'is not an object'),
            (lambda d: d['cases'][0].update(name=['keys-x']), 'case name #0'),
            (lambda d: d['cases'][0].update(needs=['untyped-string', 'untyped-string']), 'distinct known tags'),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                code, out = quiet_check_vectors(edited_vectors(tmp, edit))
            self.assertEqual(code, 1, want)
            self.assertIn(want, out)

    def test_check_marks_defaults_to_repo_layout(self):
        r = subprocess.run(
            [sys.executable, '-B', os.path.join(HERE, 'check_marks.py')],
            cwd=tempfile.gettempdir(), capture_output=True, text=True,
        )
        self.assertNotIn('Traceback', r.stderr)
        self.assertIn('anchors', r.stdout)

    def test_catalogue_covers_ops(self):
        script = os.path.join(HERE, 'check_marks.py')
        r = subprocess.run([sys.executable, '-B', script, '--catalogue'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            spec = os.path.join(tmp, 'SPEC.md')
            text = open(os.path.join(ROOT, 'SPEC.md'), encoding='utf-8').read()
            open(spec, 'w', encoding='utf-8').write(text.replace('\n#### x.floor\n', '\n#### x.floorless\n'))
            r = subprocess.run(
                [sys.executable, '-B', script, '--catalogue', spec, os.path.join(ROOT, 'vectors')],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn('operation x.floor has no "#### x.floor" entry', r.stdout)

    def _marks(self, flag, edit=None):
        """Runs check_marks.py with flag, on the repo spec or on a copy changed by edit(text)."""
        args = [sys.executable, '-B', os.path.join(HERE, 'check_marks.py'), flag]
        with tempfile.TemporaryDirectory() as tmp:
            if edit:
                spec = os.path.join(tmp, 'SPEC.md')
                text = open(os.path.join(ROOT, 'SPEC.md'), encoding='utf-8').read()
                open(spec, 'w', encoding='utf-8').write(edit(text))
                args += [spec, os.path.join(ROOT, 'vectors')]
            return subprocess.run(args, capture_output=True, text=True)

    def test_docs_pointers_carry_no_rule(self):
        r = self._marks('--docs-pointers')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for pointer in ('the partner docs', 'the docs', '`rounds.md`'):
            r = self._marks('--docs-pointers', lambda t: t + f'\nAn SDK MUST do this, as {pointer} say.\n')
            self.assertEqual(r.returncode, 1, pointer + '\n' + r.stdout + r.stderr)
            self.assertIn('docs pointer', r.stdout)
        r = self._marks('--docs-pointers', lambda t: t + '\nThe partner docs say this too.\n\nAn SDK MUST do it.\n')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_platform_notes_cite_real_cases(self):
        r = self._marks('--platform-notes')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self._marks('--platform-notes', lambda t: t + '\n- **Python.** See `keys-no-such-case`.\n')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('keys-no-such-case', r.stdout)
        r = self._marks('--platform-notes', lambda t: t + '\n- **Python.** A note citing nothing.\n')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('cites no vector case', r.stdout)
        r = self._marks('--platform-notes', lambda t: t.replace('\n## 14. Platform notes', '\n## 14. Notes'))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('section 14', r.stdout)

    def test_agents_lists_unvectored_rules(self):
        script = os.path.join(HERE, 'check_marks.py')
        r = subprocess.run([sys.executable, '-B', script, '--agents'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        agents = open(os.path.join(ROOT, 'AGENTS.md'), encoding='utf-8').read()
        head = '## Rules no vector covers\n'
        for edit, want in (
            (lambda t: re.sub(r'^- \[KEYS-68\].*\n', '', t, flags=re.M), 'KEYS-68'),
            (lambda t: t.replace(head, head + '\n- [KEYS-29](SPEC.md#keys-29): the signature.\n'), 'KEYS-29'),
            (lambda t: t.replace(head, head + '\n- [SETTLE-24](SPEC.md#settle-24): informative.\n'), 'SETTLE-24'),
            (lambda t: t.replace('(SPEC.md#keys-68)', '(SPEC.md#keys-69)'), 'KEYS-68'),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                shutil.copy(os.path.join(ROOT, 'SPEC.md'), tmp)
                open(os.path.join(tmp, 'AGENTS.md'), 'w', encoding='utf-8').write(edit(agents))
                r = subprocess.run(
                    [sys.executable, '-B', script, '--agents', os.path.join(tmp, 'SPEC.md'), os.path.join(ROOT, 'vectors')],
                    capture_output=True, text=True,
                )
            self.assertEqual(r.returncode, 1, want + '\n' + r.stdout + r.stderr)
            self.assertIn(want, r.stdout)

    def test_new_flags_leave_default_unchanged(self):
        default = subprocess.run(
            [sys.executable, '-B', os.path.join(HERE, 'check_marks.py')], capture_output=True, text=True
        )
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        r = self._marks('--catalogue', lambda t: t + '\nAn SDK MUST do this, as the partner docs say.\n')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_gid_signature_canonical_bytes(self):
        d = json.load(open(os.path.join(ROOT, 'vectors', 'golden', 'gid-signature.json'), encoding='utf-8'))
        g = d['gid']
        text = json.dumps(
            {'partner': g['partner'], 'user': g['user'], 'bet': g['bet']}, ensure_ascii=False, separators=(',', ':')
        )
        b = text.encode('utf-8')
        self.assertEqual(b, bytes.fromhex(d['canonicalHex']))
        self.assertEqual(len(b), 72)

    def test_needs_vocabulary(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = quiet_check_vectors(edited_vectors(tmp, lambda d: d['cases'][0].update(needs=['frobnicate'])))
        self.assertEqual(code, 1)
        self.assertIn('distinct known tags', out)

    def test_needs_tagged_set(self):
        # The cases carrying at least one tag of the six-tag set (every tag but ill-formed-string) are the 55 a
        # Go-like runner skips; a case may carry ill-formed-string beside such a tag.
        tagged = []
        for g in check_vectors.GROUP_FILES:
            for c in json.load(open(os.path.join(ROOT, 'vectors', g + '.json'), encoding='utf-8'))['cases']:
                if set(c.get('needs', [])) - {'ill-formed-string'}:
                    tagged.append(c['name'])
        self.assertEqual(sorted(tagged), SKIPPABLE)

    def test_ill_formed_tag_matches_input(self):
        for edit in (
            lambda d: d['cases'][0]['input'].update(partner={'$illFormed': 'a'}),
            lambda d: next(c for c in d['cases'] if c['name'] == 'keys-build-gid-ill-formed-id').pop('needs'),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                code, out = quiet_check_vectors(edited_vectors(tmp, edit))
            self.assertEqual(code, 1)
            self.assertIn('ill-formed-string exactly when', out)

    def test_u0001_case_present(self):
        cases = json.load(open(os.path.join(ROOT, 'vectors', 'gidgp.json'), encoding='utf-8'))['cases']
        c = next(c for c in cases if c['name'] == 'gidgp-gid-build-control-u0001')
        self.assertIn('\x01', c['input']['bet'])
        self.assertIn('\\u0001', c['want']['ok']['canonical'])


if __name__ == '__main__':
    unittest.main()
