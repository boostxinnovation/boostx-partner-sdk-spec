# Generating a BoostX partner SDK

You are writing a BoostX partner SDK in your user's language from this repository alone. [SPEC.md](SPEC.md) defines
what the SDK does; [`vectors/`](vectors/) is the same definition as test cases. Follow the steps below in order, and
cite rule ids (`KEYS-12`, linked as `SPEC.md#keys-12`) and case names when you record a decision or a question.

## Reading order

SPEC.md is large: read it section by section, never as one block.

1. SPEC.md sections 1 to 4: the purpose and the integration overview (1.6), the principles every group applies (2),
   the operation catalogue you implement (3), and the error taxonomy (4).
2. [`vectors/FORMAT.md`](vectors/FORMAT.md), whole. Make the decisions of its section "Bringing up a new language"
   before you write the runner.
3. SPEC.md section 14, the platform notes, for your language, before you choose libraries.
4. Each group's section, in this order. This is reading only: you implement in the build order below.

   | Group | SPEC.md | Vector file |
   |-------|---------|-------------|
   | keys | 5 | `vectors/keys.json` |
   | gidgp | 6 and 7 | `vectors/gidgp.json` |
   | inbound | 8 | `vectors/inbound.json` |
   | verifykeys | 10 | `vectors/verifykeys.json` |
   | settle | 9 | `vectors/settle.json` |
   | http | 11 | `vectors/http.json` |

5. SPEC.md section 13, the decisions. Each wins over any rule text that disagrees with it.

## Build order

Build from the bottom up; each layer uses the ones before it. Each step names the vector operations it provides.

1. Canonical unpadded base64url ([P-base64url](SPEC.md#p-base64url)), strict UTF-8 with no byte order mark
   ([P-utf8](SPEC.md#p-utf8)), and the JSON reader: exact member names, the last repeated member wins, a scan for
   lone-surrogate escapes, and acceptance of every text nested up to 64 levels deep; a depth limit of your own above
   that is optional ([P-names](SPEC.md#p-names), [P-duplicates](SPEC.md#p-duplicates),
   [P-surrogates](SPEC.md#p-surrogates), [P-one-value](SPEC.md#p-one-value)).
2. PEM and DER key loading and key usability (5.1, 5.2): `key.loadPrivate`, `key.loadPublic`.
3. JWS: emitted tokens, inbound segments and header, payload JSON, time claims, key stores (5.3 to 5.7):
   `keystore.register`.
4. The signed GID: canonical bytes, signing, verification (6): `gid.build`.
5. The builders: gamepass and the X helpers (7), settlement (9.1 to 9.3), verify-keys request and response (10.8):
   `gamepass.create`, `x.floor`, `x.player`, `settlement.create`, `verifykeys.createRequest`,
   `verifykeys.createResponse`.
6. Extraction and parsing: Booster and CheckBet (8), verify-keys (10): `booster.extract`, `booster.parse`,
   `checkbet.extract`, `checkbet.parse`, `verifykeys.extractRequest`, `verifykeys.parseRequest`,
   `verifykeys.parseResponse`.
7. The handlers: one router serving the three endpoints (11): `http.serve`.
8. The settlement client, last (9.4 to 9.8): `client.submit`.

After each step, run every case whose `op` that step provides, in whichever file it sits: a case sits in the file of
the group it was written for, whatever operation it calls (FORMAT.md, introduction), so every file mixes layers. Step 1
has no operation of its own; the later steps' cases exercise it. All six files pass at the end.

Use ECDSA P-256 with SHA-256 from the platform's standard library or a vetted, maintained crypto library (for example
`cryptography` in Python), and never write ECDSA, point arithmetic (adding or multiplying curve points) or SHA-256
yourself ([KEYS-69](SPEC.md#keys-69)). Where a rule needs a point derived from a scalar or checked against the curve
([KEYS-12](SPEC.md#keys-12), [KEYS-13](SPEC.md#keys-13), [KEYS-63](SPEC.md#keys-63)), let the library derive and check
it, as SPEC.md section 14.18 shows for each platform; the one computation of your own that 14.18 allows is testing the
curve equation with big integers, which checks a point and adds or multiplies none. Signatures on the wire are the
64-byte raw `r || s`, never DER ([KEYS-29](SPEC.md#keys-29)), and a verifier accepts a high-S signature
([KEYS-30](SPEC.md#keys-30)); many libraries default to DER, as section 14.9 lists.

## Running the vectors

- The runner calls the SDK's public API only, one test per case, named as the case. Its own check of the `gid` inside
  a built token may use a GID verifier of the SDK's, public or internal (FORMAT.md section 5.3).
- The runner never sets the SDK's clock ([KEYS-68](SPEC.md#keys-68)). It reads its own clock once per case, and the
  vectors' time expressions allow for the SDK reading the system clock later (FORMAT.md section 3.1).
- The settlement client gets the runner's fake transport through the SDK's transport injection
  ([SETTLE-68](SPEC.md#settle-68)); no case reaches the network.
- Cancellation: the submit call takes the platform's standard cancellation primitive, or a token type the SDK defines
  and documents where the platform has none ([SETTLE-76](SPEC.md#settle-76)). A handle cancelled before the call fails
  it before the key store is consulted; a cancellation during the call stops it at once in any step, the key lookup,
  the wait for the answer and the body read included, and fails with the platform's cancellation error
  ([SETTLE-62](SPEC.md#settle-62)). An expired time limit fails with the platform's timeout error, never `api_error`
  ([SETTLE-61](SPEC.md#settle-61)).
- The handlers are checked through one core, `handle(method, path, bodyBytes, cancel?) -> {status, headers, body}`
  ([HTTP-73](SPEC.md#http-73)). The SDK need not offer it: the runner adapts the SDK's own router to it (FORMAT.md
  section 6.7), and no public API changes for the runner.
- The SDK's own test suite also checks the three golden files in `vectors/golden/`: `floor-x.json` and
  `player-x.json` as [GAMEPASS-45](SPEC.md#gamepass-45) says, and `gid-signature.json` the three ways
  [GID-39](SPEC.md#gid-39) says. That suite is not the runner and may call internal functions: the canonical GID bytes
  and a GID verifier need not be public to be checked there ([GID-42](SPEC.md#gid-42), [GID-43](SPEC.md#gid-43)).

## Skips

- Run every case your SDK can take. A skip is permitted, never required: you may skip a case only when it carries
  `needs` and at least one tag in it names an input your SDK's declared parameter types cannot express, judged for
  that case's actual input, so that the call cannot be written or the language refuses it before the SDK runs
  (FORMAT.md section 7); a case needs every input its tags name. A tag can stand for several inputs (`missing-params`
  is a `null`, an absent or a non-object parameter set), so where your types express this case's input, run it;
  running a case you could have skipped is always fine. Decide by what the parameter types do, not by the language's
  family: an SDK whose parameters accept any value skips nothing.
- Report each skipped case as skipped, never as passed, with its name and its tags, for example
  `SKIP gidgp-gamepass-amount-string needs=[untyped-number]`, and report the number skipped.
- Never skip a case that has no `needs`, and never skip a case because it fails.
- Where the SDK's parameter structs cannot express absence, compare against `wantZeroValue` when a case has one.

## Rules no vector covers

No case can observe these rules, so the SDK's own tests and your review must. Meet each one, and write the
documentation it asks for.

- [KEYS-15](SPEC.md#keys-15): private- and public-key file loaders on a platform with a filesystem.
- [KEYS-16](SPEC.md#keys-16): a loaded key is an opaque handle of the platform's crypto library.
- [KEYS-43](SPEC.md#keys-43): no token length limit beyond the handlers' body cap.
- [KEYS-59](SPEC.md#keys-59): the key store is safe to register into while requests are served.
- [KEYS-62](SPEC.md#keys-62): optional low-level JWT and GID helpers follow section 5's rules.
- [KEYS-68](SPEC.md#keys-68): times come from the system clock; a runner never sets an optional clock.
- [KEYS-69](SPEC.md#keys-69): ECDSA, point arithmetic and SHA-256 come from the platform or a vetted library.
- [GID-21](SPEC.md#gid-21): every builder call signs its GID afresh; no builder takes a signed GID.
- [GID-42](SPEC.md#gid-42): optional low-level helpers, the GID form of KEYS-62.
- [GID-43](SPEC.md#gid-43): an optional standalone GID verifier checks its keys first.
- [GAMEPASS-33](SPEC.md#gamepass-33): unknown gamepass parameters are ignored and never emitted.
- [GAMEPASS-36](SPEC.md#gamepass-36): no gamepass parser is specified.
- [GAMEPASS-44](SPEC.md#gamepass-44): document which `xBase` and `decimals` a partner passes to the X helpers.
- [GAMEPASS-50](SPEC.md#gamepass-50): a neutral-spelled parameter key, if the SDK refuses it, is `invalid_claim`
  naming that member.
- [INBOUND-24](SPEC.md#inbound-24): the GID is always verified; no option skips it.
- [INBOUND-53](SPEC.md#inbound-53): the inbound gid is checked against every listed partner key.
- [SETTLE-14](SPEC.md#settle-14): the eight settlement statuses are exposed, in order.
- [SETTLE-64](SPEC.md#settle-64): retry and diagnosis guidance in the SDK's README.
- [SETTLE-65](SPEC.md#settle-65): queue parameters, not tokens; rebuild a stored token after a key rotation.
- [SETTLE-67](SPEC.md#settle-67): no settlement parser; generic helpers are optional.
- [VERIFYKEYS-03](SPEC.md#verifykeys-03): the verify-keys handler keeps no state and never throttles.
- [VERIFYKEYS-04](SPEC.md#verifykeys-04): the SDK's own code never answers 3xx.
- [VERIFYKEYS-05](SPEC.md#verifykeys-05): the builders take the nonce from their caller.
- [VERIFYKEYS-61](SPEC.md#verifykeys-61): framework adapters, the same rule as HTTP-16.
- [HTTP-16](SPEC.md#http-16): a framework adapter applies the body checks it still can.
- [HTTP-31](SPEC.md#http-31): the request's cancellation reaches the stores where the platform passes one.
- [HTTP-47](SPEC.md#http-47): the handlers keep no state and never rate-limit, serialise or block.
- [HTTP-60](SPEC.md#http-60): SDK error messages are not contract; HTTP error strings are.
- [HTTP-61](SPEC.md#http-61): optional functions on a parsed body answer as the router does.
- [HTTP-62](SPEC.md#http-62): optional low-level helpers, the HTTP form of KEYS-62.
- [HTTP-70](SPEC.md#http-70): signed payload bytes are free, except the GID's canonical bytes.

Some rules that do have vectors also ask for documentation, which no case can check: [KEYS-44](SPEC.md#keys-44) and
[HTTP-69](SPEC.md#http-69) (a key store matches ids byte for byte and never falls back to a fixed key set),
[KEYS-52](SPEC.md#keys-52) (a key store tolerates concurrent calls), [GID-10](SPEC.md#gid-10) (keep `:` out of
`user` and `bet`), [GAMEPASS-03](SPEC.md#gamepass-03) (build a gamepass right before the game opens with it),
[SETTLE-18](SPEC.md#settle-18) (0 is sent for an `amount` or `version` the SDK cannot tell from unset),
[SETTLE-51](SPEC.md#settle-51) (any 2xx with the acceptance body is an acceptance), [SETTLE-76](SPEC.md#settle-76)
(the cancellation primitive, and how to tell a cancellation from a time-out), [HTTP-29](SPEC.md#http-29) (the bet
store is idempotent), [HTTP-34](SPEC.md#http-34) (an unknown bet is `false`, not an error) and
[HTTP-66](SPEC.md#http-66) (a store wrapper forwards the optional check).

## Definition of done

- Every case of the six vector files passes, and the only skips are those FORMAT.md section 7 allows, reported with
  their tags.
- The three golden files pass.
- Every rule in "Rules no vector covers" is met, and the documentation it asks for is written.
- The decisions of FORMAT.md's "Bringing up a new language" are recorded in the runner, and in the SDK's documentation
  where a partner meets them (how to check an error, cancel a call, recognise a time-out).
- The SDK keeps a byte-for-byte mirror of `vectors/`, pinned to the spec commit it was built from (FORMAT.md
  section 8).
- Where you had to guess, or a rule and a case seem to disagree, the question is written down with its rule id and
  case name, for your user to send to sdk@boostxinnovation.com. A choice the spec marks as the SDK's needs no question:
  one granted by a `MAY` in a rule, or one under a paragraph that starts `Implementation-defined:`, wherever it stands
  (SPEC.md section 1.5 indexes the broadest), or a decision of FORMAT.md's "Bringing up a new language". Record each
  such choice, with the rule or paragraph that frees it, in the SDK's documentation or its runner, and list it in your
  notes as a choice made, not as a question. A choice you cannot tie to such a rule or paragraph is a question, even if
  you are confident of the answer: write it down with the rule ids that came closest.

## Recording the spec version

The SDK's README states, in these words, `Conforms to boostx-partner-sdk-spec vX.Y.Z (commit <sha>).`: the version of
the newest entry in [CHANGELOG.md](CHANGELOG.md), and the full commit of this repository the SDK was built and tested
from. This repository is https://github.com/boostxinnovation/boostx-partner-sdk-spec, and each release is tagged
`vX.Y.Z` there, so the commit of a release is the one its tag names. To read it,
`git ls-remote https://github.com/boostxinnovation/boostx-partner-sdk-spec 'refs/tags/vX.Y.Z*'` and take the line ending
`^{}` when there is one (an annotated tag: the plain line is the tag object, not the commit), otherwise the plain line;
in a clone, `git rev-parse 'vX.Y.Z^{commit}'`. That URL is also where the SDK's CI fetches the pinned commit to compare
its mirror (FORMAT.md section 8). An archive made by `git archive` from a commit or a tag, as GitHub's source downloads
are, records the commit as well: `unzip -z <file>.zip` prints it as the ZIP file's comment, and
`gunzip -c <file>.tar.gz | git get-tar-commit-id` reads it from a tarball, so if you were given the archive file itself,
read the commit there. If you have this repository without its git history (files unpacked from an archive, for
example) and can reach neither that URL nor the archive, ask your user for the commit rather than guess it. If you
cannot ask before you finish, write `(commit unknown)` in that line, keep the `vectors/` mirror byte for byte as you
received it, and put the missing commit first among your questions: the conformance claim is incomplete until the line
names it. That is expected when you work offline, and the one question this step leaves. Claim conformance only, never
identical behaviour to another SDK: the vectors sample the input space. Moving to a later spec release means moving the
pin, mirroring `vectors/` again, passing every case, and updating that line.

## Testing against BoostX

There is no test environment: the only base URL is BoostX production ([SETTLE-36](SPEC.md#settle-36)), so the first
real call an SDK makes reaches production. Once every vector passes, test the integration end to end with demo games
(a gamepass built with `demo: true`, [GAMEPASS-32](SPEC.md#gamepass-32)) and the dashboard's Test integration, which
calls `/verify-keys`.
