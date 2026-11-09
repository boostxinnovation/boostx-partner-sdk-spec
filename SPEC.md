# Partner SDK Specification

**Version:** v1.2.0 ([CHANGELOG.md](CHANGELOG.md))
**Scope:** the behaviour of a BoostX partner SDK: key loading and key stores, the five token types, the signed GID, the
three partner endpoints, the settlement client and the X helpers.
**Vectors:** [`vectors/`](vectors/) (format: [`vectors/FORMAT.md`](vectors/FORMAT.md)).

## Contents

1. Purpose and sources of truth
2. Principles
3. SDK surface
4. Error taxonomy
5. Keys and JWS (KEYS)
6. Signed GID (GID)
7. GamePass builder and X helpers (GAMEPASS)
8. Inbound Booster and CheckBet (INBOUND)
9. Settlement (SETTLE)
10. Verify-keys (VERIFYKEYS)
11. HTTP handlers (HTTP)
12. Conformance vectors
13. Decisions
14. Platform notes (informative)

## 1. Purpose and sources of truth

### 1.1 Purpose

This spec is the one behavioural definition of a BoostX partner SDK. An SDK in a new language is written from it, and
the two reference SDKs are tested against it. Its goal is that any SDKs built to it give the same result for the same
input: the same token accepted or refused, the same error category, the same HTTP answer.

It covers what an SDK does on its own: which inputs it accepts, in which order it checks them, which error it raises,
and how it answers BoostX. It is self-contained for SDK behaviour: with the conformance vectors, it is all an
implementer needs. Section 1.6 summarises the integration as far as an SDK depends on it. The partner docs give people
the wider context (onboarding, the game); they are never the source of an SDK rule.

Out of scope: a gamepass parser (BoostX parses gamepasses; the Go SDK keeps a deprecated one outside conformance,
[GAMEPASS-36](#gamepass-36)), the partner dashboard, and the game frame.

### 1.2 Sources of truth

| Source | What it defines |
|--------|-----------------|
| This spec | Everything an SDK does: validation gates, check orders, error categories, handler answers, client behaviour, and what BoostX sends and accepts as far as an SDK depends on it |
| The conformance vectors (section 12) | This spec in executable form, mirrored byte for byte into every SDK's test suite |
| Partner docs, which BoostX opens to its partners | Context for people: the integration flow, onboarding, key setup, the game. They describe the same wire contract and are never the source of an SDK rule |

A disagreement between the partner docs and this spec is a defect. It is settled by a decision (section 13), and the
docs, this spec, the reference SDKs and the vectors change together.

### 1.3 This repository and the reference SDKs

This repository is the master of this spec and of the conformance vectors. Two reference SDKs implement it:

| SDK | Repository | Package |
|-----|-----------|---------|
| JavaScript and TypeScript (Node.js, Cloudflare Workers, other Web Crypto runtimes) | `boostxinnovation/boostx-partner-sdk-js` | `@boostxinnovation/partner-sdk` (main entry, plus the Node-only entry `@boostxinnovation/partner-sdk/node`) |
| Go | `boostxinnovation/boostx-partner-sdk-go` | module `github.com/boostxinnovation/boostx-partner-sdk-go`: packages `keys`, `tokens`, `handlers`, `client`, and the facade package `boostx` that re-exports their public names |

How changes flow:

- A change to SDK behaviour starts here: the rule in this spec and the vectors change together, in one spec release
  whose CHANGELOG entry lists the rule ids and vector cases it changes. The reference SDKs follow it.
- From v1.2.0 the reference SDKs share this spec's major and minor version: release vX.Y.n of each SDK implements spec
  vX.Y. A change to a rule or a vector is a minor or major spec release, and both SDKs follow it as vX.Y.0, even one
  with nothing else to change, whose CHANGELOG entry says so. The patch number is each repository's own: a spec patch
  only clarifies wording, and an SDK patch changes no rule (a fix that brings that SDK in line with this spec, its
  documentation, or something only that SDK has), so neither needs a release of the others.
- Every SDK keeps an exact, byte-for-byte mirror of `vectors/`, checked against a pinned commit of this repository, and
  changes it only by moving the pin (section 12.1).
- A change partners can see also changes the partner docs and gets an entry in their changelog.
- When two sources disagree, the order is: the decisions in section 13, then the rules of this spec, including the
  principles of section 2. Where this spec is silent, or a rule and a vector case seem to disagree, an implementer does
  not copy another SDK: they write the question down, with the rule id and the case name, and send it to
  sdk@boostxinnovation.com.

### 1.4 Terminology

| Term | Meaning |
|------|---------|
| GID | The triple `partner`, `user`, `bet` that identifies one game |
| signed GID | The GID plus `signature`, an ES256 signature over the GID's canonical bytes made with the partner private key (section 6). The partner docs call this object "GID" (`gid` claim) |
| partner id | The id BoostX assigned to the partner, the GID's `partner` |
| partner private key | The partner's ES256 signing key: signs the GID, gamepasses, settlements and verify-keys responses |
| partner public keys | The list of partner public keys a parser accepts for the GID signature; more than one during a key rotation |
| BoostX public key | The key that verifies what BoostX signs for that partner: Booster, CheckBet and verify-keys requests |
| inbound token | A token BoostX signs and the partner reads: BoosterJWT, CheckBetJWT, the verify-keys request |
| extraction | Reading the partner id from an inbound token before any key is known, without verifying it ([P-extraction](#p-extraction)) |
| builder | A function that signs a token or a signed GID |
| parser | A function that verifies an inbound token and returns its claims |
| handler | The SDK code that answers one of BoostX's three calls (section 11) |
| `invalid_<token>` | The token's own category: `invalid_booster`, `invalid_checkbet`, `invalid_verify_keys` |
| malformed token | An error whose categories are `invalid_<token>` alone; verify-keys reason `shape` |

### 1.5 How rules are written

**Rule ids.** Every normative rule carries an id (`KEYS-12`) and is written once, under that id, with an anchor that is
the id in lower case (`#keys-12`). A rule that also settles ids of other groups says so in a line `Also covers: GID-04,
INBOUND-28.`, and those ids have their anchor there. Where a group writes its own view of a rule whose full text is
elsewhere, the paragraph says `Same rule as` or `Primary rule` and links it. Every id resolves to exactly one anchor.

**Normative words.** MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in RFC 2119 and RFC 8174, in capitals and
only in normative text.

**Check orders.** A check order is a numbered list in its own rule. The first failing step is the one reported, and
vectors may carry several faults to pin the order ([P-check-order](#p-check-order)). Step numbers are stable once
vectors cite them.

**Implementation-defined.** Every place an SDK may choose is marked, in one of two ways: by a `MAY` in a rule, or by a
paragraph that starts `Implementation-defined:` (in a rule paragraph or a list item, right after its bold title) and
says exactly what may vary. Those permissions and paragraphs, wherever they stand, are the complete list of freedoms.
The table indexes the broadest, for orientation:

| Freedom | Rule |
|---------|------|
| Emitted payload bytes: member order, escaping, number spelling, whitespace | [KEYS-61](#keys-61), [P-emitted-bytes](#p-emitted-bytes) |
| The escaping of an echoed partner id inside an error body | [HTTP-24](#http-24), [HTTP-38](#http-38) |
| Whether a handler's two key lookups run concurrently | [KEYS-52](#keys-52) |
| Error message texts | [HTTP-60](#http-60), section 4.5 |
| Host-router 404 and 405 bodies, and its redirects | [HTTP-02](#http-02), [HTTP-04](#http-04) |
| What happens to the connection after the body cap | [HTTP-07](#http-07) |
| A constructor that panics instead of raising `invalid_claim` (Go) | [HTTP-48](#http-48) |
| Sync or async APIs; how parameters and parameter sets are passed and named, and how result fields are named; which of the language's number types a numeric parameter accepts | section 3.4 |
| Whether a key-value map's key in the neutral spelling of a member the SDK spells otherwise is ignored or refused | [GAMEPASS-50](#gamepass-50) |
| An optional clock that defaults to the system time, which conformance runners never set | [KEYS-68](#keys-68) |
| The cancellation primitive where the platform has none, how a caller tells a cancellation from an expired time limit that shares its error type, and which timeout error reports an expired limit where the platform has more than one | [SETTLE-76](#settle-76) |
| How errors are represented (codes, sentinels, types), as long as the categories and the cause chain hold | section 4 |
| JSON nesting depth, with a floor of 64 levels | [P-one-value](#p-one-value) |
| URL parser residue beyond the client's base-URL rules, and whether a non-string base URL is converted or refused | [SETTLE-39](#settle-39) |
| Mount-prefix characters refused beyond those the host router reads as pattern syntax, and whether a router that takes a prefix requires one | [HTTP-68](#http-68) |
| Whether a cause-chain walk enters a container of several errors (Go `errors.Join`, Python `ExceptionGroup`, JS `AggregateError`) | [HTTP-69](#http-69) |
| The unit and representable range of the settlement time limit | [SETTLE-61](#settle-61) |
| The layer at which the settlement transport is injected, its shape, and the HTTP library of the default transport | [SETTLE-68](#settle-68) |
| An unpaired surrogate in a settlement error text | [SETTLE-56](#settle-56) |
| Ties at the 15th significant digit in the X helpers, and their out-of-domain inputs | [GAMEPASS-39](#gamepass-39), [GAMEPASS-40](#gamepass-40), [GAMEPASS-41](#gamepass-41) |

**Vectors.** A rule names the vector file, or the cases, that exercise it: `(Vectors: keys.json.)`. A rule with no
vector says why.

**What the SDK sees from BoostX.** Sections 6 to 11 each have a subsection whose title includes "What the SDK sees from
BoostX (informative)". It says what BoostX sends, accepts and answers, as far as an SDK observes it. It explains rules
and states no requirement on an SDK, with one exception: 8.9 also carries the round semantics, and with them
[INBOUND-51](#inbound-51), which is normative.

**Names.** A concept is named neutrally first, then in both SDKs, JS first: `buildGID` (JS
`buildGID(key, partner, user, bet)`, Go `tokens.BuildGID(partner, user, bet, key)`). Go names are package-qualified; the
facade `boostx` re-exports each under the same name, mentioned only where it matters. Parameter-set members use the
neutral names of `FORMAT.md`, which are the JS names (`xMin`, `settledAt`). Error categories are written as code
(`invalid_claim`) and mapped to each language once, in section 4.2. Operations and their inputs carry the names of the
catalogue in section 3; for the operations the vectors call, those are the operation and input names of FORMAT.md
section 6.

### 1.6 Integration overview

This subsection is informative. It describes the integration as far as an SDK depends on it; every rule it mentions
is stated where it links.

**Keys.** Two ECDSA P-256 key pairs protect the integration, one for each direction. The partner creates the partner
key pair, keeps the partner private key and gives BoostX the partner public key. BoostX creates one BoostX key pair
for each partner account, keeps the BoostX private key and gives the partner the BoostX public key. Every token is a
compact ES256 JWS (section 5).

**The five tokens.**

| Token | Signed with | Travels | Carries |
|-------|-------------|---------|---------|
| GamePassJWT | partner private key | partner to BoostX, inside the game URL | the signed GID, the stake, the X range, an optional event title and demo flag (section 7) |
| CheckBetJWT | BoostX private key | BoostX to the partner's `POST /check-bet` | the signed GID (section 8) |
| BoosterJWT | BoostX private key | BoostX to the partner's `POST /set-boost` | the signed GID, the round number, the accumulated boost, `final` and `jackpot` (section 8) |
| SettlementJWT | partner private key | partner to BoostX's settlement endpoint | the signed GID, the status, the payout, a version, an optional `xSettle`, `settledAt` (section 9) |
| Verify-keys request and response | BoostX private key; partner private key | BoostX to the partner's `POST /verify-keys`, and back in the answer | a nonce that the response echoes (section 10) |

The signed GID (section 6) is the bet's `partner`, `user` and `bet` plus a signature made with the partner private
key. The partner signs it when it builds a gamepass; BoostX echoes it unchanged in every CheckBet and Booster of that
game; the partner signs it afresh for every settlement.

**The flow.**

1. The partner builds a GamePassJWT for a bet (`gamepass.create`) right before it opens the game with it, since
   BoostX refuses a gamepass whose `iat` is more than 300 seconds from its clock. It records the `x` it signed: that
   is the `xBase` it needs to derive X later ([GAMEPASS-44](#gamepass-44)). The game frame carries the token to
   BoostX; the SDK makes no call here. A later gamepass for the same bet re-enters the same game, and only its `x`
   changes anything.
2. If the partner enabled it, BoostX calls `POST /check-bet` at every game open and before every round, and the
   partner's bet store says whether the bet is still active (`betstore.checkBet`).
3. After each round BoostX calls `POST /set-boost` with a BoosterJWT, and the bet store applies it
   (`betstore.setBoost`). The partner derives the X the player saw with `x.player` from `xBase` and `boost`. The
   round that takes X out of the range of the gamepass that created the game, or a jackpot round, carries
   `final: true` and ends the game.
4. Once the partner has settled the bet on its side, it submits a SettlementJWT (`client.submit`), and sends the same
   settlement again until BoostX accepts it.
5. Apart from games, BoostX's integration self-test (Test integration) calls `POST /verify-keys`, and the SDK answers
   with a response token signed with the partner private key.

The SDK serves the three endpoints through one router (`http.serve`, section 11). It verifies every token and its GID
before the bet store sees it, and answers BoostX with the statuses and bodies of section 11.

**Settlements are retried until accepted.** One `client.submit` call makes one attempt. Only a 2xx answer with the
body `{"result":{"ok":true}}` means BoostX holds the settlement; every other outcome, a 4xx included, means "not yet".
The partner queues the parameters, not a signed token, sends the same parameters again with a backoff over a window,
for example three days, and then raises an alert; a correction goes under a higher `version`
([SETTLE-63](#settle-63), [SETTLE-64](#settle-64), decision [retry until ok](#decision-retry-until-ok)).

**What a bet store does.** The bet store is partner code that the SDK's handlers call ([INBOUND-51](#inbound-51),
[HTTP-29](#http-29)):

- It finds the bet by `partner`, `user` and `bet` together, never by `bet` alone ([GID-11](#gid-11)).
- One round can arrive more than once: BoostX retries a call with the identical token, plays an unacknowledged round
  again with a fresh `iat`, and a delayed copy of an older round can arrive after a newer one
  ([INBOUND-50](#inbound-50)). So the store applies a round only when its number is greater than the stored one,
  returns normally for any other, and signals the round-rejected error, without writing anything, for a new round it
  will not apply. BoostX records a round only when the handler answers `{"result":{"ok":true}}`, which it does when
  the store returns normally.
- A jackpot comes as a pair: regular round `N`, committed first, then jackpot round `N + 1` with `jackpot: true` and
  `final: true`. When the jackpot leg fails, BoostX sends it again under the same `N + 1` with the same boost, and
  does not send `N` again. Every attempt keeps the `xBase` on which BoostX fixed its result
  ([GAMEPASS-44](#gamepass-44)). A jackpot round already applied is a replay like any other
  ([INBOUND-48](#inbound-48), [INBOUND-49](#inbound-49)).
- Its check-bet verdict is a boolean: `true` while the bet may play, `false` to refuse the next spin.

## 2. Principles

These principles apply across every group. A group rule that applies one links it rather than restating it. Each
principle lists the rule ids it settles.

<a id="p-names"></a>**P-names. Exact JSON member names.** Every member name an SDK reads MUST be matched exactly, code
unit for code unit after JSON unescaping, with no case folding and no Unicode folding. That covers JWS headers, JWS
payloads at every depth, request bodies (`checkbetJWT`, `boosterJWT`, `verifyKeysJWT`) and settlement responses
(`result`, `ok`, `error`). A member spelled any other way is unknown and ignored, so it never supplies or overrides the
named member. The one exception is an optional generic helper that maps claims into a structure the caller supplies:
it follows the language's own decoder ([KEYS-62](#keys-62)). Why: BoostX emits and reads exact names, and exact lookup is
the default in every language. Settles: KEYS-22, KEYS-34, KEYS-62, INBOUND-05, INBOUND-14, VERIFYKEYS-22,
VERIFYKEYS-30, VERIFYKEYS-56, GID-28, HTTP-12, HTTP-62, HTTP-67, SETTLE-53.

<a id="p-duplicates"></a>**P-duplicates. Repeated member names: the last occurrence wins.** When a JSON object repeats
a member name, at any depth and in any JSON text the SDK reads, the last occurrence MUST be the member's value. It
replaces the earlier ones whole: objects are never merged, and a later `null` counts as `null`. Why: RFC 7515 section
5.2 and RFC 7519 section 4 allow it, and the standard parsers of every common language behave this way natively.
Settles: KEYS-22, KEYS-33, INBOUND-15, SETTLE-53.

<a id="p-one-value"></a>**P-one-value. One JSON value, and an object where the spec needs one.** Every JSON text an SDK
reads MUST be exactly one JSON value, optionally surrounded by JSON whitespace; anything after it is a fault. Where the
spec needs an object, any other value, `null` included, is a structural fault of that context:

| Context | Fault |
|---------|-------|
| JWS header or payload | malformed token (verify-keys reason `shape`) |
| `gid` | `invalid_gid` |
| `booster` or `checkbet` root claim | `invalid_claim` |
| `verifyKeys` | `shape` |
| settlement response, or its `result` member | not an acceptance |

There is one exception: a request body that is `null` reads like a body with no token member ([P-body](#p-body)).
Settles: KEYS-24, KEYS-32, INBOUND-05, INBOUND-13, INBOUND-17, GID-27, VERIFYKEYS-28, VERIFYKEYS-42, HTTP-09, HTTP-67,
SETTLE-53.

Implementation-defined: an SDK's JSON reader MAY refuse a text nested deeper than a limit of its own (decision [JSON
nesting depth](#decision-json-depth)), and MUST accept every text nested 64 levels deep or less. The depth of a JSON
text is the largest number of arrays and objects open at one point of it, the outermost value included: a scalar has
depth 0, `{}` and `[]` depth 1, `{"a":[1]}` depth 2. A text over the SDK's limit is treated as not valid JSON in its
context: a malformed token, `400 invalid request body` for a request body, and not an acceptance for a settlement
response. Everything BoostX sends nests at most three levels deep (payload, root claim, `gid`). Why a floor and not
unlimited depth: every common JSON parser has a depth or recursion limit (Go's `encoding/json` refuses more than 10 000
levels), and 64 is the smallest common default (.NET `System.Text.Json`).

<a id="p-utf8"></a>**P-utf8. Strict UTF-8 and no byte order mark.** Every JSON text an SDK reads MUST be checked as
bytes before it is parsed. It MUST be well-formed UTF-8 (RFC 3629: no overlong forms, no encoded surrogates, nothing
above U+10FFFF) and MUST NOT begin with `EF BB BF`. Invalid bytes are never replaced with U+FFFD. A token header or
payload that fails is a malformed token (verify-keys reason `shape`). A request body that fails is answered
`400 {"error":"invalid request body"}`. A settlement response that fails is not an acceptance, and on a non-2xx it
gives the fallback error text. Why: replacing bytes changes signed content, and standard decoders disagree on both
points, so the rule is stated on bytes. Settles: KEYS-35, KEYS-36, KEYS-66, GID-06, INBOUND-10, INBOUND-11,
VERIFYKEYS-29, VERIFYKEYS-56, HTTP-10, SETTLE-54.

<a id="p-surrogates"></a>**P-surrogates. Ill-formed Unicode (lone surrogates).** `partner`, `user` and `bet` are
well-formed Unicode.

- A builder MUST refuse an id that is not, whether it holds an unpaired surrogate or invalid UTF-8, with
  `invalid_claim`.
- An inbound token whose header or payload JSON text contains a `\uD800`-`\uDFFF` escape that is not half of a
  high-then-low pair MUST be a malformed token (`invalid_<token>`, or verify-keys reason `shape`), in extraction and
  parsing alike, and it is never verified as a GID. The check runs on the JSON text, before or while it is parsed,
  because some decoders silently substitute U+FFFD. An escaped pair (`\uD83D\uDE00`, either hex case) and a literal
  multi-byte character are well-formed.
- The one exception is `eventTitle`, a display-only field outside the GID: a builder replaces each ill-formed part
  with U+FFFD and still issues the token.

BoostX refuses a gamepass whose `gid.partner`, `gid.user` or `gid.bet` is not well-formed when the game opens (decision
[lone-surrogate ids](#decision-lone-surrogates)). Settles: KEYS-37, GID-04, INBOUND-28, GAMEPASS-07, GAMEPASS-31,
GID-35.

<a id="p-base64url"></a>**P-base64url. Canonical unpadded base64url everywhere.** Each of the three JWS segments, and
`gid.signature`, MUST be canonical unpadded base64url: only `[A-Za-z0-9_-]`, a length that is not 1 mod 4, no `=`, no
whitespace or CR/LF, and zero unused trailing bits. Equivalently, re-encoding the decoded bytes gives back the text
exactly. The JWS signature segment MUST also decode to exactly 64 bytes, and `gid.signature` MUST match
`^[A-Za-z0-9_-]{85}[AQgw]$`. Tokens are used exactly as received, never trimmed. Why: BoostX enforces this for
`gid.signature` (decision [canonical GID signatures](#decision-canonical-gid-signatures)), one byte string then has
exactly one token text, and the check is portable (alphabet and length, decode, re-encode, compare). Settles: KEYS-26,
KEYS-31, KEYS-47, INBOUND-03, INBOUND-26, INBOUND-56, VERIFYKEYS-25, VERIFYKEYS-26, VERIFYKEYS-27, GID-17, HTTP-41,
HTTP-55.

<a id="p-signature-vs-shape"></a>**P-signature-vs-shape. Signature failure versus malformed token.** Every fault that
prevents establishing an ES256 signature MUST be a signature failure (`invalid_signature`, verify-keys reason
`signature`):

- `alg` absent, `null`, or anything other than the JSON string `"ES256"`;
- any `crit` member, whatever its value;
- a JWS signature segment that is not canonical or not 64 bytes;
- ECDSA verification failing;
- for the GID, a `gid.signature` not in canonical form, or one that no usable listed key verifies. These GID faults
  carry `invalid_gid` as well.

Every other structural fault is a malformed token (reason `shape`): the wrong segment count, header or payload
encoding or bytes, a header or payload that is not an object. Header members other than `alg` and `crit` are ignored,
whatever their type. An unusable key is never a signature failure: it is `invalid_public_key`, and only the verify-keys
reason mapper reports `invalid_public_key` as `signature`. Why: BoostX reports every verification failure except a
claim failure as `signature`, and treats a non-canonical GID signature exactly like a wrong one. Settles: KEYS-23,
KEYS-24, KEYS-31, KEYS-47, KEYS-60, KEYS-64, KEYS-65, GID-17, INBOUND-04, INBOUND-26, INBOUND-55, INBOUND-56,
VERIFYKEYS-06, VERIFYKEYS-22, VERIFYKEYS-23, VERIFYKEYS-24, VERIFYKEYS-26, VERIFYKEYS-51, HTTP-55, HTTP-57, HTTP-67.

<a id="p-integers"></a>**P-integers. Integer claims are judged by value.** An integer claim (`round`, `iat`, `nonce`)
MUST be a JSON number. Its text is converted to the nearest IEEE 754 binary64 value, and the claim is valid when that
value is integral, its magnitude is at most 2^53−1, and it lies in the claim's own range: `round` in [1, 2^53−1],
`nonce` in [1, 2147483647], `iat` with no further range. So `3`, `3.0` and `3e0` are the same value. A text beyond
binary64 range becomes plus or minus Infinity, or underflows to 0, and is judged as that value. Strings, booleans and
`null` are never numbers. A failure is the claim's invalid category: `invalid_claim` on Booster and CheckBet; on
verify-keys, `shape` for `iat` and `nonce-format` for the nonce. Why: some JSON parsers expose no number text, so a
rule on spelling cannot be followed everywhere; a rule on the value can. Settles: KEYS-39, INBOUND-34, INBOUND-35,
INBOUND-41, VERIFYKEYS-35, VERIFYKEYS-43, VERIFYKEYS-70, HTTP-23, HTTP-40.

<a id="p-null-absent"></a>**P-null-absent. Null versus absent.**

- SDK inputs. Where a language tells `null` apart from absence, `null` MUST mean absent for every parameter, option and
  role. An absent required value is refused: `missing_claim` for an id, a currency or `settledAt`
  ([SETTLE-30](#settle-30)), and `invalid_claim` for any other number and for the settlement `status`
  ([SETTLE-70](#settle-70)). An absent optional value is unset and left out of the token; the SDK never writes `null`
  into a token. An absent key-store role is left out. A registration whose only purpose is to supply a list (Go
  `RegisterWithPartnerPublicKeys`) treats nil as an empty list and refuses it. An absent cancellation handle means no
  cancellation, and an absent base URL selects the default; an empty string is never absent.
- Wire. A `null` never selects a default or makes a value valid. For Booster and CheckBet claims, absent is
  `missing_claim`, while `null` or a wrong type is `invalid_claim`. Verify-keys has no missing-claim reason, so an
  absent or `null` required claim fails the check that reads it: `iss` and `aud` read as `""` (`iss-aud`), `iat` as 0
  (`stale`), `verifyKeys` as `{}` (`nonce-format`). An optional `exp` or `nbf` that is `null` is `shape`. A `null`
  request body, or an absent or `null` token member, reads as the empty token.

Why: an idiomatic optional parameter in some languages cannot tell null from "not passed", so null-as-absent is the one
input rule every language can follow, and it opens no new outcome. Settles: GAMEPASS-34, GAMEPASS-48, SETTLE-10,
SETTLE-18, SETTLE-35, SETTLE-39, SETTLE-69, KEYS-14, KEYS-57, HTTP-58, GID-27, INBOUND-13, INBOUND-17, INBOUND-33,
INBOUND-36, INBOUND-39, INBOUND-41, VERIFYKEYS-33, VERIFYKEYS-36, VERIFYKEYS-42, VERIFYKEYS-45, VERIFYKEYS-47,
VERIFYKEYS-56.

<a id="p-zero"></a>**P-zero. What 0 means for an optional number.** When an optional numeric parameter's valid domain
excludes 0, then 0, absent and `null` all MUST mean unset, and so the default. Such parameters are `xMin`, `xMax` and
`xDecimals` on a gamepass, the `decimals` of `floorX` and `playerX`, the verify-keys window and the settlement
per-attempt time limit. A negative or non-finite value is `invalid_claim`. Where 0 is a legal value (settlement `amount`
and `version`), the parameter is required and has no default; an SDK that cannot tell an unset field from 0 (Go struct
zero values) sends 0 and documents it. A required number whose domain excludes 0 treats 0 as `invalid_claim`: the
gamepass `x`, and the gamepass `amount`, which MUST be finite and at least 0.01 (decision [minimum stake
0.01](#decision-minimum-stake)). `settledAt` is the exception named in [P-null-absent](#p-null-absent): 0 there reads as
not given, `missing_claim`. Settles: GAMEPASS-19, GAMEPASS-34, GAMEPASS-40, KEYS-41, VERIFYKEYS-38, HTTP-43, SETTLE-18,
SETTLE-61.

<a id="p-check-order"></a>**P-check-order. Check order is normative; configuration before input.** Every check order
this spec lists is normative: the first failing check is reported.

- Builders check the private key first, as far as it can be checked without signing ([KEYS-19](#keys-19)), then the
  parameters in the listed order, with the id checks of [GAMEPASS-07](#gamepass-07) step 3 (well-formed, no `:`,
  length) last ([GAMEPASS-08](#gamepass-08), [SETTLE-31](#settle-31), and [GID-34](#gid-34) for `buildGID`).
- Parsers check key configuration first, the BoostX key before the partner keys ([KEYS-46](#keys-46),
  [INBOUND-31](#inbound-31), [INBOUND-59](#inbound-59)), then follow [INBOUND-32](#inbound-32) or
  [VERIFYKEYS-46](#verifykeys-46).
- Handlers run body, then unverified extraction, then key lookups, then parse, then store ([HTTP-21](#http-21)). When
  both lookups fail, the BoostX key's outcome decides.

Only the scheduling of the lookups ([KEYS-52](#keys-52)) and how errors are represented may vary. Why: a generated
SDK's tests can then assert exact errors, and a configuration error, which breaks every call, is reported ahead of a
per-call input error. Settles: KEYS-19, GAMEPASS-08, GID-34, SETTLE-31, SETTLE-33, KEYS-46, GID-25, GID-43, INBOUND-31,
INBOUND-32, INBOUND-59, KEYS-52, HTTP-21, HTTP-26, VERIFYKEYS-46, VERIFYKEYS-68.

<a id="p-extraction"></a>**P-extraction. Unverified extraction before any key lookup.** Before calling the key store, a
handler MUST split the token into exactly three segments and check the unverified payload. It applies the payload
format rules (canonical base64url, bytes, a single object), then the same claim routine the parser runs after
verification. A failure is answered 400 without a store call. For Booster and CheckBet that routine is every claim
check: root, `gid` shape, `gid.partner`, the token's own fields, `iat`, `exp` and `nbf`. For verify-keys it is the
claim types plus an `aud` that is not empty and not `"boostx"`. Extraction never reads the header or the signature
segment. Why: junk never reaches the partner's database or KMS, and a store outage cannot change the answer to a
malformed token. Verify-keys checks less here because its reasons are ordered with `signature` before `iss-aud`,
`stale` and `nonce-format`, which BoostX's self-test reads. Settles: KEYS-49, GID-33, INBOUND-21, HTTP-21,
VERIFYKEYS-27, VERIFYKEYS-46.

<a id="p-key-usability"></a>**P-key-usability. Key usability: never crash, refuse at startup.** A key is usable only if
it is an ECDSA P-256 key of its role that the platform can use. For a public key the point MUST be present, on the
curve, with coordinates in range and not the point at infinity; for a private key the scalar MUST be valid; and the key
MUST allow verifying or signing as its role requires. An unusable key is the role's invalid-key error (handlers answer
500), never a crash and never a signature failure. In a partner public key list, unusable keys are skipped, and
`invalid_public_key` results only when no listed key is usable. Registration in an in-memory key store refuses an
unusable key and an empty partner key list at startup, with the role's invalid-key error. Settles: KEYS-14, KEYS-57,
KEYS-63, GID-26, GID-45, INBOUND-60, SETTLE-33, SETTLE-35, HTTP-26, HTTP-58.

<a id="p-taxonomy"></a>**P-taxonomy. Closed error taxonomy.** Every error an SDK raises itself MUST carry one category
from the closed set of section 4.1 ([HTTP-54](#http-54)). Key faults are `invalid_private_key` or `invalid_public_key`.
An unserved id is `unknown_partner`. Token faults are `invalid_<token>` with a cause: `missing_claim`, `invalid_claim`,
`invalid_gid` or `invalid_signature`. A failed settlement answer is `api_error`. A configuration or argument error that
is not a key is `invalid_claim` wherever it is raised as an error: an absent store, a bad base URL or time limit, a
negative or non-finite window, handler options, a mount prefix. A missing parameter set reads as an empty one, so its
first fault is `missing_claim` for `partner` ([GAMEPASS-48](#gamepass-48)). A Go constructor MAY panic instead of
returning an error ([HTTP-48](#http-48)). Causes form a chain that the language's standard check walks (section 4.1).
Message texts are not part of the contract (section 4.5). Settles: HTTP-54, INBOUND-45, KEYS-14, KEYS-15, KEYS-41,
KEYS-56, KEYS-58, VERIFYKEYS-38, VERIFYKEYS-60, SETTLE-35, SETTLE-39, SETTLE-60, GAMEPASS-48, HTTP-27, HTTP-48, HTTP-60,
HTTP-68.

<a id="p-http-errors"></a>**P-http-errors. HTTP error strings and echoed ids.** A handler refusal is defined by its
status, a JSON body `{"error": <string>}` and the string's fixed wording, all of which are normative:

| Error string | Where |
|--------------|-------|
| `invalid request body` | any endpoint, body fault |
| `invalid booster token` | `/set-boost`, token fault |
| `invalid checkbet token` | `/check-bet`, token fault |
| `invalid verifyKeysJWT: <reason>` | `/verify-keys`, token fault |
| `unknown partner ` followed by the id | `/set-boost`, `/check-bet` |
| `round rejected` | `/set-boost`, the store rejected the round |
| `failed to set boost`, `failed to check bet`, `failed to verify token` | store or key failures |
| `method not allowed`, `not found` | routing |
| `internal server error` | invalid configuration of a per-call function |

An echoed id is written between double quotes, but how characters inside it are escaped is implementation-defined
([KEYS-51](#keys-51)). Text after a verify-keys reason, such as ` (unknown partner …)`, is free-form diagnostic
([VERIFYKEYS-14](#verifykeys-14)). Where a host router answers 404 or 405 before the SDK sees the request, the router's
body is acceptable. The full list of answers per endpoint is in section 11. Settles: KEYS-51, GID-44, INBOUND-57,
VERIFYKEYS-14, VERIFYKEYS-58, VERIFYKEYS-68, HTTP-03, HTTP-04, HTTP-24, HTTP-27, HTTP-38, HTTP-60.

<a id="p-exp-nbf"></a>**P-exp-nbf. `exp` and `nbf` are enforced when present.** Every token type this spec defines a
parser for (Booster, CheckBet, and the verify-keys request and response) treats `exp` and `nbf` as optional. If absent,
there is no limit. If present, each MUST be a JSON number; `null` or any other type fails, as `invalid_claim` on
Booster and CheckBet and as `shape` on verify-keys. A token with `exp <= now` or `nbf > now` fails, as `invalid_claim`
on Booster and CheckBet and as `stale` on verify-keys, where `now` is in whole Unix seconds and no leeway applies. The
check runs after `iat` in the claim step. SDKs never emit `exp` or `nbf`. Why: it is BoostX's own acceptance rule and
the default of JOSE libraries; BoostX sends neither claim. Settles: KEYS-42, VERIFYKEYS-46, VERIFYKEYS-47,
VERIFYKEYS-67, INBOUND-32.

<a id="p-window"></a>**P-window. Verify-keys window.** Handlers MUST accept `|now - iat| <= 30` whole seconds and offer
no option to change it. A parse function MUST take a window, measured in seconds whatever its type (a number of seconds
or a duration finer than a second, [KEYS-41](#keys-41)), which a call may leave out: absent, `null` or exactly 0 means
30, a negative or non-finite value is `invalid_claim`, and any other value is truncated toward zero to whole seconds, so
a positive value under 1 s gives a zero-second window. Why: BoostX checks the response `iat` against its own ±30 s, so a
wider window on the partner's side could never rescue a drifting clock. Settles: KEYS-41, VERIFYKEYS-38, VERIFYKEYS-40,
HTTP-43.

<a id="p-iat-exposed"></a>**P-iat-exposed. `iat` is exposed, never age-checked by the SDK.** A verified Booster and a
verified CheckBet MUST carry `iat` as received, in integer Unix seconds. A verified verify-keys request or response
carries `partnerID`, `nonce` and `iat`. The SDK applies no age check to Booster or CheckBet. An age check is the
partner's choice, and it must allow for retries, which re-send the same token. Settles: KEYS-39, INBOUND-42, HTTP-30,
HTTP-65, VERIFYKEYS-54.

<a id="p-emitted-bytes"></a>**P-emitted-bytes. Emitted bytes are not canonical, except the GID signing bytes.** Outside
the canonical GID signing bytes (section 6.1), the bytes an SDK emits are implementation-defined ([KEYS-61](#keys-61)),
as long as they are valid JSON carrying the specified values. That covers payload member order, string escaping
(including `<`, `>`, `&`, U+2028 and U+2029), number spelling (`-0` as `0` or `-0`, `150` as `150.0` or in exponent
form), whitespace and a trailing newline. The header members MUST be exactly `alg` `"ES256"` and `typ` `"JWT"`, in any
order. Why: every verifier parses values and rebuilds only the GID bytes. Settles: KEYS-61, GID-38, SETTLE-19,
SETTLE-34, HTTP-17, HTTP-70, VERIFYKEYS-06.

<a id="p-optional-surface"></a>**P-optional-surface. Optional SDK surface.** The required surface is listed in section
3.1. Generic JWT helpers, standalone GID verification, exported canonical bytes, per-endpoint functions on a parsed
body and named contract constants are optional (section 3.2). An SDK that offers one MUST apply this spec's segment,
byte, header, key and category rules to it; mapping claims into a structure the caller supplies follows the language's
decoder. This spec defines no gamepass parser. Settles: KEYS-62, GID-42, GID-43, GAMEPASS-36, SETTLE-67, HTTP-61,
HTTP-62, HTTP-63.

<a id="p-body"></a>**P-body. Request body.** An SDK that sees the raw body MUST read up to 65536 bytes, counted over
every byte received; a longer body is answered `400 {"error":"invalid request body"}`. The body MUST then pass the byte
rules ([P-utf8](#p-utf8)) and be exactly one JSON value. A non-object body other than `null`, or a token member that is
present but neither a string nor `null`, is `invalid request body`. A `null` body, or an absent or `null` token member,
reads as the empty token, which the token rules then refuse. An adapter for a framework that has already parsed the
body applies the checks it still can. Settles: HTTP-07, HTTP-09, HTTP-10, HTTP-12, HTTP-16, VERIFYKEYS-56,
VERIFYKEYS-57, VERIFYKEYS-61.

<a id="p-routing"></a>**P-routing. Routing and methods.** An SDK MUST serve exactly the path BoostX calls: the API URL
with one trailing `/` removed, followed by `/set-boost`, `/check-bet` or `/verify-keys`. The name is matched
case-sensitively, the query string is ignored, and a `/` after the name gives 404. Every per-endpoint handler MUST check
the method itself, including one the partner routes: a non-POST request is answered 405 with `Allow: POST`. Paths other
than the exact one, percent-decoding and `//` handling follow the host router. A mount prefix is validated at
construction. `/check-bet` is served only when the bet store implements the check. Settles: HTTP-01, HTTP-02, HTTP-03,
HTTP-04, HTTP-66, HTTP-68, VERIFYKEYS-58, VERIFYKEYS-61.

<a id="p-settlement-acceptance"></a>**P-settlement-acceptance. Settlement acceptance and error text.** One call makes
one attempt; there is no retry helper and no retryable classification. Only a 2xx whose capped body (the first 65536
bytes) passes the byte rules and is `{"result":{"ok":true}}` by exact names is an acceptance. Any other outcome is
`api_error` with the status and an error text: the body's `error` member when that is a non-empty string,
`unexpected response` for a 2xx that is not an acceptance, and otherwise exactly `HTTP <status>`. The surrounding
message wording is informative. Why: only BoostX's exact acceptance may stop retries (decision [retry until
ok](#decision-retry-until-ok)), and the status number is the only portable fallback. Settles: SETTLE-53, SETTLE-54,
SETTLE-55, SETTLE-56, SETTLE-63, SETTLE-64, HTTP-59.

<a id="p-cancellation"></a>**P-cancellation. Cancellation and per-attempt time limit.** Each settlement attempt MUST
have one time limit, 30 s by default, that runs from the key-store lookup through reading the capped body. A
cancellation handle the caller has already cancelled fails before the store is consulted. A handler passes the
request's cancellation to store lookups where the platform conventionally does, and sets no timeout of its own. An
absent cancellation handle means none. Settles: KEYS-54, SETTLE-61, SETTLE-62, SETTLE-69, HTTP-31.

<a id="p-currency"></a>**P-currency. Currency code.** `stake.currency` and the settlement payout currency follow one
rule. Absent, `null` or empty is `missing_claim`. Otherwise the value MUST match `^[A-Z]{3,4}$` exactly, ASCII and
case-sensitive, or it is `invalid_claim`. No case mapping is applied, and the SDK does not check whether BoostX serves
the code. BoostX refuses a gamepass whose currency it does not serve when the game opens (decision [one uppercase
currency rule](#decision-currency-case)). Settles: GAMEPASS-14, GAMEPASS-15, GAMEPASS-47.

<a id="p-builder-ids"></a>**P-builder-ids. Builder id rules.** `partner`, `user` and `bet` are required. Absent, `null`
or empty MUST be `missing_claim`, and any other non-string (a number included) `invalid_claim`, never converted to text.
An id that is not well-formed Unicode is `invalid_claim` ([P-surrogates](#p-surrogates)), and so is an id that contains
`:` or is longer than its limit ([GID-09](#gid-09), [GID-10](#gid-10)); whitespace is not checked. Key-store
registration and the verify-keys builders check neither `:` nor length, but an empty partner id given to registration is
also `missing_claim` ([KEYS-56](#keys-56)); a lookup of one is `unknown_partner`,
since no such id can be registered ([KEYS-58](#keys-58)). Why: never coercing a value means a numeric bet id cannot
silently become different signed text. Settles: GAMEPASS-07, GID-35, SETTLE-10, KEYS-56, HTTP-58, GID-09, GID-10,
SETTLE-12, SETTLE-74.

## 3. SDK surface

This section is the catalogue of what an SDK offers, written so that it can be implemented in any language. Each
operation has one entry, named as the vectors name it (FORMAT.md section 6), and each entry gives:

- **Inputs**: each input, whether it is required, and what absent, `null` and 0 mean for it. The general reading is
  [P-null-absent](#p-null-absent) and [P-zero](#p-zero); an entry says where an input differs.
- **Result**: what a successful call returns (the shapes are in 3.3).
- **Errors**: the error categories of section 4, in check order. The rule that defines the order is linked, not
  restated; the first failing check is the one reported ([P-check-order](#p-check-order)).
- **I/O**: whether the call does I/O (a file, a store, the network), and how it is cancelled.
- **Examples**: the JS and Go counterparts. They show one way to meet the entry and never define it.

Argument order, sync or async, and how options and parameter sets are passed follow the language (3.4); the behaviour
and the check order do not. The Go facade package `boostx` re-exports every Go name below (`boostx.MountHandlers`,
`boostx.NewClient`, `boostx.ErrInvalidClaim` and so on) and adds no behaviour.

### 3.1 Required surface

Every SDK MUST offer the operations below, in its platform's idiom (section 3.4). An entry headed by an operation of
FORMAT.md section 6 is a vector operation, which cases call by that name. The other entries look like operation names
but are none: `key.loadPrivateFile` and `key.loadPublicFile` and `http.endpoint` are pinned by their rules and the SDK's
own tests; `keystore.lookup`, `betstore.setBoost` and `betstore.checkBet` are contracts the vectors exercise through the
fake stores of `http.serve` and `client.submit`; `verifykeys.reason` is checked through every case's `reason`, and
`error.check` through every case's category set. The optional `http.adapter` of 3.2 is not vectored either.

#### key.loadPrivate

Loads a private key, the partner's or, in tests, BoostX's, from PEM (section 5.1).

- **Inputs.** `pem`, required: text or bytes. Any other input, absent and `null` included, is the private-key error
  ([KEYS-14](#keys-14)). PKCS#8 and SEC1 are accepted ([KEYS-01](#keys-01)).
- **Result.** A private-key handle of the platform's crypto library, always usable ([KEYS-16](#keys-16),
  [KEYS-63](#keys-63)).
- **Errors.** `invalid_private_key` alone, for every failure. The steps run in the order 5.1 opens with: input,
  literal escapes, block selection, framing, body encoding, the label's format, DER content ([KEYS-13](#keys-13)).
- **I/O.** None. It may be asynchronous where the platform's key import is.
- **Examples.** JS `loadPrivateKeyFromPEM(pem)`; Go `keys.LoadPrivateKeyFromPEM(pemData)`.

#### key.loadPublic

Loads a public key, the BoostX public key or a partner public key, from PEM (section 5.1).

- **Inputs.** `pem`, required: text or bytes, as for `key.loadPrivate`. Only an SPKI block (`PUBLIC KEY`) is accepted
  ([KEYS-02](#keys-02)).
- **Result.** A public-key handle of the platform's crypto library, always usable ([KEYS-16](#keys-16)).
- **Errors.** `invalid_public_key` alone, for every failure, in the same step order; the DER content rule is
  [KEYS-12](#keys-12).
- **I/O.** None. It may be asynchronous where the platform's key import is.
- **Examples.** JS `loadPublicKeyFromPEM(pem)`; Go `keys.LoadPublicKeyFromPEM(pemData)`.

#### key.loadPrivateFile and key.loadPublicFile

Read a key file and load it, on a platform with a filesystem ([KEYS-15](#keys-15)). Not vectored: the vectors read no
files.

- **Inputs.** `path`, required.
- **Result.** As `key.loadPrivate` or `key.loadPublic`, which receive the bytes read, unchanged.
- **Errors.** A read failure is the role's invalid-key error, with the operating system's error inspectable through the
  cause chain; then the PEM loader's errors.
- **I/O.** Reads a file; it may be asynchronous.
- **Examples.** JS `loadPrivateKeyFromFile(path)`, `loadPublicKeyFromFile(path)` (from the
  `@boostxinnovation/partner-sdk/node` entry); Go `keys.LoadPrivateKeyFromFile(path)`,
  `keys.LoadPublicKeyFromFile(path)`.

#### keystore.register

Registers one partner's keys in the SDK's in-memory key store, which implements both key-store contracts of
`keystore.lookup` ([KEYS-56](#keys-56) to [KEYS-59](#keys-59)).

- **Inputs.** `partner`, required: absent, `null`, empty or not a string is `missing_claim`. Three roles, each
  optional, where absent and `null` mean the role is left out: `partnerPublicKey`, one key or a list (a list that is
  given must not be empty); `partnerPrivateKey`; `boostxPublicKey`. Whether one key can be given without a list is how
  the parameter is passed (section 3.4): JS takes either in one option and Go has a method for each, while an SDK that
  takes only a list gets one key as a one-element list, which registers the same key set ([HTTP-64](#http-64)).
- **Result.** None. The partner's whole key set is added or replaced at once, and a list is copied.
- **Errors.** In the order of [KEYS-57](#keys-57): the partner id (`missing_claim`); the partner public keys, an
  empty list and then each entry in order (`invalid_public_key`); the partner private key (`invalid_private_key`); the
  BoostX public key (`invalid_public_key`). On a refusal the earlier registration of that partner stays.
- **I/O.** None. Registration is safe while requests are served ([KEYS-59](#keys-59)).
- **Examples.** JS `new MemoryKeyStore()`, `register(partner, {partnerPublicKey?, partnerPrivateKey?,
  boostxPublicKey?})`; Go `keys.NewMemoryKeyStore()`, `Register(partner, partnerPub, partnerPriv, boostxPub)` and
  `RegisterWithPartnerPublicKeys(partner, partnerPubs, partnerPriv, boostxPub)`.

#### keystore.lookup

The key-store contracts: the lookups the handlers and the settlement client make, by partner id. The partner implements
them over its own key storage; the in-memory store implements them too (`keystore.register`, whose vectors run its
lookups). The rules are section 5.7.

- **Lookups.** A handler key store answers `partnerPublicKeys(partner)` with a list, the current key first
  ([HTTP-64](#http-64)), `partnerPrivateKey(partner)` with the key that signs the `/verify-keys` response, and
  `boostxPublicKey(partner)` with the key that verifies BoostX's tokens ([KEYS-44](#keys-44)). A client key store
  answers `partnerPrivateKey(partner)` only.
- **Inputs.** The partner id exactly as the token or the parameters give it, matched byte for byte, never folded,
  trimmed or normalised ([KEYS-48](#keys-48)); and the call's cancellation handle where the platform conventionally
  passes one to such calls ([KEYS-54](#keys-54), [HTTP-31](#http-31)).
- **Result.** A key, or a list for the partner public keys. A lookup that returns no usable key is not a lookup
  failure: the caller refuses the key ([KEYS-53](#keys-53), [SETTLE-60](#settle-60)).
- **Errors.** `unknown_partner` for an id the store does not serve, never a fallback key ([HTTP-69](#http-69)); the SDK
  gives stores a way to raise it. The in-memory store answers a role that was left out with that role's invalid-key
  error ([KEYS-58](#keys-58)). Any other error is the store's own; what the handlers and the client do with each
  outcome is [KEYS-50](#keys-50) and [SETTLE-60](#settle-60).
- **I/O.** A store may do I/O, so the SDK calls it as the platform calls I/O (asynchronously where that is the idiom,
  section 3.4). It must tolerate concurrent calls and calls after another lookup failed ([KEYS-52](#keys-52)); the SDK's
  documentation says so.
- **Examples.** JS `HandlersKeyStore` (`partnerPublicKeys`, `partnerPrivateKey`, `boostxPublicKey`) and
  `ClientKeyStore` (`partnerPrivateKey`), raising a `BoostxError` with code `unknown_partner`; Go `handlers.KeyStore`
  (`PartnerPublicKey`, `PartnerPrivateKey`, `BoostxPublicKey`, each taking a `context.Context`) with the optional
  `handlers.PartnerPublicKeysStore` (`PartnerPublicKeys`), and `client.KeyStore` (`PartnerPrivateKey(ctx, partner)`),
  returning an error that wraps `keys.ErrUnknownPartner`.

#### gid.build

Signs a GID: `buildGID` in sections 6 and 7 (section 6.3).

- **Inputs.** `key`, the partner private key, required. `partner`, `user`, `bet`, required strings: absent, `null` or
  empty is `missing_claim`, and any other non-string `invalid_claim`, never converted to text
  ([GAMEPASS-07](#gamepass-07)).
- **Result.** The signed GID: the three ids exactly as given and an 86-character `signature` ([GID-14](#gid-14)).
- **Errors.** List A of [KEYS-19](#keys-19): `invalid_private_key`; the ids' presence and type; their well-formedness,
  `:` and length (`invalid_claim`); a signing failure (`invalid_private_key`). The field tokens are `partner`, `user`
  and `bet`.
- **I/O.** None. It may be asynchronous where the platform's signing is.
- **Examples.** JS `buildGID(privateKey, partner, user, bet)`; Go `tokens.BuildGID(partner, user, bet, privateKey)`,
  which takes the key last.

#### gamepass.create

Signs a GamePassJWT, which the partner puts in the game URL: the gamepass builder of section 7.

- **Inputs.** `key`, the partner private key, required. `params`, one parameter set, in which `partner`, `user`,
  `bet` and `currency` are required (absent, `null` or empty is `missing_claim`) and so are `amount` and `x` (absent,
  `null` or 0 is `invalid_claim`); `xMin`, `xMax` and `xDecimals` are optional (absent, `null` or 0 is unset);
  `eventTitle` is optional (absent, `null` or empty is unset); `demo` is optional, and only `true` is sent. A missing
  parameter set reads as an empty one ([GAMEPASS-48](#gamepass-48)). The table at the start of section 7 lists the
  parameters with the field token each error names.
- **Result.** The token text, whose payload is [GAMEPASS-01](#gamepass-01); `iat` is the call's own time.
- **Errors.** List B of [KEYS-19](#keys-19): `invalid_private_key`, then `missing_claim` or `invalid_claim` for the
  first failing parameter, then a signing failure as `invalid_private_key`.
- **I/O.** None; it reads the clock. It may be asynchronous where the platform's signing is.
- **Examples.** JS `createGamePassToken(privateKey, params)`; Go `tokens.CreateGamePassToken(privateKey, params)`.

#### settlement.create

Signs a SettlementJWT: the settlement builder of section 9.

- **Inputs.** `key`, the partner private key, required. `params`, one parameter set (section 9.2): `partner`,
  `user`, `bet`, `currency` and `settledAt` are required (absent or `null` is `missing_claim`, and so is `""` for the
  strings and 0 for `settledAt`); `status`, `amount` and `version` are required, and absent or `null` is
  `invalid_claim` ([SETTLE-70](#settle-70), [SETTLE-18](#settle-18)); 0 is a legal `amount` and `version`, so an SDK
  that cannot tell them unset from 0 sends 0 and documents it; `xSettle` is optional (absent or `null` leaves it out,
  0 is written). A missing parameter set reads as an empty one.
- **Result.** The token text, whose payload is section 9.1; `iat` is the call's own time.
- **Errors.** [SETTLE-31](#settle-31): `invalid_private_key`, then `missing_claim` or `invalid_claim` for the first
  failing parameter, then a signing failure as `invalid_private_key`. The field tokens are in the table of section 9.2.
- **I/O.** None; it reads the clock (the `settledAt` ceiling, [SETTLE-29](#settle-29)). It may be asynchronous where
  the platform's signing is.
- **Also required.** The eight statuses are exposed as public names ([SETTLE-14](#settle-14)).
- **Examples.** JS `createSettlementToken(privateKey, params)`, `SETTLEMENT_STATUSES`; Go
  `tokens.CreateSettlementToken(privateKey, params)`, `tokens.StatusWin` and the other `Status*` constants.

#### verifykeys.createRequest

Signs a verify-keys request as BoostX would, so that a partner can test its endpoint offline: a test aid under the
SDK's own rules ([VERIFYKEYS-67](#verifykeys-67)).

- **Inputs.** `key`, the private key that stands in for BoostX's, required. `partnerID`, required: absent, `null`,
  empty or not a string is `missing_claim`, and `"boostx"` is `invalid_claim` ([VERIFYKEYS-09](#verifykeys-09)).
  `nonce`, required: an integer in [1, 2147483647]; anything else, absent and `null` included, is `invalid_claim`
  ([VERIFYKEYS-48](#verifykeys-48)).
- **Result.** The token text, the request of [VERIFYKEYS-06](#verifykeys-06).
- **Errors.** [VERIFYKEYS-49](#verifykeys-49): `invalid_private_key`; the partner id; the nonce; the partner id's
  well-formedness (`invalid_claim`). The field tokens are `partnerID` and `nonce`.
- **I/O.** None; it reads the clock. It may be asynchronous where the platform's signing is.
- **Examples.** JS `createVerifyKeysRequestToken(boostxPrivateKey, partnerID, nonce)`; Go
  `tokens.CreateVerifyKeysRequestToken(boostxPriv, partnerID, nonce)`, with an `int32` nonce.

#### verifykeys.createResponse

Signs the verify-keys response a partner returns from `/verify-keys`.

- **Inputs.** As `verifykeys.createRequest`, with the partner private key as `key`.
- **Result.** The token text, the response of [VERIFYKEYS-07](#verifykeys-07) and [VERIFYKEYS-69](#verifykeys-69).
- **Errors.** As `verifykeys.createRequest` ([VERIFYKEYS-49](#verifykeys-49)).
- **I/O.** None; it reads the clock. It may be asynchronous where the platform's signing is.
- **Examples.** JS `createVerifyKeysResponseToken(partnerPrivateKey, partnerID, nonce)`; Go
  `tokens.CreateVerifyKeysResponseToken(partnerPriv, partnerID, nonce)`.

#### x.floor

Floors a coefficient by BoostX's rule: `floorX` in section 7.6.

- **Inputs.** `x`, a number, required. `decimals`, optional: absent, `null` or 0 means 2; otherwise an integer from 2
  to 6 ([GAMEPASS-40](#gamepass-40)).
- **Result.** A binary64 number, computed as [GAMEPASS-38](#gamepass-38) says.
- **Errors.** `decimals` outside its domain gives `invalid_claim` or NaN, never a finite number, implementation-defined
  which ([GAMEPASS-40](#gamepass-40)); a non-finite `x` gives `invalid_claim` or a non-finite result, never a finite
  one ([GAMEPASS-41](#gamepass-41)).
- **I/O.** None.
- **Examples.** JS `floorX(x, decimals?)`; Go `tokens.FloorX(x, decimals)`.

#### x.player

The X the player saw for a Booster's `boost`: `playerX` in section 7.6.

- **Inputs.** `xBase` and `boost`, numbers, required. `decimals` as for `x.floor`.
- **Result.** A binary64 number, `floorX(1 + (floorX(xBase, d) - 1) × boost, d)` with no clamp
  ([GAMEPASS-42](#gamepass-42), [GAMEPASS-43](#gamepass-43), [GAMEPASS-49](#gamepass-49)).
- **Errors.** As `x.floor`, for `decimals` and for non-finite `xBase` or `boost`.
- **I/O.** None.
- **Examples.** JS `playerX(xBase, boost, decimals?)`; Go `tokens.PlayerX(xBase, boost, decimals)`.

#### booster.extract

Reads the partner id of a BoosterJWT without verifying it, so that a handler can choose keys (section 8.4).

- **Inputs.** `token`, required text.
- **Result.** `gid.partner`, unverified.
- **Errors.** `invalid_booster`, alone for a malformed token and with its cause for a claim fault; extraction runs
  steps 2.1, 2.7 and 3 of [INBOUND-32](#inbound-32) and nothing else ([KEYS-27](#keys-27)).
- **I/O.** None, and no key; it reads the clock (`exp`, `nbf`).
- **Examples.** JS `extractBoosterPartner(token)`; Go `tokens.ExtractBoosterPartner(token)`.

#### booster.parse

Verifies a BoosterJWT and its GID, and returns its claims (section 8).

- **Inputs.** `token`, required text. `boostxKey`, the BoostX public key, required: absent, `null` or unusable is
  `invalid_public_key`. `partnerKeys`, the partner public keys as a list, required: absent, `null`, empty or holding
  no usable key is `invalid_public_key`; unusable entries are skipped ([KEYS-45](#keys-45)). A single-key form is
  optional and behaves as a one-element list.
- **Result.** A Booster (3.3).
- **Errors.** [INBOUND-32](#inbound-32): the keys (`invalid_public_key` alone, never wrapped), the JWS, the claims, the
  GID. A key the platform refuses only while verifying is `invalid_public_key` alone too (steps 2.6 and 4.2,
  [INBOUND-60](#inbound-60)). Every other fault is `invalid_booster`, with a cause for a claim, signature or GID fault
  ([INBOUND-44](#inbound-44) to [INBOUND-46](#inbound-46)).
- **I/O.** None; it reads the clock. It may be asynchronous where the platform's verification is.
- **Examples.** JS `parseBoosterToken(token, boostxPublicKey, partnerPublicKeys)`; Go
  `tokens.ParseBoosterTokenWithKeys(token, boostxPub, partnerPubs)`.

#### checkbet.extract

As `booster.extract`, for a CheckBetJWT: the category is `invalid_checkbet`, and the root has no fields of its own.

- **Examples.** JS `extractCheckBetPartner(token)`; Go `tokens.ExtractCheckBetPartner(token)`.

#### checkbet.parse

As `booster.parse`, for a CheckBetJWT: the category is `invalid_checkbet`, and the result is a CheckBet (3.3).

- **Examples.** JS `parseCheckBetToken(token, boostxPublicKey, partnerPublicKeys)`; Go
  `tokens.ParseCheckBetTokenWithKeys(token, boostxPub, partnerPubs)`.

#### verifykeys.extractRequest

Reads the partner id (`aud`) of a verify-keys request without verifying it, so that a handler can choose keys.

- **Inputs.** `token`, required text.
- **Result.** `aud`, unverified and unchanged ([VERIFYKEYS-72](#verifykeys-72)).
- **Errors.** `invalid_verify_keys` with reason `shape`, in the steps of [VERIFYKEYS-10](#verifykeys-10).
- **I/O.** None, and no key.
- **Examples.** JS `extractVerifyKeysRequestPartner(token)`; Go `tokens.ExtractVerifyKeysRequestPartner(token)`.

#### verifykeys.parseRequest

Verifies a verify-keys request (section 10).

- **Inputs.** `token`, required text. `key`, the BoostX public key, required. `partnerID`, required, refused by items 1
  and 2 of [VERIFYKEYS-09](#verifykeys-09); a parser does not test its well-formedness, so an ill-formed one fails as
  `iss-aud`. `windowSeconds`, required surface that a call may leave out ([KEYS-41](#keys-41)): absent, `null` or 0
  means 30 seconds; a negative or non-finite value is `invalid_claim`; any other value is truncated toward zero to whole
  seconds. The window takes fractions of a second, as KEYS-41 requires: `0.5` gives a zero-second window, `60.9` a
  60-second one, and `-0.5` is `invalid_claim`; the vectors that pass a fraction carry no `needs` tag.
- **Result.** A verify-keys request: `partnerID`, `nonce`, `iat` (3.3).
- **Errors.** [VERIFYKEYS-46](#verifykeys-46): steps A1 to A3 (`invalid_public_key`, then `missing_claim` or
  `invalid_claim` for the partner id, then `invalid_claim` for the window), then steps 1 to 5, each refusal
  `invalid_verify_keys` with one reason. The category sets are [VERIFYKEYS-53](#verifykeys-53).
- **I/O.** None; it reads the clock. It may be asynchronous where the platform's verification is.
- **Examples.** JS `parseVerifyKeysRequestToken(token, boostxPublicKey, partnerID, {maxSkewSeconds}?)`; Go
  `tokens.ParseVerifyKeysRequestToken(token, boostxPub, partnerID, maxSkew)`, where `maxSkew` is a `time.Duration`.

#### verifykeys.parseResponse

Verifies a verify-keys response as BoostX would read it under the SDK's rules: a test aid
([VERIFYKEYS-67](#verifykeys-67)).

- **Inputs.** As `verifykeys.parseRequest`, with the partner public key as `key`; the expected `iss` is the partner id
  and the expected `aud` is `"boostx"` ([VERIFYKEYS-34](#verifykeys-34)).
- **Result.** A verify-keys response: `partnerID`, `nonce`, `iat` (3.3).
- **Errors.** As `verifykeys.parseRequest`.
- **I/O.** None; it reads the clock. It may be asynchronous where the platform's verification is.
- **Examples.** JS `parseVerifyKeysResponseToken(token, partnerPublicKey, partnerID, {maxSkewSeconds}?)`; Go
  `tokens.ParseVerifyKeysResponseToken(token, partnerPub, partnerID, maxSkew)`.

#### verifykeys.reason

The reason mapper: the wire reason of any error (section 4.3).

- **Inputs.** Any error value, an absent one included.
- **Result.** One of `signature`, `shape`, `iss-aud`, `stale`, `nonce-format`, chosen in the order of
  [VERIFYKEYS-52](#verifykeys-52) ([KEYS-60](#keys-60)).
- **Errors.** None; it never fails.
- **I/O.** None.
- **Examples.** JS `verifyKeysReason(err)`; Go `tokens.VerifyKeysReason(err)`.

#### client.submit

Sends one settlement: `submitSettlement` in section 9. The client is constructed once and submits many times.

- **Inputs at construction.** `keyStore`, a client key store (`keystore.lookup`), required: absent is a construction
  error ([SETTLE-35](#settle-35)). Options, each optional: `options.baseURL` (absent or `null` selects
  `https://partners-s2s.boostx.cloud`; an empty string is refused; normalised and validated by
  [SETTLE-37](#settle-37) to [SETTLE-39](#settle-39)); `options.timeoutMs`, the per-attempt time limit (absent,
  `null` or 0 means 30 seconds, a negative or non-finite value is refused; its unit is the SDK's,
  [SETTLE-61](#settle-61)); and the transport, which the caller can inject ([SETTLE-68](#settle-68)).
- **Inputs at each call.** `params`, the settlement parameters of `settlement.create`. `cancel`, a cancellation
  handle, optional: absent or `null` means none ([SETTLE-69](#settle-69)).
- **Result.** Nothing, on BoostX's acceptance ([SETTLE-50](#settle-50)).
- **Errors.** At construction, `invalid_claim`, or a panic or abort where the language prefers ([SETTLE-35](#settle-35),
  [HTTP-48](#http-48)). At a call, in the order of [SETTLE-59](#settle-59): a handle already cancelled; the key store's
  error, category intact (`unknown_partner`, or the role error of an in-memory store); the builder's errors
  ([SETTLE-31](#settle-31)); then the send, where the failures outside the taxonomy (cancellation, time limit, network,
  a failed body read) pass through as section 4.4 says, and any answer that is not an acceptance is `api_error` with the
  HTTP status and the error text of [SETTLE-56](#settle-56). One call makes one attempt, with no retry
  ([SETTLE-63](#settle-63)).
- **I/O.** A key-store lookup and one HTTP request; asynchronous where that is the platform's idiom (section 3.4). The
  time limit covers the lookup through the body read; cancellation stops the call at once in any step
  ([SETTLE-62](#settle-62), [SETTLE-76](#settle-76)).
- **Examples.** JS `new BoostxClient(keyStore, {baseURL?, fetch?, timeoutMs?})`,
  `client.submitSettlement(params, {signal}?)`, failing with `BoostxAPIError` (`status`, `error`); Go
  `client.New(ks, client.WithBaseURL(url), client.WithHTTPClient(hc))`, where the `Timeout` of the `http.Client` `hc` is
  the time limit, `(*client.Client).SubmitSettlement(ctx, params)`, failing with `*client.APIError` (`StatusCode`,
  `Message`).

#### http.serve

The router: one entry point that answers all three of BoostX's calls (section 11, [HTTP-66](#http-66)).

- **Inputs at construction.** `betStore`, required, with `betstore.setBoost`; `betstore.checkBet` is optional, and
  without it `/check-bet` answers 404 ([HTTP-05](#http-05)). `keyStore`, a handler key store with all three lookups
  (`keystore.lookup`), required. `mount`, the mount prefix, where the router takes one, validated as
  [HTTP-68](#http-68) says.
- **Inputs at each request.** One HTTP request, which conformance reads as the core
  `handle(method, path, bodyBytes, cancel?)` of [HTTP-73](#http-73).
- **Result.** An answer `{status, headers, body}`, from the complete answer list of 11.3. A failure a store reports is
  answered, never raised ([HTTP-28](#http-28)).
- **Errors.** At construction, a missing or incomplete store or a refused prefix is `invalid_claim`, or a panic or
  abort where the language prefers ([HTTP-48](#http-48)). At a request, the answer follows the steps of
  [HTTP-21](#http-21): route, body, unverified extraction, key lookups, parse, bet store.
- **I/O.** Reads the request body and calls both stores. The request's own cancellation is passed to the stores where
  the platform conventionally does ([HTTP-31](#http-31)); the router sets no timeout.
- **Examples.** JS `createFetchHandler({betStore, keyStore})`, a function from `Request` to `Response`, and
  `createNodeHandler(options)` from the `/node` entry, for `node:http` and Express; Go
  `handlers.Mount(mux, prefix, betStore, keyStore)` on an `http.ServeMux`.

#### http.endpoint

A unit per endpoint, for a partner who routes the requests itself, in one of two forms ([HTTP-66](#http-66)). Not
vectored: `http.serve` drives the router.

- **An HTTP handler**, constructed with what its endpoint needs ([HTTP-48](#http-48): `/verify-keys` needs only the key
  store, [HTTP-46](#http-46)), which checks the method itself ([HTTP-03](#http-03)) and answers exactly as the router.
  On a platform with no single server interface, where the router is a function of the core's shape
  ([HTTP-66](#http-66)), the same function built for one endpoint and taking no path, `handle(method, bodyBytes,
  cancel?)`, is such a handler.
- **Or a function on a parsed body** that returns a status and a body equal to the router's answer for that body, and
  answers 500 `internal server error` while its configuration is invalid ([HTTP-61](#http-61)).
- **Examples.** JS `handleSetBoost(body, options)`, `handleCheckBet(body, options)`, `handleVerifyKeys(body,
  {keyStore})`; Go `handlers.NewSetBoostHandler(store, keyStore)`, `NewCheckBetHandler(store, keyStore)`,
  `NewVerifyKeysHandler(keyStore)`.

#### betstore.setBoost

The bet-store contract for a round, implemented by the partner and called by the SDK (section 11.6).

- **Inputs.** The verified Booster (3.3), for every verified round, repeated and older rounds included
  ([HTTP-29](#http-29)); and the request's cancellation handle where the platform conventionally passes one
  ([HTTP-31](#http-31)).
- **Result.** Success, answered 200 ([HTTP-19](#http-19)). The store is idempotent: a round at or below the stored one
  changes nothing and succeeds; the SDK's documentation says so.
- **Errors.** The round-rejection marker, raised by the store or anywhere in its error's cause chain, is answered 400
  `round rejected`; any other error 500 `failed to set boost` ([HTTP-27](#http-27)). The SDK provides the marker; it is
  an input, not an SDK error category.
- **I/O.** The partner's own.
- **Examples.** JS `BetStore.setBoost(booster)`, rejecting with `RoundRejectedError`; Go
  `handlers.BetStoreUpdater.SetBoost(ctx, booster)`, returning `handlers.ErrRoundRejected`.

#### betstore.checkBet

The optional bet-store check before a round, implemented by the partner (section 11.6).

- **Inputs.** The verified signed GID; the request's cancellation handle as for `betstore.setBoost`.
- **Result.** A boolean verdict, answered 200 `{"result":{"active":…}}` ([HTTP-32](#http-32)). A bet the partner does
  not know is `false`, not an error ([HTTP-34](#http-34)).
- **Errors.** Any error, or a verdict that is not a boolean, is answered 500 `failed to check bet`
  ([HTTP-33](#http-33), [HTTP-34](#http-34)).
- **I/O.** The partner's own.
- **Examples.** JS `BetStore.checkBet(gid)`, left out when the store has no check; Go
  `handlers.BetStoreChecker.CheckBet(ctx, gid)`, implemented or not.

#### error.check

Tells whether an error carries a category of section 4.1.

- **Inputs.** An error value and a category.
- **Result.** True when the category is anywhere in the error's cause chain, found by the language's standard walk or
  by a walk of at least 16 levels (section 4.1). The API error also exposes its status and error text
  ([SETTLE-57](#settle-57)); a verify-keys error's reason is read with `verifykeys.reason`.
- **Errors.** None.
- **I/O.** None.
- **Examples.** JS `isBoostxError(err, code)` on a `BoostxError` (`code`, `message`, `cause`, `reason`); Go
  `errors.Is(err, tokens.ErrInvalidClaim)` with the sentinels of 4.2, and `errors.As` for `*client.APIError`.

### 3.2 Optional surface

Implementation-defined: which items of the optional surface an SDK offers, those in the table and `http.adapter` below
and any item a rule calls optional surface. An item an SDK offers MUST follow the rules named
([P-optional-surface](#p-optional-surface)).

| Item | Rules | Examples |
|------|-------|----------|
| Generic JWT helpers: sign, parse, extract claims | [KEYS-62](#keys-62), [HTTP-62](#http-62) | Go `tokens.SignJWT`, `tokens.ParseJWT`, `tokens.ExtractJWTClaims`; JS none |
| Standalone GID verification, with one key | [GID-43](#gid-43) | Go `tokens.VerifyGID(gid, publicKey)`; JS internal only |
| Canonical GID bytes | [GID-42](#gid-42) | neither SDK exports them |
| Single-key parser forms | section 8 | Go `tokens.ParseBoosterToken`, `tokens.ParseCheckBetToken`; JS accepts one key where the list goes |
| Functions on a parsed body (optional where the SDK offers per-endpoint HTTP handlers, `http.endpoint`) | [HTTP-61](#http-61) | JS `handleSetBoost`, `handleCheckBet`, `handleVerifyKeys`; Go none |
| Named contract constants | [HTTP-63](#http-63) | JS `BOOSTX_IDENTITY`, `DEFAULT_VERIFY_KEYS_MAX_SKEW_SECONDS`, `DEFAULT_BASE_URL`; Go `tokens.BoostxIdentity`, `tokens.VerifyKeysReason*`, `client.DefaultBaseURL` |
| Raw X helper, unfloored | [GAMEPASS-43](#gamepass-43) | Go `tokens.CalculateFinalCoefficient`; JS none |
| A gamepass parser | [GAMEPASS-36](#gamepass-36), outside conformance | Go's deprecated `tokens.ParseGamePassToken`, `tokens.ExtractGamePassClaims`; JS none |

#### http.adapter

An adapter that serves the endpoints inside a web framework that has already read the request body
([HTTP-16](#http-16), [VERIFYKEYS-61](#verifykeys-61)). Optional; not vectored, since adapters sit outside the
conformance core.

- **Inputs.** What the framework hands over: the parsed or raw body, the method and the path.
- **Result.** The router's answer, as far as the framework's own parsing lets it be: the 65536-byte cap on what it can
  measure, 400 `invalid request body` when nothing was left for it, and the routing answers (404, 405).
- **Examples.** JS `createNodeHandler`, which reads `req.body` when the stream has already ended; Go none (`net/http`
  only).

### 3.3 Result shapes

| Result | Fields, in neutral names | JS | Go |
|--------|--------------------------|----|----|
| Signed GID | `partner`, `user`, `bet`, `signature`: strings | `GID` | `tokens.GID` (`Partner`, `User`, `Bet`, `Signature`) |
| Booster | `gid` (a signed GID); `round`, an integer from 1 to 2^53−1; `boost`, a finite binary64 number above 0; `final`, `jackpot`: booleans; `iat` | `Booster` (`gid`, `round`, `boost`, `final`, `jackpot`, `iat`) | `tokens.Booster`: embedded `GID`, `Round`, `Boost`, `Final`, `Jackpot`, `IssuedAt` |
| CheckBet | `gid`, `iat` | `CheckBet` (`gid`, `iat`) | `tokens.CheckBet`: embedded `GID`, `IssuedAt` |
| Verify-keys request | `partnerID` (its `aud`), a string; `nonce`, an integer in [1, 2147483647]; `iat` | `VerifyKeysRequest` (`partnerID`, `nonce`, `iat`) | `tokens.VerifyKeysRequest` (`PartnerID`, `Nonce int32`, `IssuedAt` from the embedded `RegisteredClaims`) |
| Verify-keys response | `partnerID` (its `iss`), `nonce`, `iat` | `VerifyKeysResponse` | `tokens.VerifyKeysResponse`, same fields |
| A built token | the compact JWS text | `string` | `string` |
| API error | category `api_error`; the HTTP status, an integer; the error text, a string | `BoostxAPIError` (`status`, `error`) | `*client.APIError` (`StatusCode`, `Message`) |

`iat` is integer Unix seconds as received, of magnitude up to 2^53−1, so it needs a 64-bit integer or a binary64
number ([P-iat-exposed](#p-iat-exposed)). Rules: [HTTP-65](#http-65), [VERIFYKEYS-54](#verifykeys-54),
[INBOUND-42](#inbound-42). The field names are neutral: an SDK names its fields, or the accessors that read them, in
its language's style (section 3.4, Names), as Go names `iat` `IssuedAt`; where a neutral name is a reserved word
(`final` in Java), the language's usual way around it serves (an accessor `isFinal()`). The values and their types are
fixed.

### 3.4 Parameter conventions

- **Null and absent.** [P-null-absent](#p-null-absent): where a language tells `null` from absence, `null` means
  absent. Where a language cannot express absence (a struct field), the zero value stands for it as [P-zero](#p-zero)
  says, and the vectors' `wantZeroValue` covers the cases where that differs (section 12.4).
- **Key position.** Implementation-defined: the order of the arguments, and any overloads, in the language's idiom (Go
  `tokens.BuildGID` takes the key last). The neutral order is the signing key first for a builder, and for a parser the
  token first, then the BoostX key, then the partner key or keys or the partner id. The order of checks does not change
  with the order of arguments ([P-check-order](#p-check-order)).
- **Parameter sets.** Gamepass and settlement parameters are one set each (an object, a struct, a record, named
  arguments). The neutral names are `partner`, `user`, `bet`, `amount`, `currency`, `x`, `xMin`, `xMax`, `xDecimals`,
  `eventTitle`, `demo` for a gamepass, and `partner`, `user`, `bet`, `status`, `amount`, `currency`, `version`,
  `xSettle`, `settledAt` for a settlement. Their neutral types: the ids, `currency`, `eventTitle` and `status` are
  strings; `amount`, `x`, `xMin`, `xMax` and `xSettle` are binary64 numbers; `xDecimals` is an integer from 2 to 6;
  `demo` is a boolean; `version` is an integer up to 2^53−1 and `settledAt` an integer of epoch milliseconds, so both
  need a 64-bit integer or a binary64 number (a 32-bit integer overflows). In a language whose numbers can hold a value
  no binary64 holds (Python's arbitrary-precision `int`, a decimal type), a parameter of binary64 type stands for the
  binary64 nearest the value given: that is the value the checks judge and the token carries, "the given value" of
  [GAMEPASS-01](#gamepass-01) and [SETTLE-20](#settle-20). A value too large to round to a finite binary64 stands for
  the infinity of its sign, as IEEE 754 rounding to nearest gives (a magnitude below 2^1024 − 2^970 still rounds to the
  largest finite binary64; Python's `float()` raises `OverflowError` exactly where the result would be infinite), which
  the checks then refuse as non-finite. An integer parameter is judged by its exact value.
- **Number types.** Implementation-defined: which of the language's number types a numeric parameter accepts. A Python
  SDK may take `int`, `float`, `decimal.Decimal` and `fractions.Fraction`, each judged as the previous bullet says; JS
  takes a `number` and refuses a `bigint`; Go's parameters are typed. Fixed for every SDK: a string is never a number,
  however it is spelled (the cases tagged `untyped-number`), and neither is a boolean, even where the language makes it
  one (Python's `bool` is an `int`; test `type(x) is bool` first, as [VERIFYKEYS-70](#verifykeys-70) does).
- **Names.** Implementation-defined: the names an SDK gives its parameters, options and parameter-set members, and the
  fields of its results (3.3) and how a result nests them, in its language's style (Python `settled_at` or `settledAt`,
  Go `SettledAt`, `IssuedAt` and the GID's fields embedded in a Booster, a Java accessor `isFinal()`). One spelling per
  name, documented, serves partners best: a key-value map that an SDK reads under two spellings is ambiguous when it
  carries both. The names do not change what is fixed: the wire names of every token and body, the error categories, and
  the field tokens of [HTTP-72](#http-72), which stay the neutral spellings (`settledAt`, `xmin`) whatever the SDK calls
  the parameter, so that every SDK's errors name a field the same way. The one exception is the verify-keys window,
  whose token is the language's own name ([VERIFYKEYS-39](#verifykeys-39)).
- **Parameter-set kinds.** Implementation-defined: which kinds of value an SDK reads a parameter set from, which its
  documentation says: in JS any object; in a dynamically typed language, typically a key-value map or the SDK's own
  parameter type. An SDK that defines a parameter type of its own (a Python dataclass, for example) reads it, since a
  partner who builds one expects it to count. A value of no such kind is "not an object" in the sense of
  [GAMEPASS-48](#gamepass-48), and reads as an empty set. A key-value map's keys are the SDK's spelling of the names
  (Names, above); a key it does not define is ignored ([GAMEPASS-33](#gamepass-33), [SETTLE-05](#settle-05)), so a key
  spelt another way reads as absent and its parameter fails as absent does. That silence can mislead a partner who ports
  an example written with the neutral names to an SDK that spells them otherwise: `xMin` given to an SDK that reads
  `x_min` leaves the minimum to BoostX's default. [GAMEPASS-50](#gamepass-50) lets such an SDK refuse that key instead.
- **Sync or async.** Implementation-defined: whether each operation is synchronous or asynchronous. An operation whose
  entry does I/O is usually asynchronous where the platform's I/O is; one that only signs or verifies may be
  asynchronous where the platform's crypto is. JS returns promises for everything that touches Web Crypto or a store and
  is synchronous for extraction and the X helpers; Go is synchronous and passes a `context.Context` to stores and the
  client.
- **Cancellation.** `client.submit` takes the platform's standard cancellation primitive, or a token type the SDK
  defines where the platform has none ([SETTLE-76](#settle-76)). Handlers pass the request's own cancellation to the
  stores where the platform does so ([P-cancellation](#p-cancellation)). JS takes an `AbortSignal` (`{signal}`); Go
  takes the context.

<a id="keys-68"></a>**KEYS-68. The clock.** Every time an SDK uses (the builders' `iat`, the `settledAt` ceiling, the
`exp` and `nbf` checks and the verify-keys window) MUST come from the system clock by default.

Implementation-defined: an SDK MAY accept an optional clock that defaults to the system time. A conformance runner MUST
NOT set it: the vectors run against the clock the SDK reads by default, and their time expressions allow for the SDK
reading it after the runner (FORMAT.md section 3.1). (No vector: a runner never sets the clock, so no case can observe
one; FORMAT.md section 3.1.)

## 4. Error taxonomy

### 4.1 Categories and the cause chain

The categories form a closed set ([HTTP-54](#http-54), [P-taxonomy](#p-taxonomy)). An SDK MUST NOT raise an error of
its own without one of them.

| Category | Raised for |
|----------|-----------|
| `invalid_private_key` | A private key that is not a usable ECDSA P-256 private key: at load, at registration, at a builder's key check, or a role left out of a store |
| `invalid_public_key` | A public key that is not usable, or a partner key list with no usable key; never wrapped in a token category |
| `invalid_booster`, `invalid_checkbet`, `invalid_verify_keys` | Any fault of that inbound token; the cause says which |
| `invalid_gid` | A `gid` claim of the wrong shape, or a GID signature in the wrong form or that no listed key verifies (then with `invalid_signature`) |
| `invalid_signature` | A fault that prevents establishing an ES256 signature ([P-signature-vs-shape](#p-signature-vs-shape)) |
| `missing_claim` | A required claim or parameter that is absent, `null` or empty |
| `invalid_claim` | A claim or parameter with a wrong type or value, and every configuration or argument error that is not a key |
| `unknown_partner` | A key store asked for an id it does not serve |
| `api_error` | A settlement answer that is not an acceptance |

`invalid_gamepass` exists only where a gamepass parser is offered (Go's deprecated one) and is outside conformance.

An error carries one category, and its cause chain can add more, as the rules say: a token error is `invalid_<token>`
with a cause of `missing_claim`, `invalid_claim`, `invalid_gid` or `invalid_signature`; a bad GID signature is
`{invalid_<token>, invalid_gid, invalid_signature}`. The vectors compare the set of categories over the whole chain,
exactly (FORMAT.md section 5.1). The chain MUST be walkable by the language's standard check (Go `errors.Is` and
`errors.As`, Java `getCause`, .NET `InnerException`, Python `__cause__`); where an SDK walks it by hand, it walks at
least 16 levels (JS `isBoostxError` does).

Implementation-defined: how errors and their categories are represented (codes on one error type, sentinels, a type
per category), as long as every category is found through the cause chain as above (4.2 shows the JS and Go forms).

### 4.2 Mapping

| Category | JS (`BoostxError.code`) | Go |
|----------|------------------------|----|
| `invalid_private_key` | `invalid_private_key` | `tokens.ErrInvalidPrivateKey` |
| `invalid_public_key` | `invalid_public_key` | `tokens.ErrInvalidPublicKey` |
| `invalid_booster` | `invalid_booster` | `tokens.ErrInvalidBooster` |
| `invalid_checkbet` | `invalid_checkbet` | `tokens.ErrInvalidCheckBet` |
| `invalid_verify_keys` | `invalid_verify_keys` | `tokens.ErrInvalidVerifyKeys`, wrapped by the reason errors of 4.3 |
| `invalid_gid` | `invalid_gid` | `tokens.ErrInvalidGID` |
| `invalid_signature` | `invalid_signature` | `tokens.ErrInvalidSignature` |
| `missing_claim` | `missing_claim` | `tokens.ErrMissingClaim` |
| `invalid_claim` | `invalid_claim` | `tokens.ErrInvalidClaim` |
| `unknown_partner` | `unknown_partner` | `keys.ErrUnknownPartner` |
| `api_error` | `api_error`, on `BoostxAPIError` (extends `BoostxError`) | `*client.APIError`, by `errors.As` |
| `invalid_gamepass` (outside conformance) | none | `tokens.ErrInvalidGamePass` |

JS raises every error as a `BoostxError` (`code`, `message`, `cause`, and `reason` on a verify-keys error) and checks
it with `isBoostxError(err, code)`. Go returns errors that wrap the sentinels with `%w`, checked with `errors.Is`. The
`boostx` facade re-exports each sentinel. The bet store's round rejection (JS `RoundRejectedError`, Go
`handlers.ErrRoundRejected`) is an input the handler reads, not an SDK error.

### 4.3 Verify-keys reasons and the reason mapper

A verify-keys failure carries exactly one wire reason. The reasons, their order and what raises each are in section 10
([VERIFYKEYS-46](#verifykeys-46), [VERIFYKEYS-50](#verifykeys-50) to [VERIFYKEYS-53](#verifykeys-53)).

| Reason | JS (`BoostxError.reason`) | Go |
|--------|---------------------------|----|
| `shape` | `'shape'` | `tokens.ErrVerifyKeysShape` |
| `signature` | none: the error carries `invalid_signature` | `tokens.ErrInvalidSignature` |
| `iss-aud` | `'iss-aud'` | `tokens.ErrVerifyKeysIssAud` |
| `stale` | `'stale'` | `tokens.ErrVerifyKeysStale` |
| `nonce-format` | `'nonce-format'` | `tokens.ErrVerifyKeysNonce` |

The reason mapper (JS `verifyKeysReason(err)`, Go `tokens.VerifyKeysReason(err)`) MUST return `signature` for a
signature failure or an unusable verifying key (`invalid_public_key`), otherwise the error's own reason, and `shape`
for anything else, an error from outside the SDK included ([KEYS-60](#keys-60), [HTTP-57](#http-57)).

### 4.4 Failures outside the taxonomy

Some failures are not the SDK's own. The SDK lets each one through unchanged, or wrapped with the original reachable
as its cause, so that the platform's standard check for that kind of failure still matches it
([SETTLE-58](#settle-58), [SETTLE-62](#settle-62)). They carry no category of 4.1 and are never `api_error`:

| Failure | What the caller gets | JS | Go |
|---------|----------------------|----|----|
| Cancellation | The platform's cancellation error, or that of the SDK's own token type where the platform has none ([SETTLE-76](#settle-76)) | the abort signal's `reason` (an `AbortError` for `controller.abort()`), unchanged | the context's error, wrapped once the lookup has started; `errors.Is(err, context.Canceled)` holds |
| Time limit | The platform's timeout error, or the one its HTTP stack raises when a request's time limit expires | a `TimeoutError` | `errors.Is(err, context.DeadlineExceeded)` holds, or a `net.Error` whose `Timeout()` is true |
| Network | The transport's own error | the transport's error (a `TypeError` from `fetch`), unchanged | the HTTP transport's `*url.Error`, wrapped `send request: %w` |

A store's own error is the partner's. The settlement client lets it reach the caller with its category, if any,
intact ([SETTLE-58](#settle-58), [SETTLE-60](#settle-60)). Handlers answer it by the rules of 11.5 and 11.6 and never
pass it to BoostX.

### 4.5 Message texts

Message texts of SDK errors are not part of the contract and MAY differ between SDKs ([HTTP-60](#http-60)); partners
match errors by category. The HTTP error strings of [P-http-errors](#p-http-errors) and the verify-keys reasons are
contract, and they are not message texts.

<a id="http-72"></a>**HTTP-72. The field phrase.** One phrasing is contract, for conformance. An error about one named
claim or parameter MUST carry `missing required claim: <field>` or `invalid claim value: <field>` in the message of the
outermost error the operation raises, since a conformance runner reads that message and takes the field from the text
after the last of those two phrases (FORMAT.md section 5.1). An SDK whose error messages do not repeat their cause's
text writes the phrase into the outer message itself. The reader takes the longest run of `[A-Za-z0-9_.]` there, `.`
included for `gid.partner`, so the character after the token is none of those: `invalid claim value: amount.` reads as
the token `amount.`, while a space, a colon, a parenthesis or the end of the message ends it. The field tokens are the
neutral names, with these spellings: `xmin`, `xmax`, `xdecimals` on a gamepass, `xsettle` on a settlement, and
`partnerID` on verify-keys. The verify-keys window's token is the language's own parameter name, which no vector
compares ([VERIFYKEYS-39](#verifykeys-39)). (Vectors: through the `field` check of every case that gives one, in
`keys.json`, `gidgp.json`, `inbound.json`, `settle.json` and `verifykeys.json`.)

## 5. Keys and JWS (KEYS)

This section defines how an SDK loads keys, when a key is usable, what a key store promises, and the compact JWS
envelope every token shares: what an SDK emits, and how it reads a token up to the point where a verified payload object
is handed to the claim rules of sections 6 to 10. For SDK behaviour this section is the authority; the partner docs
describe the same key pairs and formats for people (Keys and Test integration).

Terms used throughout this section, after [P-signature-vs-shape](#p-signature-vs-shape) and the taxonomy of section 4:

| Term | Error categories | Verify-keys reason |
|------|------------------|--------------------|
| the role's invalid-key error | `{invalid_private_key}` for a private key, `{invalid_public_key}` for a public key, never wrapped in a token category | none on the wire (handlers answer 500); the mapper gives `signature` for `invalid_public_key` ([KEYS-60](#keys-60)) |
| malformed token | `{invalid_<token>}`: `invalid_booster`, `invalid_checkbet`, `invalid_verify_keys` (and `invalid_gamepass` for Go's deprecated parser) | `shape` |
| signature failure | `{invalid_<token>, invalid_signature}` | `signature` |

**Surface used in this section.** Required status is in 3.1.

| Neutral name | JS | Go |
|--------------|----|----|
| private-key PEM loader | `loadPrivateKeyFromPEM(pem: string \| Uint8Array): Promise<CryptoKeyLike>` | `keys.LoadPrivateKeyFromPEM(pemData []byte) (*ecdsa.PrivateKey, error)` |
| public-key PEM loader | `loadPublicKeyFromPEM(pem: string \| Uint8Array): Promise<CryptoKeyLike>` | `keys.LoadPublicKeyFromPEM(pemData []byte) (*ecdsa.PublicKey, error)` |
| private-key file loader | `loadPrivateKeyFromFile(path)` (entry `@boostxinnovation/partner-sdk/node`) | `keys.LoadPrivateKeyFromFile(path)` |
| public-key file loader | `loadPublicKeyFromFile(path)` (entry `@boostxinnovation/partner-sdk/node`) | `keys.LoadPublicKeyFromFile(path)` |
| handler key store | `HandlersKeyStore`: `partnerPublicKeys(partner)`, `partnerPrivateKey(partner)`, `boostxPublicKey(partner)` | `handlers.KeyStore`: `PartnerPublicKey(ctx, partner)`, `PartnerPrivateKey(ctx, partner)`, `BoostxPublicKey(ctx, partner)`; optional `handlers.PartnerPublicKeysStore`: `PartnerPublicKeys(ctx, partner)` |
| client key store | `ClientKeyStore`: `partnerPrivateKey(partner)` | `client.KeyStore`: `PartnerPrivateKey(ctx, partner)` |
| in-memory key store | `new MemoryKeyStore()`, `register(partner, {partnerPublicKey?, partnerPrivateKey?, boostxPublicKey?})` | `keys.NewMemoryKeyStore()`, `Register(partner, partnerPub, partnerPriv, boostxPub)`, `RegisterWithPartnerPublicKeys(partner, partnerPubs, partnerPriv, boostxPub)` |
| unknown-partner error | `BoostxError` with code `unknown_partner` | an error wrapping `keys.ErrUnknownPartner` |
| verify-keys reason mapper | `verifyKeysReason(err)` | `tokens.VerifyKeysReason(err)` |

### 5.1 Loading keys

The loaders turn key files into key handles. A loader is the only place an SDK reads PEM, and a key it returns is always
usable ([KEYS-63](#keys-63)). The rules below form one algorithm, applied in this order: input (KEYS-14), literal escapes
(KEYS-06), block selection (KEYS-04), framing (KEYS-08), body encoding (KEYS-11), format by label (KEYS-05), DER content
(KEYS-12, KEYS-13). Every failure is the role's invalid-key error; message texts are not contract (HTTP-60).

<a id="keys-01"></a>**KEYS-01. Private-key forms.** The private-key loader MUST accept an ECDSA P-256 private key as
PKCS#8 PEM (`-----BEGIN PRIVATE KEY-----`, RFC 5958) and as SEC1 PEM (`-----BEGIN EC PRIVATE KEY-----`, RFC 5915), given
as text or as bytes, and through the file loader (KEYS-15). PKCS#8 is the form BoostX's key setup instructions write;
SEC1 is what `openssl ecparam -genkey` and many key tools write, so an SDK accepts it too. (Vectors: `keys.json`.)

<a id="keys-02"></a>**KEYS-02. Public-key form.** The public-key loader MUST accept an ECDSA P-256 public key as SPKI PEM
(`-----BEGIN PUBLIC KEY-----`) and nothing else: a PKCS#8 or SEC1 block, an `EC PUBLIC KEY` block or a certificate is
not selected (KEYS-04) and fails. The dashboard shows the BoostX public key in this form and accepts a partner public key
only in it. (Vectors: `keys.json`.)

<a id="keys-03"></a>**KEYS-03. Curve and algorithm.** A loaded key MUST be an ECDSA key (`id-ecPublicKey`,
1.2.840.10045.2.1) on P-256 (`prime256v1`, 1.2.840.10045.3.1.7). Any other curve (P-224, P-384, P-521, secp256k1) or key
type (RSA, Ed25519) is the role's invalid-key error, from the loader itself, not later at use. (Vectors: `keys.json`.)

<a id="keys-14"></a>**KEYS-14. Loader input.** A PEM loader takes text or bytes. Any other input (absent, null, a number,
an object) MUST fail with the role's invalid-key error, never with a runtime type error ([P-null-absent](#p-null-absent),
[P-taxonomy](#p-taxonomy)). Bytes are read as text with every ASCII byte kept as it is.

Implementation-defined: how non-ASCII bytes are read (decoded as UTF-8 with replacement, or kept raw); no such byte can
belong to a block that loads, since the markers and the base64 body are ASCII. A UTF-8 byte order mark in bytes input is
covered by KEYS-07. (Vectors: `keys.json`, for null, which every runner runs, and a number, which a runner whose
loaders take only text or bytes may skip by its `untyped-string` tag.)

<a id="keys-06"></a>**KEYS-06. Literal escapes.** Before anything is searched, the loader MUST replace every literal
four-character sequence `\r\n` (backslash, `r`, backslash, `n`) and every literal two-character sequence `\n`
(backslash, `n`) with a line feed, scanning left to right and matching the four-character form first. A literal `\r` on
its own is not replaced; it then fails the body rule (KEYS-11). Keys kept in environment variables usually arrive with
their line breaks written this way. (Vectors: `keys.json`.)

<a id="keys-04"></a>**KEYS-04. Block selection.** The loader MUST use the block that starts at the earliest occurrence of
the string `-----BEGIN L-----` where `L` is one of the role's labels, found by exact, case-sensitive string search:

| Role | Labels |
|------|--------|
| private key | `PRIVATE KEY`, `EC PRIVATE KEY` |
| public key | `PUBLIC KEY` |

No label grammar is involved: blocks with any other label (`ENCRYPTED PRIVATE KEY`, `ECDSA PRIVATE KEY`,
`EC PUBLIC KEY`, `CERTIFICATE`, a lower-case `private key`) are never selected, so a bundle loads its first wanted key
wherever it sits. When no wanted marker occurs, the load fails; the message can name the labels it found, since message
texts are free ([HTTP-60](#http-60)). When the selected block is broken the load fails: a later block is never tried.
Selecting by label is what OpenSSL and .NET do, and it matches the dashboard, which takes only `BEGIN PUBLIC KEY`.
(Vectors: `keys.json`.)

<a id="keys-08"></a>**KEYS-08. Framing.** The block's body MUST run from the end of the selected BEGIN marker to the first
following occurrence of `-----END L-----` with the same `L`; with none, the load fails. Text before the BEGIN marker, on
its line or earlier, and text after the END marker are ignored, so the marker need not start a line, an indented key
loads, and a body written on the marker's own line loads. From the body the loader MUST remove exactly the RFC 7468
whitespace characters, U+0020, U+0009, U+000A, U+000B, U+000C and U+000D, and no others: a no-break space, U+2028 or
U+FEFF inside the body stays and fails KEYS-11. Two string searches and a fixed character set give the same result in
every language, where native PEM readers (`encoding/pem`, OpenSSL, .NET `PemEncoding`) disagree at exactly these edges;
the leniency is safe because the key file is trusted configuration and its DER is still fully checked.
(Vectors: `keys.json`.)

<a id="keys-07"></a>**KEYS-07. Byte order mark before the key.** A UTF-8 byte order mark before the BEGIN marker, in text
or in bytes, MUST NOT prevent loading: it is text before the marker (KEYS-08). (Vectors: `keys.json`.)

<a id="keys-11"></a>**KEYS-11. Body encoding.** After whitespace removal the body MUST be padded standard base64 (RFC 4648
section 4): only `A`-`Z`, `a`-`z`, `0`-`9`, `+` and `/`, with `=` only as the last one or two characters, and a length
that is a multiple of 4. Anything else is the role's invalid-key error: an unpadded body, `-` or `_`, `=` before the
end, a stray character. The unused bits of the last quantum are not checked. Line width and line endings (LF, CRLF) do
not matter, since the line breaks are removed. An empty body passes this step and fails the DER step. (Vectors:
`keys.json`.)

<a id="keys-09"></a>**KEYS-09. Encapsulated header lines.** RFC 1421 header lines inside a block (`Comment: x`,
`Proc-Type: 4,ENCRYPTED`, `DEK-Info: …`) are not supported. Their `:` is outside the base64 alphabet, so such a block
fails KEYS-11 with the role's invalid-key error and no extra code. When the body carries `Proc-Type: 4,ENCRYPTED`, the
message SHOULD tell the partner to decrypt the key first. (Vectors: `keys.json`.)

<a id="keys-10"></a>**KEYS-10. Encrypted keys.** Encrypted private keys MUST be refused with `invalid_private_key`.
`ENCRYPTED PRIVATE KEY` is not a wanted label (KEYS-04); when no wanted block is found and such a block is present, the
message SHOULD tell the partner to decrypt the key first. An encrypted SEC1 key carries a `Proc-Type` header and fails as
KEYS-09 says. A plaintext PKCS#8 body under an `ENCRYPTED PRIVATE KEY` label is not loaded either, since the label is
never selected. (Vectors: `keys.json`, by category only.)

<a id="keys-05"></a>**KEYS-05. The label decides the format.** The decoded DER MUST be parsed only as the format its label
names:

| Label | Parsed as |
|-------|-----------|
| `PRIVATE KEY` | PKCS#8 `PrivateKeyInfo` whose algorithm is `id-ecPublicKey` with parameters `prime256v1` |
| `EC PRIVATE KEY` | SEC1 `ECPrivateKey` (KEYS-13) |
| `PUBLIC KEY` | SPKI `SubjectPublicKeyInfo` (KEYS-12) |

A body that does not parse as its label's format is the role's invalid-key error: a PKCS#8 body under `EC PRIVATE KEY`
and a SEC1 body under `PRIVATE KEY` both fail. The PKCS#8 AlgorithmIdentifier MUST be exactly
`SEQUENCE { id-ecPublicKey, prime256v1 }`: missing parameters, NULL parameters or another curve fail, even when the
inner `ECPrivateKey` names P-256. Lengths MUST be DER: a long form where the short form fits, or an indefinite
length, fails. The decoded body MUST be exactly the structure, and the `privateKey` octet string of a PKCS#8 key exactly
one `ECPrivateKey`: octets after either are the role's invalid-key error, for a private key as for a public key
(KEYS-12; decision [private-key structures](#decision-private-key-structure)). Dispatching on the label is what OpenSSL
and .NET do; trying one parser after another is an `encoding/x509` habit that cannot be written down portably. (Vectors:
`keys.json`.)

<a id="keys-13"></a>**KEYS-13. Private-key content.** Each structure MUST hold its fields in this order and nothing else
(decision [private-key structures](#decision-private-key-structure)); anything else is the private-key error:

- A PKCS#8 `PrivateKeyInfo` is `SEQUENCE { INTEGER 0, AlgorithmIdentifier (KEYS-05), OCTET STRING privateKey,
  [0] attributes OPTIONAL }`. The attributes, a constructed `[0]` (tag octet `0xA0`), are not read: only that
  element's own tag and DER length are checked, and its content is not parsed, so it need not be well-formed DER.
  Version 1 (RFC 5958 `OneAsymmetricKey`, with or without its `[1]` publicKey), any other version, and any element after
  `privateKey` other than the attributes fail, a primitive `[0]` (tag octet `0x80`) included.
- An `ECPrivateKey`, in an `EC PRIVATE KEY` block or inside a PKCS#8 `privateKey`, is `SEQUENCE { INTEGER 1,
  OCTET STRING scalar, [0] parameters OPTIONAL, [1] publicKey OPTIONAL }`. A field out of order, a field twice and an
  unknown field fail. The `[0]` field, when present, MUST hold exactly `namedCurve prime256v1`, inside PKCS#8 too, where
  the AlgorithmIdentifier already names the curve; another curve or explicit curve parameters fail. In an
  `EC PRIVATE KEY` block the `[0]` field MUST be present.

For both private-key formats:

- A version is a DER INTEGER, and DER writes an integer in its fewest octets: the PKCS#8 version is exactly `02 01 00`
  and the `ECPrivateKey` version exactly `02 01 01`; a version written with a redundant leading octet (`02 02 00 00`,
  `02 02 00 01`) fails, although its value is right.
- The scalar's integer value MUST be in [1, n−1]; 0 and n or more fail. A scalar octet string shorter than 32 octets
  (leading zeros dropped, as older OpenSSL versions wrote) or one with extra leading zero octets is accepted.
- The `[1]` public-key field of the `ECPrivateKey`, standalone or inside a PKCS#8 `privateKey` octet string, is
  optional; a key without it loads. When it is present, it MUST be a BIT STRING with no unused bits holding the 65-octet
  uncompressed encoding `0x04 || X || Y` of exactly the point the scalar derives (decision [a private key whose halves
  disagree is refused](#decision-embedded-public-key)). Anything else is `invalid_private_key`: another key pair's
  point, the scalar's own point compressed (`0x02`, `0x03`) or hybrid (`0x06`, `0x07`), a point off the curve, the
  encoding of the point at infinity, any other length, an empty BIT STRING, a `[1]` that holds anything but a primitive
  BIT STRING (an OCTET STRING, a constructed BIT STRING) or is itself primitive. A file whose two halves disagree is
  corrupt, and which half was meant cannot be known; a compressed or hybrid point is refused as KEYS-12 refuses it in a
  public key, so the field is never decoded. Each SDK compares the field with the point it derives from the scalar
  itself: Go's `x509` ignores the field, and what a Web Crypto `pkcs8` import does with it varies by runtime (Node.js 22
  and workerd refuse another key pair's point but accept the own point compressed), so the JS SDK hands the platform the
  scalar alone. The crypto library derives the point; section 14.18 shows how without point arithmetic of the SDK's own
  ([KEYS-69](#keys-69)).

A key with no parameters says nothing about its curve, and reading its scalar as P-256 can silently load the wrong key;
OpenSSL, .NET `ImportECPrivateKey` and Go's `x509` refuse parameterless SEC1 too. (Vectors: `keys.json`.)

<a id="keys-12"></a>**KEYS-12. Public-key content.** The decoded DER MUST be exactly the 91-octet SPKI of a P-256 key with
an uncompressed point: `SEQUENCE { SEQUENCE { id-ecPublicKey, prime256v1 }, BIT STRING 0x04 || X || Y }`, X and Y 32
octets each, in a BIT STRING with no unused bits (its first content octet, which counts them, is `0x00`), the point on
the curve and not the point at infinity. A compressed point (prefix `0x02` or `0x03`), a hybrid point (`0x06`, `0x07`),
a BIT STRING that declares unused bits, any other algorithm or curve, and octets after the structure are the public-key
error. Uncompressed is the one form every standard library imports: Java's SunEC, .NET on Windows and Go's `x509`
cannot import a compressed SPKI without hand-written point decompression. BoostX's dashboard applies the same rule to
the partner public key, so nothing a partner uploads can be refused by an SDK. (Vectors: `keys.json`.)

<a id="keys-15"></a>**KEYS-15. File loaders.** An SDK for a platform with a filesystem MUST offer a private-key and a
public-key file loader (JS `loadPrivateKeyFromFile(path)`, `loadPublicKeyFromFile(path)` from the
`@boostxinnovation/partner-sdk/node` entry; Go `keys.LoadPrivateKeyFromFile(path)`, `keys.LoadPublicKeyFromFile(path)`).
A read failure MUST be the role's invalid-key error with the operating-system error kept as an inspectable cause (JS
`err.cause`, with its `code` such as `ENOENT`; Go `errors.Is(err, fs.ErrNotExist)` holds). The bytes read are handed to
the PEM loader unchanged. (Vectors: none; the vectors read no files.)

<a id="keys-16"></a>**KEYS-16. What a loaded key is.** A loaded key is an opaque handle of the platform's standard crypto
library (JS a non-extractable Web Crypto `CryptoKey`, typed structurally as `CryptoKeyLike`, with the usage `sign` or
`verify`; Go `*ecdsa.PrivateKey` and `*ecdsa.PublicKey`).

Implementation-defined: whether loading is synchronous (Web Crypto has no synchronous import), whether a private key
exposes its public half, and whether a key can be exported. The handle never crosses the wire. (Vectors: none;
representation.)

### 5.2 Key usability

<a id="keys-63"></a><a id="gid-45"></a>**KEYS-63. Usable keys, and never a crash.** A key is usable only if it is an ECDSA
P-256 key of its role that the platform can use ([P-key-usability](#p-key-usability)):

- a public key: the point is present, on the curve, with coordinates in [0, p−1], and not the point at infinity, and the
  key allows verifying (where the platform has key usages, it carries `verify`);
- a private key: the scalar is present and in [1, n−1], and the key allows signing (usage `sign`); where the platform's
  private-key object also carries the public point and needs it to sign, the point is present.

An unusable key MUST be reported as the role's invalid-key error, which the handlers answer 500. It MUST NOT crash the
caller (no panic, abort or uncaught runtime exception) and MUST NOT be reported as a signature failure. In a partner
public key list, unusable keys are skipped, and `invalid_public_key` results only when no listed key is usable
([KEYS-45](#keys-45)). Every crypto library can validate a key before use (section 14.18): Web Crypto validates at
import, and in Go `(*ecdsa.PublicKey).ECDH()` and `(*ecdsa.PrivateKey).ECDH()` refuse an off-curve point or an invalid
scalar once nil fields are excluded (they dereference them). A key made by the loaders always passes, so the check costs
live traffic nothing. Also covers: [GID-45](#gid-45), [SETTLE-33](#settle-33).

Implementation-defined: how much is checked before use. JS can check a `CryptoKey` only structurally (type, algorithm
`ECDSA` on `P-256`, usage), while Go checks the curve, the fields and the point up front. A key that passes the up-front
check and still fails at signing or verifying is the role's invalid-key error, raised at that point.

Implementation-defined: whether a key object whose stored public point disagrees with its scalar (only a hand-built
object can be one, given KEYS-13) is refused or used with its scalar. (Vectors: `keys.json`, `gidgp.json`, through the
`@unusable` reference, which is a P-384 key of the role; malformed key objects are language-specific and pinned by each
SDK's own tests.)

<a id="keys-17"></a>**KEYS-17. Signing needs a usable private key.** Every function that signs (the GID builder, every
token builder, the settlement client, an optional generic signer) MUST refuse a key that is not a usable ECDSA P-256
private key with `{invalid_private_key}`, alone. A public key passed where the private key goes is such a key. The
builders check the key before any parameter: [KEYS-19](#keys-19), written in 7.2. (Vectors: `keys.json`.)

<a id="keys-18"></a>**KEYS-18. Verifying needs a usable public key.** Every function that verifies MUST refuse a key that
is not a usable ECDSA P-256 public key with `{invalid_public_key}`, alone: a parser passes it through as it is, never
wrapped in `invalid_<token>` and never as a signature failure, because it is the caller's configuration, not BoostX's
token. A private key passed where a public key goes is such a key. The handlers answer it 500
`{"error":"failed to verify token"}` ([KEYS-53](#keys-53), [HTTP-26](#http-26)). Parsers check their keys before reading
the token, the BoostX key first: [KEYS-46](#keys-46), written in 6.4. (Vectors: `keys.json`.)

### 5.3 Emitted tokens

<a id="keys-20"></a>**KEYS-20. Emitted header.** The header of every token an SDK signs MUST have exactly two members,
`alg` with the string `"ES256"` and `typ` with the string `"JWT"`, and no other (no `kid`, no `crit`). BoostX verifies
ES256 only and reads no `typ`.

Implementation-defined: the header's member order and JSON spelling ([P-emitted-bytes](#p-emitted-bytes)); both
reference SDKs emit the 27 octets `{"alg":"ES256","typ":"JWT"}`, base64url `eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9`.
(Vectors: the builder checks of FORMAT.md section 5.3, applied to every accepted builder result in every file;
`keys.json`.)

<a id="keys-25"></a>**KEYS-25. Emitted segments.** All three segments of an emitted token MUST be canonical unpadded
base64url ([P-base64url](#p-base64url)). A verifier that follows KEYS-26, the SDK's own verify-keys response parser
included, refuses anything else. (Vectors: the builder checks of FORMAT.md section 5.3; `keys.json`.)

<a id="keys-29"></a>**KEYS-29. The JWS signature.** ES256 is ECDSA on P-256 with SHA-256. A signer MUST sign the octets
of the signing input, the header segment, `.` and the payload segment, and MUST emit the signature as the 64-octet
`r || s`, each a 32-octet big-endian unsigned integer left-padded with zeros, never DER. A verifier MUST decode the
signature segment to exactly 64 octets ([KEYS-31](#keys-31)), split it into `r` and `s`, and verify it over the exact
octets of the received token text before the second `.`, never over re-encoded segments. Where the text is held as
characters, its octets are its UTF-8 encoding, which is plain ASCII for segments of base64url; a payload segment
holding any other character is verified over those octets, so a signer that signed the same octets passes this check
and the segment then fails its own check as malformed, never as a signature failure
(`inbound-booster-payload-non-ascii-signed`, `verifykeys-request-payload-non-ascii-signed`; JS encodes the text as
UTF-8, and a Go string holds those octets). A DER signature (usually 70 to 72 octets) or any other length is a
signature failure. Web Crypto already signs and verifies the raw form; in Go the halves are written with `FillBytes`
into 32-octet buffers. A payload segment holding a lone surrogate, which has no UTF-8 octets, reaches this step only
through a direct parser call: a request body may carry one as a `\ud800` escape in its token member, which is valid
JSON that the body checks accept, as [HTTP-15](#http-15) says of the other members, but a handler's extraction refuses
that payload segment first, and a header or signature segment holding one fails its own check before this step. Such
a text is refused like any other fault, never with a crash ([P-taxonomy](#p-taxonomy)).

Implementation-defined: the category of that refusal. JS encodes the surrogate as U+FFFD (`TextEncoder`), and a Go
string, which cannot hold one, holds the bytes it was given (its JSON decoder has already turned a `\ud800` escape
into U+FFFD); both verify over those octets, so the result is a signature failure unless the signer signed exactly
them, and then the payload segment's own failure as malformed. An SDK whose encoder refuses the text (Python's strict
`str.encode`) reports a signature failure. (Vectors: `keys.json`; `inbound.json` and `verifykeys.json` for a payload
segment that is not ASCII.)

<a id="keys-30"></a>**KEYS-30. No low-S rule.** A verifier MUST accept a high-S signature (s > n/2) and MUST NOT require
low-S. A signature with `r` or `s` equal to 0, or n or more, is a signature failure, not a key error.

Implementation-defined: the signer's nonce, random or deterministic (RFC 6979), and whether the signer normalises S; the
vectors never compare signature octets. ECDSA signatures stay malleable through (r, n−s) whatever the encoding rules,
and BoostX's verifier accepts both forms. (Vectors: `keys.json`, for a zero signature and, through a token given as raw
text, for a high-S token signature.)

<a id="keys-69"></a>**KEYS-69. The crypto comes from a vetted library.** An SDK MUST take ECDSA P-256 and SHA-256 from
its platform's standard library or from a vetted, maintained crypto library, and MUST NOT implement ECDSA,
elliptic-curve point arithmetic (adding or multiplying points) or SHA-256 itself. Reading and checking the encodings
around them (PEM, DER, base64url, the raw `r || s`) is the SDK's own work. The point checks of [KEYS-12](#keys-12),
[KEYS-13](#keys-13) and [KEYS-63](#keys-63) need no point arithmetic of the SDK's own: section 14.18 shows how a library
derives and checks the points. Hand-written curve code is where timing leaks and missed edge cases come from, and no
vector can see them. (No vector: a case sees only results, never how a signature, a hash or a point was computed.)

<a id="keys-38"></a>**KEYS-38. Emitted time claims.** Every token an SDK signs (gamepass, settlement, verify-keys
request and response) MUST carry `iat` as a JSON integer, the current Unix time in whole seconds rounded down at the
call (JS `Math.floor(Date.now() / 1000)`, Go `time.Now().Unix()`), and MUST NOT carry `exp`, `nbf` or `jti`
([P-exp-nbf](#p-exp-nbf)). BoostX reads that `iat` against its own windows: 300 seconds for a gamepass when the game
opens, ±30 seconds for a verify-keys response, none for a settlement. (Vectors: `keys.json`; the builder cases of the
other files compare `iat` with `${now}`.)

<a id="keys-61"></a><a id="gid-38"></a>**KEYS-61. Emitted payload bytes.** Implementation-defined: outside the canonical
GID signing bytes (section 6.1) and the header members (KEYS-20), the octets of an emitted payload, as long as they are
valid JSON (RFC 8259) in UTF-8 carrying the specified values: member order, string escaping (`<`, `>`, `&`, U+2028 and
U+2029 included), number spelling (`-0` as `0` or `-0`, `150` as `150.0` or in exponent form), whitespace and a final
line feed ([P-emitted-bytes](#p-emitted-bytes)). Every verifier, BoostX included, parses the payload and rebuilds only the
GID bytes from the decoded values; pinning more would force a hand-written JSON encoder in every SDK. Also covers:
[GID-38](#gid-38), [SETTLE-34](#settle-34), [HTTP-70](#http-70). (Vectors: `gidgp.json`, which compares decoded
values; no vector compares payload octets.)

### 5.4 Inbound JWS: segments, bytes and header

These rules apply to every token an SDK reads: the Booster and CheckBet parsers and extractors (section 8), the
verify-keys request and response parsers and the request extractor (section 10), Go's deprecated gamepass parser, and
any optional generic helper ([KEYS-62](#keys-62)). Their normative order is [KEYS-67](#keys-67). The parse functions
impose no length limit on a token: [KEYS-43](#keys-43), written in 11.2.

<a id="keys-28"></a>**KEYS-28. Three segments.** A token MUST split on `.` into exactly three segments; the empty text, one,
two, four or more segments is a malformed token, in extraction and in parsing alike. Empty segments count as segments
(`a..c` has three) and then fail the segment rules. A token argument that is not text, where the language allows one, is
malformed too. Text here is a value of the language's string type: bytes are not text (a Python `bytes`, a JS
`Uint8Array`), unlike the input of a key loader, which takes either ([KEYS-14](#keys-14)). (Vectors: `keys.json`.)

<a id="keys-26"></a><a id="inbound-03"></a><a id="verifykeys-25"></a>**KEYS-26. Canonical base64url segments.** Each of
the three segments MUST be canonical unpadded base64url ([P-base64url](#p-base64url)): only `[A-Za-z0-9_-]`, a length
that is not 1 mod 4, no `=`, no whitespace, CR or LF, and zero unused trailing bits. Equivalently, re-encoding the decoded
octets gives back the segment exactly. A header or payload segment that fails is a malformed token; a signature segment
that fails is a signature failure ([KEYS-31](#keys-31)). Tokens are used exactly as received, never trimmed. An empty
segment is canonical (zero octets) and fails the next step. A decoder that skips CR and LF even in strict mode (Go's
`base64.RawURLEncoding.Strict()`) needs an explicit alphabet check. BoostX emits canonical segments, so the live
partner sees no difference. Also covers: [INBOUND-03](#inbound-03), [VERIFYKEYS-25](#verifykeys-25),
[HTTP-41](#http-41). (Vectors: `keys.json`, `inbound.json`, `verifykeys.json`, `http.json`.)

<a id="keys-35"></a><a id="keys-36"></a><a id="keys-66"></a><a id="gid-06"></a><a id="inbound-10"></a><a id="inbound-11"></a><a id="verifykeys-29"></a>
**KEYS-35. Segment bytes.** The decoded header and the decoded payload MUST each be well-formed UTF-8 (RFC 3629: no overlong form,
no encoded surrogate, nothing above U+10FFFF, no truncated sequence) and MUST NOT begin with the octets EF BB BF
([P-utf8](#p-utf8)). Invalid octets are never replaced with U+FFFD, and a byte order mark is never stripped: U+FEFF is
not JSON whitespace, so it fails the one-JSON-value rule wherever it stands outside a string. Either fault is a malformed
token, in extraction (payload) and in parsing (header and payload). Replacing octets would change signed content before
anything reads it, and RFC 8259 forbids a sender to add a byte order mark; standard decoders disagree on both points,
which is why the rule is stated on octets. Also covers: [KEYS-36](#keys-36), [KEYS-66](#keys-66), [GID-06](#gid-06),
[INBOUND-10](#inbound-10), [INBOUND-11](#inbound-11), [VERIFYKEYS-29](#verifykeys-29). (Vectors: `keys.json`,
`gidgp.json`, `inbound.json`, `verifykeys.json`.)

<a id="keys-37"></a><a id="gid-04"></a><a id="inbound-28"></a>**KEYS-37. Lone-surrogate escapes.** A token whose header
or payload JSON text contains a `\u` escape of a code unit in U+D800 to U+DFFF that is not part of a pair, a high
surrogate escape (U+D800 to U+DBFF) immediately followed by a low surrogate escape (U+DC00 to U+DFFF), MUST be refused
as a malformed token ([P-surrogates](#p-surrogates), decision [lone-surrogate ids](#decision-lone-surrogates)). The test
runs on the JSON text as written: hex digits in either case, and an escaped backslash (`\\`) does not start an escape.
It therefore covers member names, unknown members, every depth, and a member that a repeated name later replaces. It
applies in extraction (payload) and parsing (header and payload) alike, before any claim is read, so such a token is
never verified as a GID. Walking the parsed value is not enough, since it misses a replaced member; and an unescaped
surrogate cannot occur, because KEYS-35 refuses its encoded octets. Builders refuse ids that are not well-formed Unicode
with `invalid_claim` ([P-builder-ids](#p-builder-ids), [GID-35](#gid-35)). Why the token level: Go's `encoding/json`
replaces such an escape with U+FFFD silently and PHP and .NET refuse the whole document, so only a test on the text
gives one outcome in every language; and BoostX refuses a gamepass whose ids hold a lone surrogate, so no Booster or
CheckBet carries one. Also covers: [GID-04](#gid-04), [INBOUND-28](#inbound-28). (Vectors: `keys.json`, `gidgp.json`,
`inbound.json`, `verifykeys.json`, `http.json`.)

<a id="keys-22"></a><a id="keys-21"></a><a id="keys-24"></a><a id="keys-65"></a><a id="inbound-05"></a><a id="inbound-55"></a><a id="verifykeys-22"></a>
**KEYS-22. The JWS header.** After KEYS-26, KEYS-35 and KEYS-37:

1. The decoded header MUST be exactly one JSON value, optionally surrounded by JSON whitespace (space, tab, LF, CR), and
   that value MUST be an object ([P-one-value](#p-one-value)). `null`, an array, a string, a number, a boolean or data
   after the value is a malformed token, not a signature failure.
2. Member names are matched exactly, code unit for code unit after JSON unescaping, with no case or Unicode folding
   ([P-names](#p-names)): `ALG` or `Alg` is not `alg`. When a name repeats, the last occurrence is the member's value
   ([P-duplicates](#p-duplicates)): `{"alg":"none","alg":"ES256"}` has `alg` `"ES256"`, and
   `{"alg":"ES256","alg":"none"}` has `alg` `"none"`.
3. The member named exactly `alg` MUST be the JSON string `"ES256"`, compared after unescaping and case-sensitively.
   An absent `alg`, `null`, another string (`none`, `es256`, `ES384`), a number, a boolean, an object or an array is a
   signature failure. This is checked before `crit` ([KEYS-23](#keys-23)) and before the signature segment.

Only `alg` and `crit` are read from the header. Exact names with the last duplicate winning is what `JSON.parse`, Python
`json`, PHP `json_decode`, Jackson trees and .NET `JsonElement` do natively; Go's case-insensitive struct matching is an
`encoding/json` quirk a written rule cannot reproduce, so Go reads the header as a map. Every `alg` fault is a signature
failure because it prevents establishing an ES256 signature, which is also how BoostX reports it. Also covers:
[KEYS-21](#keys-21), [KEYS-24](#keys-24), [KEYS-65](#keys-65), [INBOUND-05](#inbound-05), [INBOUND-55](#inbound-55),
[VERIFYKEYS-22](#verifykeys-22), [HTTP-67](#http-67). (Vectors: `keys.json`, `inbound.json`, `verifykeys.json`,
`http.json`.)

<a id="keys-23"></a><a id="keys-64"></a><a id="inbound-04"></a><a id="verifykeys-23"></a>**KEYS-23. crit and the other
header members.** A header that has a member named exactly `crit`, whatever its value (`null`, `[]`, a list of names),
MUST be refused as a signature failure: the SDK understands no JWS extension, and RFC 7515 section 4.1.11 requires
refusing an unknown `crit`. Every other member (`typ`, `kid`, `x5u`, `b64`, unknown names) MUST be ignored whatever its
JSON type, so `"typ":1` or `"kid":{}` is accepted, and `b64` without `crit` has no effect. The header checks run in this
order: object (KEYS-22 step 1), `alg` (step 3), `crit`. The JOSE libraries a third SDK would use refuse an unknown
`crit` too, and BoostX never sends one. Also covers: [KEYS-64](#keys-64), [INBOUND-04](#inbound-04),
[VERIFYKEYS-23](#verifykeys-23). (Vectors: `keys.json`, `inbound.json`, `verifykeys.json`, `http.json`.)

<a id="keys-31"></a><a id="inbound-56"></a><a id="verifykeys-26"></a>**KEYS-31. The signature segment.** A signature
segment that is not canonical base64url (KEYS-26), or that does not decode to exactly 64 octets, MUST be a signature
failure, the same category as a signature that does not verify. Every fault that prevents establishing an ES256
signature is a signature failure, and every other structural fault is a malformed token
([P-signature-vs-shape](#p-signature-vs-shape)); BoostX's diagnostic reads `signature` as a key problem, which is where
such a token points. Also covers: [INBOUND-56](#inbound-56), [VERIFYKEYS-26](#verifykeys-26). (Vectors: `keys.json`,
`inbound.json`, `verifykeys.json`, `http.json`.)

<a id="keys-27"></a>**KEYS-27. Unverified extraction reads only the payload.** An extractor (the partner id read before
any key is known) MUST NOT decode or check the header or the signature segment. It requires three segments (KEYS-28),
applies the payload rules (KEYS-26, KEYS-35, KEYS-37, KEYS-32 to KEYS-34) and then the claim checks
([KEYS-49](#keys-49)). A token whose header is not JSON, whose `alg` is `none`, or whose signature is empty, DER or made
with the wrong key still yields its partner id; verification decides afterwards. (Vectors: `keys.json`.)

<a id="keys-67"></a>**KEYS-67. Verification order.** A parser MUST run these steps in this order and report the first
failing step ([P-check-order](#p-check-order)):

1. **Keys.** The verifying key is usable ([KEYS-18](#keys-18)). Booster and CheckBet check the BoostX key and then the
   partner key list ([KEYS-46](#keys-46)). A failure is the key error.
2. **Segments.** Exactly three ([KEYS-28](#keys-28)). Malformed.
3. **Header.** Canonical base64url ([KEYS-26](#keys-26)), bytes ([KEYS-35](#keys-35)), one JSON object
   ([KEYS-22](#keys-22) step 1) and no lone-surrogate escape ([KEYS-37](#keys-37)). Malformed. These faults share one
   outcome, so their relative order is not observable, and any order meets this step.
4. **alg** ([KEYS-22](#keys-22) step 3). Signature failure.
5. **crit** ([KEYS-23](#keys-23)). Signature failure.
6. **Signature segment.** Canonical and 64 octets ([KEYS-31](#keys-31)). Signature failure.
7. **ECDSA verification** over the received text ([KEYS-29](#keys-29)). Signature failure; a key the platform refuses
   only at this point is the key error ([KEYS-63](#keys-63)).
8. **Payload.** As step 3, with [KEYS-32](#keys-32) for the object; [KEYS-33](#keys-33) and [KEYS-34](#keys-34) govern
   how its members are then read. Malformed.
9. **Claims, then the GID**, in the token's own order: [INBOUND-32](#inbound-32) for Booster and CheckBet,
   [VERIFYKEYS-46](#verifykeys-46) for verify-keys.

So a forged token with a malformed payload is a signature failure, and a validly signed token whose payload does not
decode is malformed. An extractor runs steps 2 and 8 and then the claim checks ([KEYS-27](#keys-27)). (Vectors:
`keys.json`; a case with several faults expects the first step's outcome.)

### 5.5 Inbound payload JSON

<a id="keys-32"></a><a id="verifykeys-28"></a>**KEYS-32. The payload is one JSON object.** The decoded payload MUST be
exactly one JSON value, optionally surrounded by JSON whitespace, and that value MUST be an object
([P-one-value](#p-one-value)). `null`, an array, a scalar or data after the value is a malformed token, in extraction
and in parsing. A payload nested 64 levels deep or less is read like any other (the depth floor of P-one-value, decision
[JSON nesting depth](#decision-json-depth)). Also covers: [VERIFYKEYS-28](#verifykeys-28). (Vectors: `keys.json`,
`inbound.json`, `verifykeys.json`, `http.json`.)

<a id="keys-33"></a><a id="inbound-15"></a>**KEYS-33. Repeated payload members.** When an object in the payload repeats a
member name, at any depth, the last occurrence MUST be the member's value and replace the earlier ones whole: objects are
never merged, and a later `null` counts as `null` ([P-duplicates](#p-duplicates)). So a payload with two `booster` objects
reads only the second, and a `gid` the first one carried does not survive. RFC 7515 section 5.2 and RFC 7519 section 4
allow this, and it is what the standard parsers do natively; refusing duplicates would need a hand-written JSON scanner
in JS. Also covers: [INBOUND-15](#inbound-15). (Vectors: `keys.json`, `gidgp.json`, `inbound.json`, `verifykeys.json`,
`http.json`.)

<a id="keys-34"></a><a id="gid-28"></a><a id="inbound-14"></a><a id="verifykeys-30"></a>**KEYS-34. Exact payload member
names.** Payload member names MUST be matched exactly, code unit for code unit after JSON unescaping, at every level:
root claims, the token's root object, `gid` and its members, `verifyKeys` ([P-names](#p-names)). A member whose name
differs in any way, letter case included, is an unknown member and is ignored, so it never supplies or overrides the named
member: a root spelled `Booster` leaves `booster` absent, and `IAT` is not `iat`. The one exception is an optional generic
helper that maps claims into a structure the caller supplies ([KEYS-62](#keys-62)). Also covers: [GID-28](#gid-28),
[INBOUND-14](#inbound-14), [VERIFYKEYS-30](#verifykeys-30), [HTTP-12](#http-12). (Vectors: `keys.json`, `gidgp.json`,
`inbound.json`, `verifykeys.json`.)

### 5.6 Time claims

<a id="keys-39"></a><a id="inbound-41"></a><a id="inbound-42"></a>**KEYS-39. iat on Booster and CheckBet.** A Booster or
CheckBet payload MUST carry a top-level `iat`; an absent one is `missing_claim` (field `iat`). It MUST be a JSON number
whose value, read per [P-integers](#p-integers) (the nearest binary64 value), is an integer of magnitude at most
2^53−1: `1700000000`, `1.7e9` and `1700000000.0` are accepted; `1.5`, `9007199254740992`, `1e20`, a number beyond the
binary64 range (read as ±Infinity), `null`, a string and a boolean are `invalid_claim` (field `iat`). Zero and negative
values are accepted; no range or sign check applies. The check runs in the claim step after the token's own fields and
before `exp` and `nbf` ([INBOUND-32](#inbound-32)), in extraction as in parsing. A verified Booster and a verified
CheckBet MUST expose `iat` as received, in integer Unix seconds (JS `Booster.iat`, `CheckBet.iat`; Go `Booster.IssuedAt`,
`CheckBet.IssuedAt`), and the SDK applies no age check to it (KEYS-40, [P-iat-exposed](#p-iat-exposed)). Pinning the
check to the binary64 value is what `JSON.parse`, Python and PHP do natively and makes decimal-exact parsers (Java
`BigDecimal`, .NET `decimal`) agree. Also covers: [INBOUND-41](#inbound-41), [INBOUND-42](#inbound-42),
[HTTP-30](#http-30). (Vectors: `keys.json`, `inbound.json`, `http.json`.)

<a id="keys-40"></a>**KEYS-40. No age check on Booster and CheckBet.** An SDK MUST NOT refuse a Booster or CheckBet for its
`iat`'s age or future skew: any value that passes KEYS-39, a millisecond value or 0 included, is accepted. An age check is
the partner's choice and must allow for retries, because BoostX re-sends the same token on every retry. The only age
check an SDK makes is the verify-keys window, |now − iat| ≤ the window in whole seconds ([KEYS-41](#keys-41)).
(Vectors: `keys.json`.)

<a id="keys-41"></a><a id="verifykeys-38"></a><a id="verifykeys-40"></a>**KEYS-41. The verify-keys window.** A
verify-keys token is accepted when |now − iat| ≤ W, with now in whole Unix seconds ([P-window](#p-window)). A
verify-keys parse function MUST take W as a parameter a call may leave out (JS `{maxSkewSeconds}` in seconds, Go
`maxSkew time.Duration`): absent, null or exactly 0 means 30 ([P-zero](#p-zero)); a negative or non-finite value is
`invalid_claim`, raised after the key and partner id checks and before the token is read
([VERIFYKEYS-46](#verifykeys-46)); any other value is truncated toward zero to whole seconds, so a positive value under
one second gives a zero-second window. The window parameter MUST carry fractions of a second, whatever its type (a
number of seconds, or a duration finer than a second), so that the truncation is the SDK's: `0.5` is a zero-second
window, `60.9` a 60-second one, and `-0.5` is `invalid_claim`. The endpoint handlers MUST always use 30 seconds and MUST
NOT offer a window option. BoostX checks the partner's response against its own ±30 seconds, so a wider window on the
partner's side could never rescue a drifting clock. The parameter's name in an error message is the language's own
(`maxSkewSeconds`, `maxSkew`). Also covers: [VERIFYKEYS-38](#verifykeys-38), [VERIFYKEYS-40](#verifykeys-40),
[HTTP-43](#http-43). (Vectors: `verifykeys.json`, `keys.json`, `http.json`.)

<a id="keys-42"></a><a id="verifykeys-47"></a>**KEYS-42. exp and nbf.** Every token an SDK parses (Booster, CheckBet, the
verify-keys request and response) treats `exp` and `nbf` as optional: absent means no limit ([P-exp-nbf](#p-exp-nbf)).
A present `exp` or `nbf` MUST be a JSON number; `null` or any other type fails, as `invalid_claim` (field `exp` or `nbf`)
on Booster and CheckBet and as reason `shape` on verify-keys. A token with `exp` ≤ now or `nbf` > now fails, as
`invalid_claim` on Booster and CheckBet and as reason `stale` on verify-keys, with now in whole Unix seconds (rounded
down) and no leeway. The values are compared as binary64 numbers, so a fraction compares as written and a number beyond
the binary64 range compares as ±Infinity (`exp` +Infinity never expires, `nbf` +Infinity is never reached). The check
runs after `iat`: on Booster and CheckBet right after the `iat` check, on verify-keys after the `iat` window. SDKs never
emit either claim ([KEYS-38](#keys-38)). This is BoostX's own acceptance rule as a receiver (no tolerance, non-numbers
refused) and the JOSE libraries' default, so a third SDK built on one lands on it. BoostX sends neither
claim. Also covers: [VERIFYKEYS-47](#verifykeys-47). (Vectors: `keys.json`, `inbound.json`, `verifykeys.json`,
`http.json`.)

### 5.7 Key stores

The SDK finds keys through a key store the partner implements, keyed by the BoostX partner id. The handlers' store
supplies three roles and the settlement client's store one. The answers the handlers give for each store outcome are
written in 11.5 ([HTTP-24](#http-24) to [HTTP-26](#http-26), [HTTP-64](#http-64), [HTTP-69](#http-69)); this section
states the contract and what the SDK does with what a store returns.

<a id="keys-44"></a>**KEYS-44. The handler key store.** The handlers' key store MUST provide, for a partner id, three
roles: the partner public keys, which verify the GID (a list, the current key first); the partner private key, which
signs the `/verify-keys` response; and the BoostX public key, which verifies Booster, CheckBet and verify-keys requests
(JS `HandlersKeyStore`; Go `handlers.KeyStore` with the optional `handlers.PartnerPublicKeysStore`, which the handlers
prefer, and the single-key `PartnerPublicKey` read as a one-element list, [HTTP-64](#http-64)). A lookup returns a key (or
a list) or fails; it signals an id it does not serve with `unknown_partner` ([HTTP-69](#http-69)). A store matches the id
byte for byte, never folds, trims or normalises it, and never falls back to a fixed key set; the SDK's documentation says
so. A store that returns neither a key nor an error is answered as KEYS-53 says. The settlement client's store provides
the partner private key only (JS `ClientKeyStore`, Go `client.KeyStore`). A store missing at construction is a
construction error ([HTTP-48](#http-48), [HTTP-68](#http-68)). (Vectors: `keys.json`.)

<a id="keys-45"></a>**KEYS-45. Rotation set.** A GID MUST pass when any usable key in the partner public key list
verifies it. List order is informational (current key first); unusable entries are skipped ([KEYS-63](#keys-63)); a list
that is empty or holds no usable key is `{invalid_public_key}` (handlers: 500); a list with a usable key that does not
verify is the GID signature failure of section 6.4. Where an SDK lets a single key stand for the list, it behaves as a
one-element list. BoostX holds one partner public key and echoes the GID of the gamepass that created the game, so after
a rotation the old key stays listed until games started before it have ended. (Vectors: `keys.json`.)

<a id="keys-48"></a>**KEYS-48. Lookup by the unverified partner id.** A handler MUST look keys up by the partner id the
token itself names, read without verification: `gid.partner` for Booster and CheckBet, `aud` for a verify-keys request,
passed to the store exactly as read. An empty `gid.partner`, or an `aud` that is empty or `boostx`, is refused before
any lookup (400 `invalid booster token`, `invalid checkbet token`, `invalid verifyKeysJWT: shape`). (Vectors:
`keys.json`.)

<a id="keys-49"></a><a id="gid-33"></a><a id="inbound-21"></a>**KEYS-49. Validation before the lookup.** Before calling
the key store, a handler MUST run the unverified extraction ([P-extraction](#p-extraction)): three segments, the payload
rules, and the same claim routine the parser runs after verification. For Booster and CheckBet that is every claim check
(root object, `gid` shape, non-empty `gid.partner`, the token's own fields, `iat`, `exp` and `nbf`); for verify-keys the
claim types and an `aud` that is not empty and not `boostx`. A failure is answered 400 with no store call. Junk then never
reaches the partner's database or KMS, a store outage cannot change the answer to a malformed token, and extraction and
parsing report the same claim error. Also covers: [GID-33](#gid-33), [INBOUND-21](#inbound-21). (Vectors: `keys.json`,
`http.json`, `gidgp.json`, `inbound.json`, `verifykeys.json`.)

<a id="keys-50"></a>**KEYS-50. Unknown partner and other store failures.** A handler MUST recognise `unknown_partner`
anywhere in a store error's cause chain ([P-taxonomy](#p-taxonomy): at least 16 levels when walked by hand) and answer it
400: `{"error":"unknown partner \"<id>\""}` on `/set-boost` and `/check-bet` ([HTTP-24](#http-24)), and on
`/verify-keys` an error that starts `invalid verifyKeysJWT: iss-aud`, from the BoostX-key or the private-key lookup
(both SDKs append ` (unknown partner "<id>")`, which is free-form, [VERIFYKEYS-14](#verifykeys-14)). Any other store
error is 500 `failed to get boostx key`, `failed to get partner key` or `failed to get partner private key`
([HTTP-25](#http-25)). BoostX's self-test requires a non-2xx answer to an `aud` the partner does not serve (its
foreign-id probe, [VERIFYKEYS-62](#verifykeys-62)). (Vectors: `keys.json`.)

<a id="keys-51"></a><a id="gid-44"></a><a id="inbound-57"></a>**KEYS-51. The echoed id.** An answer that names the partner
id MUST write it between double quotes.

Implementation-defined: how characters inside the id are escaped (control characters, non-ASCII, invalid UTF-8; JS
writes JSON string escapes, Go `%q`). Status, the `{"error": <string>}` shape and the wording around the id are
normative ([P-http-errors](#p-http-errors)). Neither BoostX nor any conformance test parses the id, and printable-ASCII
ids come out identical. Also covers: [GID-44](#gid-44), [INBOUND-57](#inbound-57), [HTTP-24](#http-24). (Vectors:
`keys.json`, `gidgp.json`, `inbound.json`, `http.json`, by prefix.)

<a id="keys-52"></a>**KEYS-52. Lookup scheduling.** Implementation-defined: whether a handler looks up the BoostX public
key and the partner public keys concurrently or one after the other, and whether the second lookup runs after the first
has failed. When both fail, the BoostX-key failure MUST decide the answer. A key store MUST tolerate concurrent calls and
calls made after another lookup has failed; the SDK's documentation says so. The answer is fixed by the precedence
clause, and a synchronous language cannot always run lookups concurrently. (Vectors: `keys.json`, `http.json`; the
vectors never compare which lookups ran or in what order.)

<a id="keys-53"></a>**KEYS-53. A store that returns no usable key.** A lookup that succeeds without a usable key (no key,
an empty list, a list with no usable key, a key of the wrong kind or curve) is not a bad token: parsing refuses it with
the key error ([KEYS-18](#keys-18)), and the handler MUST answer 500 `{"error":"failed to verify token"}` for public
keys ([HTTP-26](#http-26)) and 500 `{"error":"failed to sign response"}` for the partner private key on `/verify-keys`.
Where it can (KEYS-46), parsing reports such a key ahead of anything wrong with the token. (Vectors: `keys.json`.)

<a id="keys-54"></a>**KEYS-54. Cancellation and time limits of lookups.** Handlers MUST pass the request's cancellation to
key-store lookups where the platform conventionally does (Go `r.Context()`; JS passes none) and MUST NOT set a timeout of
their own ([HTTP-31](#http-31), [P-cancellation](#p-cancellation)). The settlement client's per-attempt time limit
covers the key lookup ([SETTLE-61](#settle-61)). A lookup error MUST leave the settlement unsent and be returned with the
store's own error inspectable through the cause chain (JS propagates it unchanged; Go wraps it with `%w`), so the next
attempt can follow.

Implementation-defined: whether a handler's store call is cancellable at all, since a synchronous SDK cannot stop
waiting for a blocking callback without threads. Also covers: [SETTLE-61](#settle-61). (Vectors: `keys.json`, for the
client side, with SETTLE-61; none for the handler side.)

<a id="keys-55"></a>**KEYS-55. The client signs with the current key.** The settlement client MUST look up the private
key for `params.partner` on every attempt, before it validates the parameters, and sign that attempt with the key the
store returns at that moment. Any lookup error stops the attempt before HTTP. So a settlement for a partner id the store
does not serve fails with the store's `unknown_partner`, not with a parameter error, and a key rotated between attempts
is picked up by the next one. BoostX verifies a settlement's GID against the one partner public key it holds when the
settlement arrives. (Vectors: `keys.json`.)

Two rules of this topic are written in 6.4 with the GID: [KEYS-46](#keys-46) (a parser checks its keys before the
token, the BoostX key first) and [KEYS-47](#keys-47) (a non-canonical GID signature is a GID signature failure).

**The in-memory key store.** Every SDK offers one, as required surface (section 3.1, `keystore.register`, which the
vectors exercise), and it MUST follow KEYS-56 to KEYS-59.

<a id="keys-56"></a>**KEYS-56. Registration.** Registration MUST add or replace a partner's whole key set atomically
(JS `register(partner, {partnerPublicKey?, partnerPrivateKey?, boostxPublicKey?})`, where `partnerPublicKey` is one key
or a list; Go `Register(partner, partnerPub, partnerPriv, boostxPub)` and `RegisterWithPartnerPublicKeys(partner,
partnerPubs, partnerPriv, boostxPub)`). Any role may be left out (KEYS-57); a registration with every role left out
registers the partner with no keys, so its lookups fail with role errors, not `unknown_partner`. The key list MUST be
copied on registration, and nothing a lookup returns can change the stored list (JS returns a frozen array, Go a copy).
A partner id that is empty, or not a string where the language allows one, MUST be refused with `missing_claim`, before
any key is checked ([P-builder-ids](#p-builder-ids)). (Vectors: `keys.json`, `http.json`.)

<a id="keys-57"></a><a id="gid-26"></a>**KEYS-57. Registration checks every key.** Registration MUST check every key it is
given against its role: each partner public key and the BoostX public key a usable ECDSA P-256 public key, the partner
private key a usable ECDSA P-256 private key ([KEYS-63](#keys-63)). Unlike a parser, it skips nothing: an unusable or
null entry in a list refuses the registration. A role is left out when the caller does not supply it: an omitted option
or argument, null where the language tells null from absence ([P-null-absent](#p-null-absent)), or, in Go, a nil key
passed to the single-key `Register`. A registration whose purpose is to supply the list (Go
`RegisterWithPartnerPublicKeys`) refuses an empty list, and nil counts as empty there; a list given in an options object
must be non-empty unless it is absent or null. On refusal the role's invalid-key error is raised and the earlier
registration of that partner is kept. The checks run in this order, the first failure reported: the partner id (KEYS-56),
the partner public keys (an empty list, then each entry in list order), the partner private key, the BoostX public key
(decision [registration order](#decision-registration-order)).
A misconfiguration then fails at startup instead of on live traffic; stating absence as "left out" rather than "null"
closes Go's hole, where a list built from empty configuration with `append` stays nil. Also covers: [GID-26](#gid-26),
[HTTP-58](#http-58). (Vectors: `keys.json`, `gidgp.json`, `http.json`.)

<a id="keys-58"></a>**KEYS-58. Lookups.** A lookup for an id that is not registered MUST fail with `unknown_partner`
(both SDKs' message is `unknown partner "<id>"`; message texts are not contract, section 4.5). That includes every id
registration refuses ([KEYS-56](#keys-56)): an empty one and, where the language can pass them, an absent one or one
that is not a string. A lookup of a role that was left out MUST fail with that role's invalid-key error:
`invalid_public_key` for the partner public keys and the BoostX public key, `invalid_private_key` for the partner
private key. Ids match exactly, code unit for code unit: no folding, and no name is special (`__proto__` and
`constructor` are unknown ids). A single-key lookup (Go `PartnerPublicKey`) returns the first listed key. Also covers:
[SETTLE-60](#settle-60). (Vectors: `keys.json`.)

<a id="keys-59"></a>**KEYS-59. Concurrency.** The store MUST be safe to register into while requests are served, and a
lookup MUST see one registration whole, never a mix of two. A store value obtained other than through its constructor
(Go's zero `MemoryKeyStore`, which answers lookups as unknown but panics on `Register`) is outside the spec. (Vectors:
none; concurrency is not observable through the vector operations.)

### 5.8 Errors and optional surface

<a id="keys-60"></a><a id="verifykeys-51"></a>**KEYS-60. Reason of a key error.** The verify-keys reason mapper (JS
`verifyKeysReason(err)`, Go `tokens.VerifyKeysReason(err)`) MUST map an error that carries `invalid_signature` or
`invalid_public_key` anywhere in its cause chain to `signature`, then an error's own reason (`iss-aud`, `stale`,
`nonce-format`) to that reason, and anything else to `shape`. The handlers never reach it for a key error: they answer a
store key that cannot verify with 500 ([KEYS-53](#keys-53)). For an unusable BoostX key, `signature` is the accurate
hint, since BoostX's self-test reads it as a stale or wrong BoostX public key, where `shape` would blame the payload.
Also covers: [VERIFYKEYS-51](#verifykeys-51), [HTTP-57](#http-57). (Vectors: `keys.json`, `verifykeys.json`,
`http.json`.)

<a id="keys-62"></a><a id="gid-42"></a>**KEYS-62. Optional low-level helpers.** Generic JWT sign, verify and extract
helpers, and standalone GID verification, are optional surface ([P-optional-surface](#p-optional-surface)). Go exports
`tokens.SignJWT(claims, privateKey)`, `tokens.ParseJWT(token, claims, publicKey)`, `tokens.ExtractJWTClaims(token,
claims)`, `tokens.RegisteredClaims` and `tokens.VerifyGID(gid, publicKey)` (and the deprecated gamepass parser,
`tokens.ParseGamePassToken` and `tokens.ExtractGamePassClaims`, outside conformance, [GAMEPASS-36](#gamepass-36)); JS
exports none. An
SDK that offers one MUST apply this section's rules: a signer emits KEYS-20, KEYS-25, KEYS-29 and checks its key
(KEYS-17); a verifier runs [KEYS-67](#keys-67) steps 1 to 8 with the same outcome for a key fault (the key error) and for
a signature failure (`invalid_signature`); an extractor runs steps 2 and 8 (KEYS-27); a standalone GID verifier follows
section 6.4. Mapping claims into a structure the caller supplies follows the language's decoder (Go's: case-insensitive
names, field-by-field merging of repeated objects), the one exception to [P-names](#p-names) and
[P-duplicates](#p-duplicates). Claims the spec itself defines are always read by exact name.

Implementation-defined: how a generic helper reports a malformed token or a failure to map claims, since no token
category applies to a generic token (Go's helpers return such errors without a category), and whether a generic signer
serialises the claims before it checks the key. Also covers: [GID-42](#gid-42), [SETTLE-67](#settle-67),
[HTTP-62](#http-62). (Vectors: none; optional surface.)

The builders' key-first order is [KEYS-19](#keys-19), written in 7.2.

## 6. Signed GID (GID)

This section defines the signed GID as an SDK builds and verifies it: the object, the canonical bytes its signature
covers, the ids, the signature form, verification against a list of partner public keys, and the shape of the `gid`
claim inside an inbound Booster or CheckBet token. The terms GID (the triple `partner`, `user`, `bet`) and signed GID
(the triple plus `signature`) are defined in section 1. For SDK behaviour this section is the authority; the partner
docs describe the same object for people (GID and GamePassJWT).

Rules of this topic whose primary rule is written in section 5, and so are not repeated here:

| Id | Primary | Subject |
|----|---------|---------|
| GID-04 | [KEYS-37](#keys-37) | A lone-surrogate escape anywhere in an inbound token's header or payload makes the token malformed; BoostX refuses such a gamepass |
| GID-06 | [KEYS-35](#keys-35) | Strict UTF-8 for an inbound token's header and payload |
| GID-26 | [KEYS-57](#keys-57) | The in-memory key store refuses an empty or unusable partner public key list at registration |
| GID-28 | [KEYS-34](#keys-34) | `gid`, `partner`, `user`, `bet` and `signature` are matched by exact name |
| GID-33 | [KEYS-49](#keys-49) | Unverified extraction runs every claim check, the gid shape included, before any key lookup |
| GID-38 | [KEYS-61](#keys-61) | How the gid is written inside an emitted payload is free; only the canonical bytes are fixed |
| GID-42 | [KEYS-62](#keys-62) | Standalone GID verification and exported canonical bytes are optional surface |
| GID-44 | [KEYS-51](#keys-51) | The escaping of an echoed partner id in a 400 body is implementation-defined |
| GID-45 | [KEYS-63](#keys-63) | A key that is not a usable P-256 key is a key error, never a crash; skipped inside a list |

### 6.1 Object and canonical bytes

<a id="gid-01"></a>**GID-01. The signed GID object.** A signed GID is a JSON object with four members, `partner`,
`user`, `bet` and `signature`, each a JSON string, named exactly so in lowercase. An SDK MUST represent a signed GID with
exactly these four values (JS `GID` with `partner`, `user`, `bet`, `signature`; Go `tokens.GID` with `Partner`, `User`,
`Bet`, `Signature`, aliased as `boostx.GID`). When an SDK writes a gid into a token it writes these four members and no
other. Their order, escaping and spacing inside the payload are free ([P-emitted-bytes](#p-emitted-bytes),
[KEYS-61](#keys-61)); both SDKs write them in the order `partner`, `user`, `bet`, `signature`. (Vectors: `gidgp.json`.)

<a id="gid-02"></a>**GID-02. The signed bytes.** A GID signature covers exactly the UTF-8 encoding of the canonical text

```text
{"partner":<P>,"user":<U>,"bet":<B>}
```

where `<P>`, `<U>` and `<B>` are the three ids written as JSON strings by [GID-03](#gid-03): those three members, in
that order, with no whitespace anywhere and no `signature` member. The text MUST be rebuilt from the three string values
every time, both when building and when verifying. A verifier MUST NOT sign or verify the gid text as it appears in a
received payload, and MUST NOT re-serialise a received object with a general-purpose encoder: the payload may write the
same values with other escapes, another member order or extra members ([GID-47](#gid-47)). The canonical bytes are the
only bytes in this specification that are fixed exactly ([P-emitted-bytes](#p-emitted-bytes)). (Vectors: `gidgp.json`.)

<a id="gid-03"></a>**GID-03. Writing an id into the canonical text.** Each id is written as `"`, then each of its
characters in order as the table says, then `"`. The ids are well-formed Unicode ([GAMEPASS-07](#gamepass-07)), so
every character is a Unicode scalar value.

| Character | Written as |
|-----------|-----------|
| U+0022 `"` | `\"` |
| U+005C `\` | `\\` |
| U+0008 | `\b` |
| U+0009 | `\t` |
| U+000A | `\n` |
| U+000C | `\f` |
| U+000D | `\r` |
| any other U+0000 to U+001F | `\u00` and two lowercase hex digits, e.g. `\u000b`, `\u001f` |
| everything else | its UTF-8 bytes, unescaped |

"Everything else" includes `/`, `<`, `>`, `&`, U+007F, U+2028, U+2029, every other non-ASCII character and every
character outside the Basic Multilingual Plane. This is exactly what JavaScript's `JSON.stringify` writes for a
well-formed string, which is how BoostX builds the bytes. A language's JSON encoder can write them only if it produces
these bytes exactly; many do not. Go's `encoding/json` escapes `<`, `>` and `&` by default and U+2028 and U+2029 always,
so the Go SDK writes the text by hand (Go `canonicalGIDPayload`, unexported); Python's
`json.dumps(..., separators=(",", ":"), ensure_ascii=False)` matches; any encoder in an HTML-safe or ASCII-only mode
does not. Neither SDK exports the canonical-bytes function (JS `canonicalGIDPayload` in `src/gid.ts` is internal), and
exporting one is optional ([KEYS-62](#keys-62)). (Vectors: `gidgp.json`, where a `gid.build` case pins the bytes by
verifying the built signature over a given `canonical` text.)

<a id="gid-37"></a>**GID-37. Control and astral characters are allowed.** U+0000 and every other C0 control character,
U+2028, U+2029 and characters outside the Basic Multilingual Plane are valid in an id. A builder MUST NOT refuse them;
they are signed in the escaped form (C0) or literal form (the rest) of [GID-03](#gid-03). The limits of
[GID-09](#gid-09) still apply, each such character counting as one: a 33rd astral character in `partner` is refused for
the length, not for being astral. (Vectors: `gidgp.json`.)

<a id="gid-47"></a>**GID-47. Decoded values.** On verification the canonical-form check of the signature
([GID-16](#gid-16)) and the canonical bytes ([GID-02](#gid-02)) apply to the decoded JSON string values: escapes inside
a gid member are resolved first. A `signature` member whose first character is written as a `\u` escape is accepted when
the decoded text is canonical, and a `user` written `"u\u003c1"` contributes the literal `<` to the canonical bytes.
(Vectors: `gidgp.json`.)

<a id="gid-39"></a>**GID-39. Canonical-byte and signature test data.** Each SDK's test suite MUST check its canonical
bytes against the shared cases and MUST check the signature test vector `vectors/golden/gid-signature.json` three ways:
its canonical bytes equal the 72 bytes the file gives in hex; the file's signature verifies under the file's public key;
and a signature the SDK makes over the same triple with the file's private key verifies under that public key. The
shared cases are the `gid.build` cases of the conformance file `gidgp.json`, which cover every character class of
[GID-03](#gid-03) (plain, ampersand, angle brackets, quote and backslash, short control escapes, line separators, other
C0 including U+0001, Cyrillic, astral). BoostX's encoder produces every one of them. The suite may reach the canonical
bytes and the GID verifier through internal functions, since neither need be public ([GID-42](#gid-42),
[GID-43](#gid-43)). (Vectors: `gidgp.json`; the signature test vector is an obligation on each SDK's own suite.)

### 6.2 Ids

The id rules apply to every builder that signs a GID: `buildGID`, the gamepass builder (section 7) and the settlement
builder (section 9).

<a id="gamepass-07"></a><a id="gid-35"></a>**GAMEPASS-07. Builder ids.** `partner`, `user` and `bet` are required
parameters of every builder that signs a GID, checked in this way:

1. Absent, null or the empty string: `missing_claim`, naming the parameter (`partner`, `user` or `bet`).
2. Any other value that is not a string, a number or boolean included: `invalid_claim`, naming the parameter. The value
   is never converted to text. A statically typed SDK meets this through its parameter types, and conformance runners
   skip the cases it cannot express (FORMAT section 7).
3. A string that is not well-formed Unicode, then one that contains `:` ([GID-10](#gid-10)), then one longer than its
   limit of 32 (`partner`), 64 (`user`) or 96 (`bet`) Unicode scalar values ([GID-09](#gid-09)): `invalid_claim`, naming
   the parameter. Well-formed means: in a language whose strings are UTF-16 code units, no unpaired surrogate (JS
   `String.prototype.isWellFormed()`); in a language whose strings are bytes, valid UTF-8 by RFC 3629, so no overlong
   form, no encoded surrogate (`ED A0 80` to `ED BF BF`) and nothing above U+10FFFF (Go `utf8.ValidString`); in a
   language whose strings are code points, no code point from U+D800 to U+DFFF. The test is on the SDK's own string
   type, so the same surrogate pair can differ: Python can hold a high and a low surrogate as two code points (text
   decoded with `surrogatepass`), which is refused, while JS reads the same two UTF-16 units as one well-formed
   character.

Steps 1 and 2 run for `partner`, then `user`, then `bet`, early in the builder's order. Step 3 runs after every other
parameter check ([KEYS-19](#keys-19)), per id: `partner`, then `user`, then `bet`, each through all three of its checks
before the next, so a `:` in `partner` is reported ahead of an ill-formed `user`. An SDK MUST NOT check whitespace, and
MUST NOT trim, case-fold or normalise an id ([GID-08](#gid-08)). Step 1 refuses an empty id because one is almost
always a fault in the caller's code. Also covers: GID-35. The settlement builder's ids follow this same rule
([SETTLE-10](#settle-10)). Applies [P-builder-ids](#p-builder-ids), [P-surrogates](#p-surrogates) and
[P-null-absent](#p-null-absent). (Vectors: `gidgp.json`.)

The inbound half of the well-formed rule is token-level: a lone-surrogate escape anywhere in an inbound token's header
or payload makes the token malformed before any gid is read ([KEYS-37](#keys-37), which also covers GID-04).

<a id="gid-05"></a>**GID-05. Ids that are not valid UTF-8.** In a language whose strings are bytes, an id that is not
valid UTF-8 is refused with `invalid_claim` ([GAMEPASS-07](#gamepass-07) step 3). Why: the token payload cannot carry
such bytes unchanged. A JSON encoder replaces them (Go's `encoding/json` writes U+FFFD) while the signature would cover
the raw bytes, so the token could never verify at BoostX. (Vectors: `gidgp.json`, using `{"$illFormed": …}`.)

<a id="gid-07"></a>**GID-07. Empty ids.** Building a GID, directly or inside a gamepass or settlement token, refuses an
empty `partner`, `user` or `bet` with `missing_claim` before anything is signed ([GAMEPASS-07](#gamepass-07) step 1).
(Vectors: `gidgp.json`.)

<a id="gid-08"></a>**GID-08. No normalisation.** Ids are used exactly as given. An SDK MUST NOT trim, case-fold or
Unicode-normalise them: whitespace-only and padded ids build and verify, and an inbound `gid.partner` is returned and
matched to keys code unit for code unit. Key lookups follow the same rule for the partner id ([KEYS-48](#keys-48)).
(Vectors: `gidgp.json`.)

<a id="gid-09"></a>**GID-09. Id length.** A builder that signs a GID MUST refuse a `partner` longer than 32, a `user`
longer than 64 or a `bet` longer than 96 Unicode scalar values with `invalid_claim`, naming that id, checked as
[GAMEPASS-07](#gamepass-07) step 3 orders it. The length counts scalar values, never bytes, UTF-16 code units or
grapheme clusters: JS `[...s].length`, Java `s.codePointCount(0, s.length())`, Go `utf8.RuneCountInString`, Python
`len`, Swift `s.unicodeScalars.count` (not `s.count`). A character outside the Basic Multilingual Plane counts as one,
and so does a character the canonical text writes as an escape ([GID-03](#gid-03)). An empty id is `missing_claim`
([GAMEPASS-07](#gamepass-07) step 1), so the limit is an upper bound only. Parsing an inbound token MUST NOT check the
length, since a game opened before this rule keeps its gid for life. Why: BoostX identifies a game by the three ids
([GID-11](#gid-11)) and refuses a gamepass whose ids break this rule (decision [ids hold no `:` and have bounded
lengths](#decision-gid-id-rules)). (Vectors: `gidgp.json`, `inbound.json`.)

<a id="gid-10"></a>**GID-10. No `:` in an id.** A builder that signs a GID MUST refuse a `partner`, `user` or `bet` that
contains U+003A `:` with `invalid_claim`, naming that id, checked as [GAMEPASS-07](#gamepass-07) step 3 orders it. Only
U+003A is refused: the full-width U+FF1A and other look-alikes are ordinary characters, and nothing is normalised before
the check ([GID-08](#gid-08)). Parsing an inbound token MUST NOT check for `:`, since a game opened before this rule
keeps its gid for life. Why: BoostX identifies a game by the three ids ([GID-11](#gid-11)) and refuses a gamepass whose
ids break this rule (decision [ids hold no `:` and have bounded lengths](#decision-gid-id-rules)). An SDK's
documentation SHOULD state this rule and the limits of [GID-09](#gid-09) where it documents the id parameters.
(Vectors: `gidgp.json`, `inbound.json`.)

### 6.3 Signing

`buildGID` (JS `buildGID(privateKey, partner, user, bet): Promise<GID>`; Go `tokens.BuildGID(partner, user, bet,
privateKey) (*GID, error)`, also `boostx.BuildGID`) is required surface. It returns the signed GID with the three ids
exactly as given and the signature of [GID-14](#gid-14). Its check order is list A of [KEYS-19](#keys-19).

<a id="gid-13"></a>**GID-13. Algorithm.** The GID signature is ES256: ECDSA on P-256 with SHA-256 over the canonical
bytes of [GID-02](#gid-02), made with the partner private key and verified with a partner public key.
(Vectors: `gidgp.json`.)

<a id="gid-14"></a>**GID-14. Signature form.** A built signature is the raw 64-byte `r || s`, each integer left-padded to
32 bytes, encoded as unpadded base64url ([P-base64url](#p-base64url)). It is therefore always 86 characters, matches
`^[A-Za-z0-9_-]{85}[AQgw]$` and is canonical. An SDK MUST NOT emit a DER signature or any other encoding of the same
bytes. (Vectors: `gidgp.json`; every accepted builder result is checked this way, FORMAT 5.3.)

<a id="gid-15"></a>**GID-15. Signatures are not unique.** A verifier MUST accept both S forms of a valid signature (`s`
and `n - s`) and MUST NOT require low-S.

Implementation-defined: how a builder makes its nonce (random, as both SDKs do, or deterministic per RFC 6979) and which
S form it produces. Consequently a signature text is never an identity or a deduplication key: the same triple has many
valid signatures, and a game is identified by the triple alone ([GID-11](#gid-11)). Conformance never compares a built
signature's text, only verifies it. (Vectors: `gidgp.json`.)

<a id="gid-36"></a>**GID-36. The private key.** Building requires a usable ECDSA P-256 private key
([P-key-usability](#p-key-usability), [KEYS-63](#keys-63)). Absent, a public key, a key on another curve, or any key
that fails the checks a platform can make without signing is `invalid_private_key`, reported before any parameter
([KEYS-19](#keys-19)). A key that passes those checks but fails when signing is also `invalid_private_key`, raised at
that point. The key is the platform key object the SDK's loaders return (JS `CryptoKey` from `loadPrivateKeyFromPEM`; Go
`*ecdsa.PrivateKey` from `keys.LoadPrivateKeyFromPEM`); builders do not take PEM text. (Vectors: `gidgp.json`.)

<a id="gid-21"></a>**GID-21. A GID is signed afresh for every token.** No builder takes a pre-signed GID or a signature
as input. Every gamepass and settlement token carries a GID signed during that call with the private key that call was
given, so the GID always matches the key the token is signed with. Why: BoostX verifies the GID of every gamepass,
re-entries included, and of every settlement against the one partner public key it holds now, so a GID stored from
before a key rotation would be refused. (No vector: not observable beyond [GAMEPASS-06](#gamepass-06).)

### 6.4 Verification

GID verification is required inside the Booster and CheckBet parsers (JS `parseBoosterToken(token, boostxPublicKey,
partnerPublicKeys)` and `parseCheckBetToken(…)`, where `partnerPublicKeys` is one key or a list; Go
`tokens.ParseBoosterTokenWithKeys(token, boostxPub, partnerPubs)`, `tokens.ParseCheckBetTokenWithKeys(…)`, and the
single-key `ParseBoosterToken`, `ParseCheckBetToken`). A standalone verifier is optional ([GID-43](#gid-43)). The whole
parse order is [INBOUND-32](#inbound-32); the GID's part of it is [KEYS-46](#keys-46) at the start and
[GID-46](#gid-46) at the end.

<a id="keys-46"></a><a id="gid-25"></a><a id="inbound-31"></a>**KEYS-46. Keys before the token.** A Booster or CheckBet parser checks its keys
before it reads anything of the token, in this order:

1. The BoostX public key MUST be usable ([P-key-usability](#p-key-usability)).
2. The partner public key list MUST contain at least one usable key. An empty list has none; so does a single-key call
   given no key.

A failure at either step is `invalid_public_key`, whatever the token holds, and the error carries `invalid_public_key`
alone: it is not wrapped in `invalid_booster` or `invalid_checkbet`. When both steps would fail, step 1's failure is the
one reported ([INBOUND-59](#inbound-59)); the category is the same, only the message differs. A handler answers a key
failure 500 `{"error":"failed to verify token"}` ([HTTP-26](#http-26)); a token that unverified extraction refuses has
already been answered 400 before any key lookup ([KEYS-49](#keys-49)).

Implementation-defined: how much of a key's usability a platform can judge before verifying. Go checks the curve, the
presence of both coordinates and that the point is on the curve and not at infinity; JS checks that the `CryptoKey` is
an ECDSA P-256 public key with the `verify` usage, since Web Crypto validates the point at import. A listed key that
passes this check but then fails to verify for any reason other than a bad signature is skipped ([GID-24](#gid-24)); if
no listed key could verify at all, the result is `invalid_public_key`. Also covers: GID-25, INBOUND-31.
[HTTP-26](#http-26) is the handler view of the same rule. Applies [P-check-order](#p-check-order). (Vectors: `gidgp.json`,
`inbound.json`, `http.json`, `keys.json`, `verifykeys.json`.)

<a id="keys-47"></a><a id="gid-17"></a><a id="inbound-26"></a>**KEYS-47. A malformed GID signature fails like an unverified one.** A
`gid.signature` that is not in canonical form ([GID-16](#gid-16)) is refused before any key is tried. The error carries
both `invalid_gid` and `invalid_signature`, inside the token's category (`invalid_booster` or `invalid_checkbet`),
exactly as for a canonical signature that no usable listed key verifies ([GID-18](#gid-18)). The message can say which
case it was, since message texts are free ([HTTP-60](#http-60)). A handler answers either case 400 (the token's
refusal). Why: BoostX itself treats a malformed GID signature as a failed verification, and with both categories on both
cases a caller checking for either one matches every GID signature failure. Also covers: GID-17, INBOUND-26.
[HTTP-55](#http-55) is the handler view of the same rule. Applies [P-base64url](#p-base64url) and
[P-signature-vs-shape](#p-signature-vs-shape). (Vectors: `gidgp.json`, `inbound.json`, `keys.json`, `http.json`.)

<a id="gid-16"></a>**GID-16. Canonical form only.** On verification a `gid.signature` is accepted only if the whole
decoded string matches `^[A-Za-z0-9_-]{85}[AQgw]$`. `=` padding, the `+` and `/` alphabet, whitespace or CR/LF anywhere
(a trailing newline included), any other length, and non-zero unused bits in the last character are refused even when
they decode to the right 64 bytes. Equivalently: strict unpadded base64url decoding to exactly 64 bytes whose
re-encoding gives back the text ([P-base64url](#p-base64url)). The match MUST cover the whole string: an implementation
whose regular-expression `$` also matches before a final newline (Python `re.match`, PCRE without `D`, Ruby) MUST use a
full-match form (`re.fullmatch`, `\z`, Java `matches()`). JS uses a strict decoder plus a length check, Go the regular
expression; the two accept exactly the same texts. (Vectors: `gidgp.json`.)

<a id="gid-18"></a>**GID-18. No listed key verifies.** A canonical signature that no usable listed key verifies is
refused with `invalid_signature` and `invalid_gid`, inside the token's category. A handler answers 400.
(Vectors: `gidgp.json`.)

<a id="gid-19"></a>**GID-19. A token-signature failure is not a GID failure.** A failure of the outer BoostX token
signature carries `invalid_signature` but never `invalid_gid`. So `invalid_gid` in the chain tells a GID failure (for
example a GID signed with a key the partner no longer lists) from a token-signature failure. (Vectors: `gidgp.json`.)

<a id="gid-20"></a>**GID-20. Several partner public keys.** A parser MUST accept a list of partner public keys, so that
a partner can keep the old key listed during a rotation. The GID passes when any usable listed key verifies it, whatever
its position in the list ([KEYS-45](#keys-45)).

Implementation-defined: whether keys are tried in order and whether trying stops at the first success, which no caller
can observe. (Vectors: `gidgp.json`.)

<a id="gid-22"></a>**GID-22. The gid as received.** A verified Booster or CheckBet carries the gid's four decoded values
unchanged, and the handlers hand exactly those to the bet store ([GID-41](#gid-41)). Unknown gid members are dropped
([GID-29](#gid-29)). Why: BoostX sends in every CheckBet and Booster the signed GID of the gamepass that created the
game, unchanged for the game's life, so the partner looks the bet up by that triple. (Vectors: `gidgp.json`.)

<a id="gid-23"></a>**GID-23. An empty key list is a key error.** An empty partner public key list is
`invalid_public_key`, not a token error ([KEYS-46](#keys-46) step 2). (Vectors: `gidgp.json`.)

<a id="gid-24"></a>**GID-24. Unusable listed keys are skipped.** A listed partner public key that cannot verify is
skipped, so a later key can still verify the GID. When at least one usable key was tried and refused the signature, the
result is `invalid_signature` with `invalid_gid` ([GID-18](#gid-18)), whatever unusable keys sat beside it; only when no
listed key could verify at all is the result `invalid_public_key` ([KEYS-46](#keys-46)). Verification never crashes on
any key value ([KEYS-63](#keys-63)). (Vectors: `gidgp.json`.)

<a id="gid-40"></a>**GID-40. GID verification is always on.** The handlers MUST verify the GID of every Booster and
CheckBet, and an SDK MUST NOT offer an option, store method or configuration that disables it. A partner who writes
their own endpoints can leave GID verification out; an SDK always does it, which costs nothing and refuses a GID signed
with a key the partner no longer lists. (Vectors: `gidgp.json`.)

<a id="gid-43"></a>**GID-43. Standalone verification.** A standalone GID verifier is optional surface
([KEYS-62](#keys-62)); Go offers one with a single key (`tokens.VerifyGID(gid, publicKey)`, not re-exported from
package `boostx`), JS none (its `verifyGID` is internal). An SDK that offers one applies [KEYS-46](#keys-46) step 2 to
its keys first, then [GID-46](#gid-46)'s GID steps, with the same categories but no token category around them. Where the
language allows a null GID, a null GID is refused with `invalid_gid` alone, after the key check, so an unusable key is
reported first. (No vector: optional surface.)

<a id="gid-46"></a>**GID-46. The GID signature is checked last.** After the key checks of [KEYS-46](#keys-46), the GID
signature is examined only once the token signature has verified and every claim check has passed: the root object, the
gid shape ([GID-27](#gid-27)), a non-empty `gid.partner`, the token's own fields, `iat`, `exp` and `nbf`
([INBOUND-32](#inbound-32)). A token that fails any earlier step reports only that failure, with no `invalid_gid` from
the signature. GID verification itself runs:

1. Form: the signature's canonical form ([GID-16](#gid-16)); a failure is [KEYS-47](#keys-47).
2. Keys: rebuild the canonical bytes from the decoded `partner`, `user` and `bet` ([GID-02](#gid-02)), decode the 64
   bytes and verify ES256 under each usable listed key ([GID-20](#gid-20), [GID-24](#gid-24)); acceptance on the first
   key that verifies, otherwise [GID-18](#gid-18) or `invalid_public_key` as [GID-24](#gid-24) says.

Applies [P-check-order](#p-check-order). (Vectors: `gidgp.json`.)

### 6.5 Inbound gid shape

<a id="gid-27"></a><a id="inbound-17"></a>**GID-27. The gid claim's shape.** In a Booster or CheckBet payload the root object's `gid` member is
read as follows, and the first failing step is reported, wrapped in the token's category:

1. `gid` absent: `missing_claim`, naming `gid`.
2. `gid` present but not a JSON object (null, a string, a number, a boolean, an array): `invalid_gid`.
3. Any of `partner`, `user`, `bet` and `signature` absent, null or not a JSON string: `invalid_gid`.
4. `partner` is the empty string: `missing_claim`, naming `gid.partner`.

Members are read by exact name ([KEYS-34](#keys-34)) and a repeated name takes its last value ([GID-30](#gid-30)). Other
members are ignored ([GID-29](#gid-29)). An empty `user` or `bet` passes ([GID-32](#gid-32)), and an empty `signature`
passes this step and fails the form check later ([GID-16](#gid-16)). These checks run with the other claim checks, in
unverified extraction and in parsing alike ([KEYS-49](#keys-49)), before the GID signature is examined
([GID-46](#gid-46)). Also covers: INBOUND-17. Applies [P-one-value](#p-one-value),
[P-null-absent](#p-null-absent) and [P-names](#p-names). (Vectors: `gidgp.json`, `keys.json`, `inbound.json`,
`http.json`.)

<a id="gid-29"></a>**GID-29. Unknown gid members.** Members of the gid object other than the four are ignored: they
never supply or override a named member, and they are not part of the result or of what the bet store receives.
(Vectors: `gidgp.json`.)

<a id="gid-30"></a>**GID-30. Repeated gid members.** A gid member that appears twice under exactly the same name takes
its last value, as anywhere in the JSON an SDK reads ([P-duplicates](#p-duplicates)). A member whose name differs only
in case is a different, unknown member ([KEYS-34](#keys-34)). (Vectors: `gidgp.json`.)

<a id="gid-31"></a>**GID-31. Empty `gid.partner`.** An inbound token whose `gid.partner` is the empty string is refused
with `missing_claim` naming `gid.partner`, in extraction and parsing alike, so a handler answers 400 before any key
lookup. (Vectors: `gidgp.json`.)

<a id="gid-32"></a>**GID-32. Empty `user` or `bet` inbound.** An inbound gid with an empty `user` or `bet` passes the
shape check and is verified over the empty value. An SDK MUST NOT refuse it there, although its builders refuse empty
ids ([GAMEPASS-07](#gamepass-07)): the verdict on an inbound GID belongs to its signature. (Vectors: `gidgp.json`.)

### 6.6 Bet store

<a id="gid-41"></a>**GID-41. The bet store receives the verified GID.** The handlers call the bet store only after GID
verification passed. `checkBet` receives the gid (JS `BetStore.checkBet(gid)`; Go `CheckBet(ctx, *GID)` of
`handlers.BetStoreChecker`) and `setBoost` the Booster, which carries it (JS `Booster.gid`; Go `tokens.Booster` embeds
`GID`). The partner looks the bet up by the triple ([GID-11](#gid-11)). (Vectors: `gidgp.json`.)

The key-store rules that touch the GID (registration of a partner public key list, the unknown-partner answer) are
[KEYS-57](#keys-57) and [KEYS-51](#keys-51).

### 6.7 Optional surface

Required GID surface: `buildGID`, and GID verification inside the Booster and CheckBet parsers, which accept one partner
public key or several. Optional ([KEYS-62](#keys-62)): a standalone verifier ([GID-43](#gid-43)), a multi-key standalone
verifier (neither SDK), and an exported canonical-bytes function (neither SDK). An SDK that offers one follows this
section's rules for the signature form, keys, shape and categories. The test-data obligation of [GID-39](#gid-39)
holds whichever is offered.

### 6.8 What the SDK sees from BoostX (informative)

Nothing in this subsection is a requirement on an SDK, and none of it has vectors.

<a id="gid-11"></a>**GID-11. A game is the triple.** BoostX identifies a game by `partner`, `user` and `bet` together;
the signature plays no part. Partner records should therefore be keyed by the triple, never by `gid.signature` or the
token text, which differ between gamepasses for one game ([GID-15](#gid-15)). An SDK's documentation should say so;
the JS README warns against keying by `gid.signature`.

<a id="gid-12"></a>**GID-12. `gid.partner` is the assigned id.** `gid.partner` must be the partner id BoostX assigned. A
settlement that names an id BoostX does not know is answered 404 `not found`: BoostX does not know this partner id, and
the partner checks it ([SETTLE-75](#settle-75)). No SDK can check that an id is the assigned one.

## 7. GamePass builder and X helpers (GAMEPASS)

The gamepass builder signs the GamePassJWT a partner puts in the game URL. It is required surface (JS
`createGamePassToken(privateKey, params): Promise<string>`; Go `tokens.CreateGamePassToken(privateKey, params) (string,
error)`, also `boostx.CreateGamePassToken`), and so are the X helpers of 7.6. The parameters, in the neutral names of the
vectors:

| Neutral | JS (`GamePassParams`) | Go (`tokens.GamePassParams`) | Required | Field an error names |
|---------|----------------------|------------------------------|----------|----------------------|
| `partner`, `user`, `bet` | same | `Partner`, `User`, `Bet` | yes | `partner`, `user`, `bet` |
| `amount` | `amount` | `Amount` | yes | `amount` |
| `currency` | `currency` | `Currency` | yes | `currency` |
| `x` | `x` | `X` | yes | `x` |
| `xMin`, `xMax` | same | `XMin`, `XMax` | no | `xmin`, `xmax` |
| `xDecimals` | `xDecimals` | `XDecimals` | no | `xdecimals` |
| `eventTitle` | `eventTitle` | `EventTitle` | no | `eventTitle` |
| `demo` | `demo` | `Demo` | no | `demo` |

The field names `xmin`, `xmax` and `xdecimals` are lowercase in both SDKs' messages, and the vectors' `field` reads
them so (section 4.5).

Implementation-defined: sync or async, and how the parameter set is passed (an object, a struct), as long as each
parameter can be given or left unset as below.

### 7.1 Token shape, header and iat

<a id="gamepass-01"></a>**GAMEPASS-01. Emitted payload.** The payload of an issued GamePassJWT is a JSON object with
exactly these members, and no other at any depth:

| Member | Present | Value |
|--------|---------|-------|
| `iat` | always | [GAMEPASS-03](#gamepass-03) |
| `gamepass.gid` | always | `buildGID` over `partner`, `user`, `bet` with the same private key: `partner`, `user`, `bet`, `signature` ([GAMEPASS-06](#gamepass-06)) |
| `gamepass.stake.amount` | always | `amount` unchanged ([GAMEPASS-12](#gamepass-12)) |
| `gamepass.stake.currency` | always | `currency` unchanged |
| `gamepass.xrange.init` | always | `x` unchanged ([GAMEPASS-18](#gamepass-18)) |
| `gamepass.xrange.min`, `.max` | when `xMin`, `xMax` is set ([GAMEPASS-23](#gamepass-23)) | the value unchanged |
| `gamepass.xrange.decimals` | when `xDecimals` is set ([GAMEPASS-26](#gamepass-26)) | the integer |
| `gamepass.event.title` | when `eventTitle` is a non-empty string ([GAMEPASS-29](#gamepass-29)) | the title, ill-formed parts replaced ([GAMEPASS-31](#gamepass-31)) |
| `gamepass.demo` | when `demo` is `true` ([GAMEPASS-32](#gamepass-32)) | `true` |

An SDK MUST NOT write `null` for any member, and MUST NOT write `exp`, `nbf` or any member the table does not list. A
number MUST be written so that a binary64 reader recovers exactly the given value.

Implementation-defined: member order, string escaping (including `<`, `>`, `&`, U+2028, U+2029), number spelling
(`1e300` or `1e+300`) and whitespace ([P-emitted-bytes](#p-emitted-bytes), [KEYS-61](#keys-61)): BoostX reads every
member by name. Conformance compares the decoded payload and the listed absent paths, never the bytes. (Vectors:
`gidgp.json`.)

<a id="gamepass-02"></a>**GAMEPASS-02. Header and signature.** The header is exactly the members `alg` `"ES256"` and
`typ` `"JWT"` ([KEYS-20](#keys-20)), and the token is signed ES256 with the partner private key, the same key that signs
the gid. BoostX verifies ES256 only and does not read `typ`. (Vectors: `gidgp.json`; every accepted builder result is
checked this way, FORMAT 5.3.)

<a id="gamepass-03"></a>**GAMEPASS-03. iat.** The SDK stamps `iat` itself when the call runs: the current Unix time in
whole seconds, rounded down, written as a JSON integer. A caller cannot supply `iat`, `exp` or `nbf`, and the SDK adds
no other registered claim. Why: BoostX refuses a gamepass whose `iat` is more than 300 seconds from its clock when the
game opens ([GAMEPASS-04](#gamepass-04)), so a token is minted immediately before the game is opened with it; SDK
documentation SHOULD say so (both SDKs' builder docs do). (Vectors: `gidgp.json`, with the `${now}` time expression.)

### 7.2 Check order, parameters and ids

<a id="keys-19"></a><a id="gamepass-08"></a><a id="gid-34"></a>**KEYS-19. Key first, then parameters.** Every builder
(`buildGID`, the gamepass builder, the settlement builder, the verify-keys request and response builders) first runs
the private-key checks it can make without signing ([GID-36](#gid-36)): present, an ECDSA P-256 private key, and, where
the platform exposes it, a valid scalar and point. A key that fails them is `invalid_private_key`, whatever else is
wrong. Only then are the parameters checked, in the builder's order, and the first failing check is reported. A key that
passes the up-front checks but fails at signing is `invalid_private_key` at that point. Also covers: GAMEPASS-08,
GID-34. The settlement builder's order is [SETTLE-31](#settle-31) and the verify-keys builders' is
[VERIFYKEYS-49](#verifykeys-49). Applies [P-check-order](#p-check-order).

List A, `buildGID`:

1. The private key: `invalid_private_key`.
2. `partner`, then `user`, then `bet`: presence and type ([GAMEPASS-07](#gamepass-07) steps 1 and 2).
3. `partner`, then `user`, then `bet`, each: well-formed Unicode, no `:`, within its length
   ([GAMEPASS-07](#gamepass-07) step 3).
4. Sign; a failure is `invalid_private_key`.

List B, the gamepass builder:

1. The private key: `invalid_private_key`.
2. `partner`, then `user`, then `bet`: presence and type ([GAMEPASS-07](#gamepass-07) steps 1 and 2).
3. `currency`: presence, then shape ([GAMEPASS-13](#gamepass-13), [GAMEPASS-14](#gamepass-14)).
4. `amount` ([GAMEPASS-11](#gamepass-11)).
5. `x` ([GAMEPASS-19](#gamepass-19)).
6. `xMin`, then `xMax` ([GAMEPASS-24](#gamepass-24)), then `xDecimals` ([GAMEPASS-26](#gamepass-26)).
7. The type of `eventTitle` ([GAMEPASS-29](#gamepass-29)), then of `demo` ([GAMEPASS-32](#gamepass-32)); reachable only
   in a language that lets a caller pass another type.
8. `partner`, then `user`, then `bet`, each: well-formed Unicode, no `:`, within its length
   ([GAMEPASS-07](#gamepass-07) step 3).
9. Sign the GID, then the token; a failure is `invalid_private_key`.

A missing parameter set reads as an empty one ([GAMEPASS-48](#gamepass-48)), so with a usable key its first failure is
`missing_claim` for `partner`. (Vectors: `gidgp.json`, `keys.json`, `verifykeys.json`, including cases with several
faults.)

<a id="gamepass-09"></a>**GAMEPASS-09. One error per call.** The gamepass builder reports exactly one error, the first
failing step of list B ([KEYS-19](#keys-19)). The id checks (well-formedness, `:`, length) run after every other
parameter, as part of building the GID, and a key that passed step 1 can still fail at step 9. The category and the
field are those the step names; message texts beyond the `missing required claim: <field>` /
`invalid claim value: <field>` phrasing are free ([HTTP-60](#http-60)). (Vectors: `gidgp.json`.)

<a id="gamepass-06"></a>**GAMEPASS-06. The gid is the SDK's own.** The builder builds `gamepass.gid` with its own
`buildGID` over the `partner`, `user` and `bet` parameters and the private key it was given. It MUST NOT accept a gid, a
signature or a pre-built GID from the caller ([GID-21](#gid-21)). A gid the SDK builds with the partner private key that
matches the partner public key BoostX holds, for the partner id BoostX assigned ([GID-12](#gid-12)), is one BoostX
accepts. (Vectors: `gidgp.json`; the builder checks of FORMAT 5.3 verify the gid.)

Ids: [GAMEPASS-07](#gamepass-07) (6.2) applies to the gamepass builder's `partner`, `user` and `bet`.

<a id="gamepass-34"></a>**GAMEPASS-34. Null means unset.** Where a language tells null from absence, a null parameter
means absent ([P-null-absent](#p-null-absent)):

- `partner`, `user`, `bet` or `currency` null: `missing_claim`, as when absent or empty.
- `amount` or `x` null: `invalid_claim`, as when absent or 0.
- `xMin`, `xMax`, `xDecimals`, `eventTitle` or `demo` null: unset, and the member is left out of the token.

The SDK never writes `null` into a token. Null optional parameters therefore produce the same token as absent ones in
JS and as the zero values in Go, and no gamepass case needs `wantZeroValue`. Applies [P-zero](#p-zero).
(Vectors: `gidgp.json`.)

<a id="gamepass-48"></a>**GAMEPASS-48. A missing parameter set.** A parameter set that is absent, null or not an object
(a value of no kind the SDK reads parameters from, such as a number where a dynamically typed SDK takes a key-value map,
section 3.4) is read as an empty one; after the key check the first failure is then `missing_claim` for `partner`. Every
error the builder raises is the SDK's own error type with a category ([P-taxonomy](#p-taxonomy)), never a language
runtime error from reading the missing set. A statically typed SDK that takes a struct meets this trivially; runners
skip such cases there (FORMAT section 7). (Vectors: `gidgp.json`.)

### 7.3 Stake

<a id="gamepass-10"></a>**GAMEPASS-10. The stake object.** `gamepass.stake` is always sent, as an object with a number
`amount` and a string `currency`. (Vectors: `gidgp.json`.)

<a id="gamepass-11"></a>**GAMEPASS-11. Amount.** `amount` MUST be a number that is finite and at least 0.01, compared as
an IEEE-754 binary64 value (`amount >= 0.01`), in every currency. Anything else is `invalid_claim` naming `amount`:
absent, null, 0, -0, a negative number, a positive number below 0.01 (`0.009999`, `1e-320`), NaN, ±Infinity, or a
non-number such as the string `"5"`. Why: BoostX refuses such a gamepass when the game opens (decision [minimum stake
0.01](#decision-minimum-stake)). (Vectors: `gidgp.json`.)

<a id="gamepass-12"></a>**GAMEPASS-12. No maximum, no rounding.** `amount` has no upper bound and no precision or step
limit: any finite value of at least 0.01 is sent unchanged, never rounded and never converted to minor units. It is the
stake in major units of `currency` (`12.5` for twelve euros fifty). (Vectors: `gidgp.json`.)

<a id="gamepass-13"></a>**GAMEPASS-13. Missing currency.** `currency` absent, null or the empty string is
`missing_claim` naming `currency` ([P-currency](#p-currency)). (Vectors: `gidgp.json`.)

<a id="gamepass-14"></a><a id="gamepass-15"></a>**GAMEPASS-14. Currency shape.** A present, non-empty `currency` MUST be
a string that matches `^[A-Z]{3,4}$` as a whole: three or four ASCII capital letters, case-sensitive. Anything else is
`invalid_claim` naming `currency`: a lowercase or mixed-case code (`usd`, `Usd`), five letters, surrounding whitespace
or a trailing newline, a non-ASCII letter, or a non-string. No case mapping and no trimming is applied, and the code is
sent unchanged. The SDK does not check whether BoostX serves the code; BoostX's list is not published and an SDK MUST
NOT embed it. The match MUST cover the whole string ([GID-16](#gid-16) says how for regular-expression engines); a
byte-wise check of length and range, as Go's `validCurrencyCode` does, is equivalent. The same rule governs the
settlement payout currency ([SETTLE-21](#settle-21)). Also covers: GAMEPASS-15. Applies [P-currency](#p-currency)
(decision [one uppercase currency rule](#decision-currency-case)). (Vectors: `gidgp.json`.)

<a id="gamepass-47"></a>**GAMEPASS-47. No Unicode case mapping.** The currency check MUST be the ASCII-only,
case-sensitive test of [GAMEPASS-14](#gamepass-14), with no case mapping before it. A Unicode upper-casing would turn
`uſd` (U+017F) into `USD` and `ınr` (U+0131) into `INR`; under this rule both are refused like any other non-matching
code. BoostX does not upper-case either ([P-currency](#p-currency)). (Vectors: `gidgp.json`.)

### 7.4 xrange

<a id="gamepass-18"></a>**GAMEPASS-18. The xrange object.** `gamepass.xrange` is always sent, as an object whose `init`
is the `x` parameter unchanged. `x` is the partner's own coefficient for the bet before the boost, never an X derived
from a `boost`. (Vectors: `gidgp.json`.)

<a id="gamepass-19"></a>**GAMEPASS-19. The x gate.** `x` MUST be a number that is finite and greater than 0; -0 counts as
0. Anything else is `invalid_claim` naming `x`: absent, null, 0, -0, a negative number, NaN, ±Infinity or a non-number.
The SDK applies no range check: `[1.1, 200]`, `xMin < xMax` and the bounds on X are BoostX's, so `0.5`, `1e-300` and
`200.009` are signed. Applies [P-zero](#p-zero). (Vectors: `gidgp.json`.)

<a id="gamepass-23"></a>**GAMEPASS-23. xMin and xMax are optional.** `xMin` and `xMax` that are absent, null, 0 or -0 are
unset, and `xrange.min` and `xrange.max` are then left out of the token, so BoostX applies its defaults 1.1 and 200. A
set value passing [GAMEPASS-24](#gamepass-24) is sent unchanged. Applies [P-zero](#p-zero). (Vectors: `gidgp.json`.)

<a id="gamepass-24"></a>**GAMEPASS-24. The xMin and xMax gate.** A set `xMin` or `xMax` MUST be a number that is finite
and not negative. A negative number, NaN, ±Infinity or a non-number is `invalid_claim` naming `xmin` or `xmax`. Any
other value is sent unchecked, `0.5` and `1e300` included; the bounds are BoostX's ([GAMEPASS-19](#gamepass-19)).
(Vectors: `gidgp.json`.)

<a id="gamepass-25"></a>**GAMEPASS-25. A bound of 0 cannot be sent.** Because 0 means unset
([GAMEPASS-23](#gamepass-23)), an SDK never sends `xrange.min` or `xrange.max` as 0. Neither lies in `[1.1, 200]`, so no
valid gamepass is lost. (Vectors: `gidgp.json`.)

<a id="gamepass-26"></a>**GAMEPASS-26. xDecimals.** `xDecimals` that is absent, null, 0 or -0 is unset, and
`xrange.decimals` is left out (BoostX's default is 2). Otherwise it MUST be an integer-valued number from 2 to 6, sent
as that integer; an integral value written `2.0` is the integer 2. Anything else is `invalid_claim` naming `xdecimals`:
1, 7, a negative number, 2.5, NaN, ±Infinity or a non-number. Applies [P-zero](#p-zero). (Vectors: `gidgp.json`.)

What a later gamepass for the same bet changes is [GAMEPASS-21](#gamepass-21) and [GAMEPASS-28](#gamepass-28) in 7.7.

### 7.5 Event title, demo and unknown parameters

<a id="gamepass-29"></a>**GAMEPASS-29. Event title.** `gamepass.event` is sent, as `{"title": <title>}`, exactly when
`eventTitle` is a non-empty string; a whitespace-only title is non-empty and is sent. An `eventTitle` that is absent,
null or the empty string is unset and `event` is left out. In a language that lets a caller pass another type, a
non-string `eventTitle` is `invalid_claim` naming `eventTitle` ([KEYS-19](#keys-19) list B step 7).
(Vectors: `gidgp.json`.)

<a id="gamepass-30"></a>**GAMEPASS-30. Title length and form.** The SDK applies no length limit and no trimming or
Unicode normalisation to the title; it is sent as given, except for the replacement of [GAMEPASS-31](#gamepass-31).
BoostX shows it on the game screen as signed. (Vectors: `gidgp.json`.)

<a id="gamepass-31"></a>**GAMEPASS-31. An ill-formed title is repaired, not refused.** An `eventTitle` that is not
well-formed Unicode is sent with each ill-formed part replaced by U+FFFD, and the token is still issued. In a language
whose strings are UTF-16, each lone surrogate becomes exactly one U+FFFD (JS `String.prototype.toWellFormed()`); in
one whose strings are code points, each surrogate code point does, so a pair held as two code points becomes two
([GAMEPASS-07](#gamepass-07) step 3).

Implementation-defined: in a language whose strings are bytes, how many U+FFFD a run of invalid bytes becomes (Go's
`encoding/json` writes one per invalid byte, so an encoded surrogate `ED A0 80` becomes three). This is the one
exception to [P-surrogates](#p-surrogates): the title is display-only and outside the GID, and refusing it would add a
gate on a field live partners send, to protect only a display string. (Vectors: `gidgp.json`, with `{"$illFormed": …}`.)

<a id="gamepass-32"></a>**GAMEPASS-32. Demo.** `gamepass.demo` is sent, as `true`, exactly when `demo` is `true`. `false`,
absent and null are unset and the member is left out; `false` and absence mean the same to BoostX. In a language that
lets a caller pass another type, a non-boolean `demo` (`1`, `"true"`) is `invalid_claim` naming `demo`.
(Vectors: `gidgp.json`.)

<a id="gamepass-33"></a>**GAMEPASS-33. Unknown parameters and members.** A parameter the builder does not define is
ignored where the language lets a caller pass one (except the neutral spelling of a member the SDK spells otherwise,
which [GAMEPASS-50](#gamepass-50) lets it refuse), and the SDK emits no member beyond those of
[GAMEPASS-01](#gamepass-01). BoostX ignores unknown members anyway. (Vectors: none; FORMAT has no input for a parameter
the builder does not define, and a builder's `ok` compares only the members it lists.)

<a id="gamepass-50"></a>**GAMEPASS-50. A neutral spelling the SDK reads under another name.** In a key-value map given
as a gamepass or settlement parameter set, a key that is the neutral spelling of a member the SDK spells otherwise
(`xMin` given to an SDK that reads `x_min`, section 3.4) is either ignored, as [GAMEPASS-33](#gamepass-33) and
[SETTLE-05](#settle-05) say of any key the SDK does not define, or refused. An SDK that refuses it MUST do so with
`invalid_claim` naming that member's field token ([HTTP-72](#http-72)), at that member's step of the check order. Why:
an ignored key leaves its member absent, so a partner porting an example written with the neutral names gets BoostX's
default `xMin`, or a `missing_claim` for `settledAt`, with no hint of the cause.

Implementation-defined: whether such a key is ignored or refused. (No vector: a runner writes every member in its SDK's
spelling.)

### 7.6 X helpers

`floorX` (JS `floorX(x, decimals?)`; Go `tokens.FloorX(x, decimals int)`, also `boostx.FloorX`) floors a coefficient by
BoostX's rule, and `playerX` (JS `playerX(xBase, boost, decimals?)`; Go `tokens.PlayerX(xBase, boost, decimals int)`,
also `boostx.PlayerX`) gives the X the player saw for a Booster's `boost`. Both are required surface. All arithmetic is
IEEE-754 binary64 with round-to-nearest-even. These are BoostX's own rules, so a partner's X matches the X the player
saw; the partner docs describe the same flooring for people (Rounds, Flooring X).

<a id="gamepass-38"></a>**GAMEPASS-38. floorX.** `floorX(x, d)`, with `d` resolved by [GAMEPASS-40](#gamepass-40), is
computed in four steps:

1. `s = x × 10^d`, one binary64 multiplication (`10^d` is exact for `d` from 2 to 6).
2. `r` = `s` rounded to 15 significant decimal digits and converted back to the nearest binary64: format `s` with 15
   significant digits and parse the text (JS `+s.toPrecision(15)`; Go `strconv.FormatFloat(s, 'g', 15, 64)` then
   `strconv.ParseFloat`).
3. `f = floor(r)`, toward negative infinity.
4. The result is `f / 10^d`, one binary64 division.

Step 2 is there because a decimal on the grid is often held just below itself (`1.15 × 100` is `114.99999999999999`),
and a plain floor would land one step low. This is BoostX's own function. (Vectors: `floor-x.json`, `player-x.json`;
`gidgp.json` for single cases.)

<a id="gamepass-39"></a>**GAMEPASS-39. The tie rule is fixed only below 10^14.** Results MUST equal BoostX's exactly
whenever `|x × 10^d| < 10^14`.

Implementation-defined: how an exact tie at the 15th significant digit is rounded when `|x × 10^d| >= 10^14` (BoostX and
JS round half away from zero, Go half to even, so `floorX(5629499534213.125, 2)` is `5629499534213.13` in JS and
`5629499534213.12` in Go). Why the bound: below 10^14 the 15th significant digit is fractional, and a tie can carry into
the integer part only when the kept digit is 9, where half-even rounds up too, so the floor is the same either way. No
vector reaches the bound. (Vectors: `gidgp.json`, below the bound; none above 10^14, by design.)

<a id="gamepass-40"></a>**GAMEPASS-40. The decimals domain.** `decimals` that is absent, null, 0 or -0 means 2.
Otherwise it MUST be an integer from 2 to 6, judged by value as `xDecimals` is ([GAMEPASS-26](#gamepass-26)): an
integral value written `3.0` is 3, while 2.5, NaN, ±Infinity, a boolean or a string is outside the domain. Outside that
domain a helper MUST NOT return a finite number: it raises `invalid_claim` or returns NaN.

Implementation-defined: which of the two (JS raises; Go returns NaN, read as `invalid_claim`, FORMAT 6.3). Applies
[P-zero](#p-zero). (Vectors: `gidgp.json`.)

<a id="gamepass-41"></a>**GAMEPASS-41. Non-finite inputs.** `x`, `xBase` and `boost` are meant to be finite numbers. For
a non-finite or non-number input a helper raises `invalid_claim` or returns a non-finite number (NaN or ±Infinity), and
MUST NOT return a finite number.

Implementation-defined: which of the two (JS raises, Go returns a non-finite result). The cases expect `invalid_claim`,
and a runner accepts a non-finite result as that error (FORMAT 6.3). Finite inputs whose result overflows give ±Infinity
in both (`floorX(1e308, 2)` is +Infinity). (Vectors: `gidgp.json`.)

<a id="gamepass-42"></a>**GAMEPASS-42. playerX.** `playerX(xBase, boost, d)` is `floorX(1 + (floorX(xBase, d) - 1) ×
boost, d)`, the reduced form BoostX uses in live play, with the same resolved `d` for both floors. There is no clamp
below 1 and any boost is accepted, 0 and negatives included: `playerX(0.5, 2)` is 0 and `playerX(2, -1)` is 0. Finite
inputs that overflow give +Infinity. Why `xBase` is floored first: BoostX floors `xrange.init` onto the grid when it
receives the gamepass and boosts the floored value. (Vectors: `player-x.json`; `gidgp.json`.)

<a id="gamepass-43"></a>**GAMEPASS-43. No fused multiply-add.** The raw value `1 + (b - 1) × boost` is computed with each
of its three operations rounded on its own; a fused multiply-add MUST NOT be used, because it can change the last bit
and so the floor. A helper that returns the unfloored raw value is optional (Go `tokens.CalculateFinalCoefficient(x,
boost)`, not in the facade; JS none); one that is offered computes `1 + (x - 1) × boost` unfused and unfloored.
(Vectors: `floor-x.json`, whose `rawX` member is that value, and `gidgp.json`.)

<a id="gamepass-44"></a>**GAMEPASS-44. Which inputs a partner passes.** `xBase` is the `x` (`xrange.init`) signed for the
entry that sent the round, with two exceptions. A `final: true` regular round sent again keeps the `x` of the entry
during which it was first sent. A jackpot round keeps, on every attempt, the `x` of the entry during which BoostX fixed
its result, normally the entry that first sent it. The token carries no `xBase`: when the first attempt never reached
the partner and a later entry changed `x`, the token alone cannot tell which entry's `x` applies. `playerX` on that
`xBase` gives the X the player saw, on a jackpot round too. `decimals` is the bet's `xDecimals` as issued on the
creating gamepass, unset meaning 2. This is guidance for the SDK's documentation (both READMEs give it), not something
a helper can check. (No vector: documentation.)

<a id="gamepass-45"></a>**GAMEPASS-45. Golden X vectors.** `floor-x.json` (3049 cases: `xBase`, `boost`, `decimals`,
`rawX`, `x`) and `player-x.json` (2051 cases: `init`, `boost`, `decimals`, `xBase`, `x`) are generated by BoostX and
published in `vectors/golden/`, which every SDK mirrors with the rest of `vectors/` (section 12.1). Each SDK's test
suite MUST check every case, with binary64 equality: for `floor-x.json`, the unfused `1 + (xBase - 1) × boost` equals
`rawX` and `floorX(rawX, decimals)` equals `x`; for `player-x.json`, `floorX(init, decimals)` equals `xBase` and
`playerX(init, boost, decimals)` equals `x`. The files cover decimals 2 to 6 with finite inputs, all below the tie
bound of [GAMEPASS-39](#gamepass-39); unset decimals and out-of-domain cases are in `gidgp.json`. (Vectors: the two
files themselves, and `gidgp.json` in the shared format.)

<a id="gamepass-49"></a>**GAMEPASS-49. No clamp.** `playerX` is the reduced, unclamped form, and an SDK MUST NOT clamp
it. The general form, `xBase + max(0, xBase - 1) × (boost - 1)`, which leaves X at `xBase` when `xBase` is 1 or less, is
the partner's own rule at settlement, where `xSettle` can be below 1 (section 9.2); a helper for it is optional and
belongs to the settlement topic. (Vectors: `gidgp.json`.)

### 7.7 What the SDK sees from BoostX (informative)

Nothing in this subsection is a requirement on an SDK, and none of it has vectors. How BoostX answers a refused gamepass
is for the game frame, which opens the game, and is not part of this specification.

<a id="gamepass-04"></a>**GAMEPASS-04. Freshness when the game opens.** BoostX refuses a gamepass whose `iat` is more
than 300 seconds from its clock when the game opens, so a gamepass is built right before the game is opened with it
([GAMEPASS-03](#gamepass-03)).

<a id="gamepass-05"></a>**GAMEPASS-05. No other time limit.** A gamepass the SDK builds carries no `exp` or `nbf`
([GAMEPASS-03](#gamepass-03)), so only its `iat` limits when it can open the game.

<a id="gamepass-17"></a>**GAMEPASS-17. Served currencies.** Which stake currencies BoostX serves for a game is BoostX's;
the SDK checks only the shape of the code ([GAMEPASS-14](#gamepass-14)).

<a id="gamepass-20"></a>**GAMEPASS-20. Bounds.** The bounds on `x`, `xMin` and `xMax` are BoostX's
([GAMEPASS-19](#gamepass-19)): the SDK signs any value its own gates pass.

<a id="gamepass-21"></a>**GAMEPASS-21. A later gamepass's x.** A later gamepass for a bet still in play re-enters its
game, and its `x` becomes the `xBase` of the rounds sent from then on, apart from the two exceptions of
[GAMEPASS-44](#gamepass-44).

<a id="gamepass-22"></a>**GAMEPASS-22. The end of a game.** Which rounds BoostX plays is BoostX's; a Booster with
`final: true` tells the partner that the game has ended ([INBOUND-49](#inbound-49)).

<a id="gamepass-27"></a>**GAMEPASS-27. Flooring.** BoostX floors `x` onto the bet's `xDecimals` grid with the rule of
[GAMEPASS-38](#gamepass-38), which is why `playerX` floors `xBase` first ([GAMEPASS-42](#gamepass-42)).

<a id="gamepass-28"></a>**GAMEPASS-28. What a later gamepass changes.** A later gamepass for the same bet changes only
`x`: the stake, the event title, the demo flag, `xMin`, `xMax`, `xDecimals` and the signed GID stay those of the
gamepass that created the game.

<a id="gamepass-35"></a>**GAMEPASS-35. Answers to the game frame.** A refused gamepass is answered to the game frame,
never to the SDK; the partner docs list those answers for people (Errors and troubleshooting).

<a id="gamepass-37"></a>**GAMEPASS-37. The game URL.** The game is opened at
`https://wheel.boostx.cloud/?gamepass=<GamePassJWT>` (partner docs, Iframe integration). No SDK function builds the URL;
percent-encoding the token changes nothing, since a JWT is base64url and dots.

### 7.8 The Go gamepass parser, outside conformance

<a id="gamepass-36"></a>**GAMEPASS-36. No gamepass parser is specified.** This specification defines no gamepass parser
and no conformance cases for one: a partner never receives a gamepass. An SDK that keeps one applies the generic token
rules of [KEYS-62](#keys-62) (canonical segments, strict bytes, the `alg` and `crit` header rules, key usability, exact
names for the claims it reads, the gid shape of [GID-27](#gid-27)) and reports failures as `invalid_gamepass`
([HTTP-54](#http-54)). Its acceptance MUST NOT be read as BoostX's. The Go SDK keeps `tokens.GamePass`,
`tokens.ExtractGamePassClaims` and `tokens.ParseGamePassToken` (single key) for tests, marked deprecated, with the
sentinel `tokens.ErrInvalidGamePass`; they verify the signatures and read the claims' types, not BoostX's gamepass
rules. Applies [P-optional-surface](#p-optional-surface).

Implementation-defined: which gamepass claims such a parser checks. (No vector: outside conformance.)

## 8. Inbound Booster and CheckBet (INBOUND)

BoostX sends a partner two tokens it signs itself: the BoosterJWT to `/set-boost` after each round, and the CheckBetJWT
to `/check-bet` before each round and at each game open. Both are compact ES256 JWTs signed with the BoostX private key
held for that partner, and both carry the signed GID of the gamepass that created the game. This section defines how an
SDK reads the partner id from such a token before it has any key (extraction) and how it verifies the token and its GID
(parsing). For SDK behaviour this section is the authority; the partner docs describe the same tokens for people
(Rounds; Integration details, Request pipeline). The JWS and JSON mechanics shared with the other inbound tokens are
written once in 5.4 and 5.5, and the signed GID in section 6; this section links them and states how they apply here.

**Surface used in this section.** Required status is in 3.1 and the result shapes in 3.3.

| Neutral name | JS | Go |
|--------------|----|----|
| Booster extractor | `extractBoosterPartner(boosterJWT): string` | `tokens.ExtractBoosterPartner(token) (string, error)` |
| Booster parser | `parseBoosterToken(boosterJWT, boostxPublicKey, partnerPublicKeys): Promise<Booster>` | `tokens.ParseBoosterTokenWithKeys(token, boostxPub, partnerPubs) (*Booster, error)` |
| CheckBet extractor | `extractCheckBetPartner(checkBetJWT): string` | `tokens.ExtractCheckBetPartner(token) (string, error)` |
| CheckBet parser | `parseCheckBetToken(checkBetJWT, boostxPublicKey, partnerPublicKeys): Promise<CheckBet>` | `tokens.ParseCheckBetTokenWithKeys(token, boostxPub, partnerPubs) (*CheckBet, error)` |

All four are required. A parser takes the BoostX public key and a list of partner public keys. A single-key form (Go
`tokens.ParseBoosterToken` and `tokens.ParseCheckBetToken`; JS accepts one key where the list goes) is optional and,
where offered, MUST behave exactly as the list form given a one-element list.

Implementation-defined: whether the parsers are synchronous or asynchronous; the extractors need no key and no I/O.

| Result | Neutral field | JS | Go |
|--------|---------------|----|----|
| Booster | `gid` | `gid: GID` | embedded `GID` (`Partner`, `User`, `Bet`, `Signature`) |
| | `round` | `round: number` | `Round int` |
| | `boost` | `boost: number` | `Boost float64` |
| | `final`, `jackpot` | `final: boolean`, `jackpot: boolean` | `Final bool`, `Jackpot bool` |
| | `iat` | `iat: number` | `IssuedAt int64` |
| CheckBet | `gid`, `iat` | `gid: GID`, `iat: number` | embedded `GID`, `IssuedAt int64` |

**Conventions of this section.** `invalid_<token>` is `invalid_booster` for a BoosterJWT and `invalid_checkbet` for a
CheckBetJWT. A *malformed token* is an error whose cause chain carries `invalid_<token>` and no other category. "Field"
is the claim an error names, read as 4.5 describes (`missing required claim: <field>`, `invalid claim value: <field>`).
An error's categories are written as a set, as the vectors compare them (FORMAT.md section 5.1).

**Principles applied** (section 2): [P-names](#p-names) (exact member names), [P-duplicates](#p-duplicates) (last
occurrence wins), [P-one-value](#p-one-value), [P-utf8](#p-utf8), [P-surrogates](#p-surrogates) (ill-formed Unicode,
decision [lone-surrogate ids](#decision-lone-surrogates)), [P-base64url](#p-base64url),
[P-signature-vs-shape](#p-signature-vs-shape), [P-integers](#p-integers), [P-null-absent](#p-null-absent),
[P-check-order](#p-check-order), [P-extraction](#p-extraction), [P-key-usability](#p-key-usability),
[P-taxonomy](#p-taxonomy), [P-http-errors](#p-http-errors), [P-exp-nbf](#p-exp-nbf), [P-iat-exposed](#p-iat-exposed),
[P-body](#p-body).

### 8.1 Transport and framing

<a id="inbound-01"></a>**INBOUND-01. Request body.** BoostX sends `POST` with a JSON body `{"boosterJWT": "<token>"}` to
`/set-boost` and `{"checkbetJWT": "<token>"}` to `/check-bet`. A handler MUST take the token from the member named
exactly `boosterJWT` or `checkbetJWT` ([P-names](#p-names); a repeated name resolves by
[P-duplicates](#p-duplicates)). A body that is JSON `null`, or a token member that is absent or `null`, MUST read as the
empty token, which extraction then refuses (400 `{"error":"invalid booster token"}` or
`{"error":"invalid checkbet token"}`, INBOUND-47). A body that is any other non-object JSON value, or a token member that
is present but neither a string nor `null`, MUST be answered 400 `{"error":"invalid request body"}` before extraction.
The request `Content-Type` is not checked ([HTTP-06](#http-06)). The body cap and the byte and JSON rules of the body
are [P-body](#p-body) and 11.2. (Vectors: `inbound.json`.)

<a id="inbound-02"></a>**INBOUND-02. Compact serialization, three segments.** A token MUST be split on every `.` into
exactly three segments. Any other count (the empty string, one, two, four or more segments) is a malformed token, at
extraction and at parse. The JWS JSON serialization is not accepted. The general rule is [KEYS-28](#keys-28).
(Vectors: `inbound.json`.)

<a id="inbound-06"></a>**INBOUND-06. JWS signature.** A parser MUST verify the token with ES256 (ECDSA P-256 with
SHA-256) and the BoostX public key it was given, over the octets of `<header segment>.<payload segment>` exactly as
received, which are ASCII for base64url segments and otherwise the text's UTF-8 octets, with the signature segment
decoded to the 64-byte `r || s` ([KEYS-29](#keys-29)). A signature that does not verify is
`{invalid_<token>, invalid_signature}`. (Vectors: `inbound.json`.)

<a id="inbound-07"></a>**INBOUND-07. The signature text is not an identity.** A parser MUST accept a high-S signature as
well as a low-S one and MUST NOT normalise either ([KEYS-30](#keys-30)), so one payload can arrive under several valid
signature texts, and BoostX re-signs a replayed round with a fresh `iat` (INBOUND-50). An SDK MUST NOT deduplicate
rounds, or key any state, on the token text, the signature text or `iat`. A partner deduplicates on (`gid.partner`,
`gid.user`, `gid.bet`, `round`), as the bet store contract says (INBOUND-51). (Vectors: `inbound.json`, for a high-S GID
signature; a high-S token signature is pinned under [KEYS-30](#keys-30).)

<a id="inbound-08"></a>**INBOUND-08. Signature before payload.** A parser decodes and checks the header, then the
signature, and decodes the payload only after the signature has verified (order in INBOUND-32), so a malformed payload
under a bad signature is reported as `{invalid_<token>, invalid_signature}`. Extraction reads the payload only and
never the header or the signature segment ([KEYS-27](#keys-27)). (Vectors: `inbound.json`.)

<a id="inbound-09"></a>**INBOUND-09. The payload is one JSON object.** The decoded payload MUST be exactly one JSON value
that is an object, optionally surrounded by JSON whitespace ([P-one-value](#p-one-value), [KEYS-32](#keys-32)).
Trailing data after it, an array, a scalar or `null` is a malformed token, at extraction and at parse.
(Vectors: `inbound.json`.)

Written elsewhere, and how they apply to these two tokens:

| Id | Written as | Here |
|----|------------|------|
| INBOUND-03 | [KEYS-26](#keys-26) | All three segments are canonical unpadded base64url ([P-base64url](#p-base64url)). A header or payload segment that is not is a malformed token; a signature segment that is not is `{invalid_<token>, invalid_signature}`. |
| INBOUND-04 | [KEYS-23](#keys-23) | Of the header only `alg` and `crit` are read. A `crit` member, whatever its value, is `{invalid_<token>, invalid_signature}`; every other header member is ignored whatever its JSON type. |
| INBOUND-05 | [KEYS-22](#keys-22) | The header is one JSON object (else malformed), and `alg` is matched by exact name, so `"ALG"` is not `alg`. |
| INBOUND-55 | [KEYS-22](#keys-22) | Any `alg` other than the JSON string `"ES256"` (absent, `null`, a number, a boolean, an object, an array, another string) is `{invalid_<token>, invalid_signature}` ([P-signature-vs-shape](#p-signature-vs-shape)). |
| INBOUND-10, INBOUND-11 | [KEYS-35](#keys-35) | The header and payload bytes are strict UTF-8 and do not start with EF BB BF ([P-utf8](#p-utf8)); otherwise the token is malformed. |
| INBOUND-56 | [KEYS-31](#keys-31) | A signature segment that is not canonical base64url, or not 64 bytes, is `{invalid_<token>, invalid_signature}`, like one that does not verify. |

### 8.2 Root claim, names, duplicates, unknown members

<a id="inbound-12"></a>**INBOUND-12. The root claim.** A BoosterJWT payload MUST carry a member named exactly `booster`,
and a CheckBetJWT payload one named exactly `checkbet`; this root object holds `gid` and the token's own fields. An
absent root is `{invalid_<token>, missing_claim}` naming the root (field `booster` or `checkbet`). A token of one flow
given to the other flow's extractor or parser is therefore refused, and cannot be replayed into the other endpoint.
(Vectors: `inbound.json`.)

<a id="inbound-13"></a>**INBOUND-13. A root that is not an object.** A root member that is present with any value other
than a JSON object (`null`, an array, a string, a number, a boolean) is `{invalid_<token>, invalid_claim}` naming the
root ([P-one-value](#p-one-value), [P-null-absent](#p-null-absent)). (Vectors: `inbound.json`, `http.json`.)

<a id="inbound-16"></a>**INBOUND-16. Unknown members are ignored.** A member this section does not name is ignored, at
the payload's top level, in the root object and in `gid`, whatever its JSON value; the only top-level members read
besides the root are `iat`, `exp` and `nbf` (8.7). An ignored member never supplies or overrides a named one
([P-names](#p-names)). The byte, surrogate and JSON-syntax rules still apply to its text, so an unknown member holding a
lone-surrogate escape still makes the token malformed. The result carries only the fields of the tables above, and its
GID only `partner`, `user`, `bet` and `signature`. (Vectors: `inbound.json`.)

| Id | Written as | Here |
|----|------------|------|
| INBOUND-14 | [KEYS-34](#keys-34) | Member names are matched exactly at every level: header, payload, root and `gid`. `"Booster"`, `"GID"`, `"ROUND"`, `"IAT"` or `"Partner"` is an unknown member, so a root spelled `"Booster"` leaves `booster` absent. |
| INBOUND-15 | [KEYS-33](#keys-33) | A repeated name takes its last occurrence, whole: a later `null` is `null` (so a later `"round": null` is `invalid_claim`), and two `booster` or `gid` objects are never merged. |

### 8.3 The gid

<a id="inbound-18"></a>**INBOUND-18. Empty partner id.** A `gid` whose `partner` is the empty string is
`{invalid_<token>, missing_claim}` with field `gid.partner`, at extraction and at parse. It is checked after the `gid`
shape ([GID-27](#gid-27)), and no key lookup happens for it. (Vectors: `inbound.json`.)

<a id="inbound-19"></a>**INBOUND-19. Empty user and bet ids are accepted.** An inbound `gid.user` or `gid.bet` that is
the empty string passes the shape check, and the GID signature is verified over the empty value. The builders are
stricter ([GAMEPASS-07](#gamepass-07), [GID-35](#gid-35)); the inbound side accepts any GID whose signature verifies.
(Vectors: `inbound.json`.)

<a id="inbound-20"></a>**INBOUND-20. Ids as received.** The four `gid` strings MUST be used exactly as decoded from JSON,
code unit for code unit: no trimming, case folding or Unicode normalisation, in the key lookup, in the canonical bytes
or in the result. The partner id handed to the key store is `gid.partner` as decoded, and a key store matches it
exactly ([KEYS-48](#keys-48)). (Vectors: `inbound.json`.)

<a id="inbound-25"></a>**INBOUND-25. GID signature form.** `gid.signature` MUST match `^[A-Za-z0-9_-]{85}[AQgw]$` as a
whole string, which is exactly the canonical unpadded base64url text of 64 bytes ([P-base64url](#p-base64url)). The form
is checked after every claim check and before any partner key is tried (INBOUND-32 step 4.1). `=` padding, the `+` `/`
alphabet, whitespace or a line break, another length, non-zero unused bits in the last character, and the empty string
all fail it, with the categories of [KEYS-47](#keys-47): `{invalid_<token>, invalid_gid, invalid_signature}` (decision
[canonical GID signatures](#decision-canonical-gid-signatures)). A generated SDK MUST anchor the match at the very end
of the text: in a regular-expression dialect where `$` also matches before a final line break (Python `re`, PCRE, Java),
use the end-of-text anchor (`\Z` in Python, `\z` in PCRE and Java) or a full-match function, or the signature
`"<86 characters>\n"` passes. (Vectors: `inbound.json`.)

<a id="inbound-27"></a>**INBOUND-27. What the GID signature covers.** The GID signature MUST be verified with ECDSA P-256
and SHA-256, as a 64-byte `r || s`, over the UTF-8 bytes of the canonical GID payload rebuilt from the decoded
`partner`, `user` and `bet` ([GID-02](#gid-02), [GID-03](#gid-03)): `{"partner":…,"user":…,"bet":…}` in that order, no
whitespace, each string escaped exactly as `JSON.stringify` escapes it (`/`, `<`, `>`, `&`, U+007F, U+2028, U+2029 and
all non-ASCII literal). A parser MUST NOT re-serialise the received `gid` object or reuse its text, which carries
`signature` and the sender's member order and escapes. (Vectors: `inbound.json`; the canonical bytes themselves are
pinned by the GID canonical vectors, section 12.)

<a id="inbound-53"></a>**INBOUND-53. The gid is the creating gamepass's, for the game's life.** The `gid` in every
BoosterJWT and CheckBetJWT is the signed GID of the gamepass that created the game, echoed unchanged, signature
included, for the game's whole life. After a partner key rotation it still verifies only under the key that signed it.
A parser therefore MUST verify it against every listed partner key (INBOUND-29), never the current key alone, and a
handler MUST hand the verified GID unchanged to the bet store ([GID-41](#gid-41)). (No vector: the SDK behaviour is
pinned under INBOUND-29.)

<a id="inbound-61"></a>**INBOUND-61. The extracted id is the verified id.** In a handler, the `gid.partner` of the
verified token MUST equal the partner id the keys were looked up for. An SDK meets this by construction when extraction
and parsing read the same payload bytes through the same JSON reader, as this section requires
([P-names](#p-names), [P-duplicates](#p-duplicates)). An SDK whose extraction uses a different reader from its parser
MUST compare the two ids after parsing and refuse a mismatch as a malformed token (answered 400 as INBOUND-47 says).
(Vectors: `inbound.json`, through the repeated-`gid` cases; otherwise it holds by construction in a conforming SDK.)

| Id | Written as | Here |
|----|------------|------|
| INBOUND-17 | [GID-27](#gid-27) | An absent `gid` is `missing_claim` (field `gid`). A `gid` that is not a JSON object, or whose `partner`, `user`, `bet` or `signature` is absent, `null` or not a JSON string, is `invalid_gid`. Then an empty `partner` is `missing_claim` (field `gid.partner`). All inside `invalid_<token>`, run with the claims at extraction and at parse, before the GID signature is examined; other `gid` members are ignored. |
| INBOUND-26 | [KEYS-47](#keys-47) | A `gid.signature` not in the canonical form is `{invalid_<token>, invalid_gid, invalid_signature}`, the same set as a well-formed one that no listed key verifies; the message may say which. |
| INBOUND-28 | [KEYS-37](#keys-37) | A header or payload whose JSON text holds a `\uD800`–`\uDFFF` escape that is not half of a high-then-low pair is a malformed token, at extraction (payload) and parse (header and payload), and is never verified as a GID ([P-surrogates](#p-surrogates), decision [lone-surrogate ids](#decision-lone-surrogates)). |

### 8.4 Keys and unverified extraction

<a id="inbound-22"></a>**INBOUND-22. Key lookup in a handler.** With the extracted id, a handler looks up the BoostX
public key and the partner public key list. A lookup that fails with `unknown_partner`, from either lookup, is answered
400 `{"error":"unknown partner \"<id>\""}`, with the id between double quotes and its inner escaping
implementation-defined ([KEYS-51](#keys-51)). Any other lookup failure is answered 500
`{"error":"failed to get boostx key"}` or `{"error":"failed to get partner key"}`. When both lookups fail, the BoostX
key's outcome decides the answer.

Implementation-defined: whether the two lookups run one after the other or concurrently ([KEYS-52](#keys-52)); the
decision rule does not vary. (Vectors: `inbound.json`.)

<a id="inbound-23"></a>**INBOUND-23. Unusable BoostX key.** A BoostX public key that is absent, or not usable
(INBOUND-60), is `{invalid_public_key}` alone, never wrapped in the token category, raised before the token is read. A
handler answers it 500 `{"error":"failed to verify token"}`. (Vectors: `inbound.json`.)

<a id="inbound-24"></a>**INBOUND-24. The GID is always verified.** A parser MUST verify the GID signature of every
BoosterJWT and CheckBetJWT and MUST NOT offer an option, flag or variant that skips it; a handler never calls the bet
store with an unverified GID ([HTTP-20](#http-20)). A hand-written integration can leave GID verification out; an SDK
makes that choice for its user. (No vector: the absence of an option is not observable through the API.)

<a id="inbound-29"></a>**INBOUND-29. Any listed partner key.** The GID passes when any usable key in the partner key
list verifies it, whatever its position. Unusable entries are skipped, and the order carries no meaning (by convention
the current key comes first). (Vectors: `inbound.json`.)

<a id="inbound-30"></a>**INBOUND-30. Empty partner key list.** An empty or absent partner key list is
`{invalid_public_key}` alone, raised before the token is read; a handler answers it 500
`{"error":"failed to verify token"}`. (Vectors: `inbound.json`.)

<a id="inbound-59"></a>**INBOUND-59. The BoostX key first.** Of the two key configuration checks, the BoostX key is
checked first and the partner key list second; when both fail, the BoostX key's failure is reported
([P-check-order](#p-check-order)). (Vectors: `keys.json`, `gidgp.json`, `inbound.json`, `http.json`, by category
only: both failures are `invalid_public_key`, so only the message tells them apart.)

<a id="inbound-60"></a>**INBOUND-60. A usable public key.** A key is usable for these tokens when the platform can verify
an ES256 signature with it: an ECDSA public key on P-256 whose point is present, on the curve, with coordinates in range
and not the point at infinity, and which the platform permits for verifying ([P-key-usability](#p-key-usability),
[KEYS-63](#keys-63)). In Web Crypto that is algorithm `ECDSA`, `namedCurve` `P-256`, `type` `"public"` and `usages`
including `"verify"`; in Go, curve P-256 with both coordinates present and a point that converts to a `crypto/ecdh` key.
Usability is judged before the token is read (INBOUND-32 step 1). A verification that fails at run time for any reason
other than a signature that does not verify counts as unusability: for the BoostX key it is `{invalid_public_key}`
alone; for a partner key that key is skipped, and `{invalid_public_key}` results only when no listed key returned a
verdict, while a "does not verify" from any usable key makes the GID fail as INBOUND-46 says. (Vectors:
`inbound.json`, `http.json`, for the portable cases of KEYS-63; usability beyond them depends on the platform's key
model.)

| Id | Written as | Here |
|----|------------|------|
| INBOUND-21 | [KEYS-49](#keys-49) | Extraction splits the token into three segments, decodes the payload under the payload rules, runs the same claim routine as parsing (INBOUND-32 step 3, including `iat`, `exp` and `nbf`) and returns `gid.partner`. It never reads the header or the signature segment, consults no key and trusts nothing; a failure carries the categories parsing would report ([P-extraction](#p-extraction)). |
| INBOUND-31 | [KEYS-46](#keys-46) | The key configuration is checked before the token is read, so an unusable BoostX key or partner key list is `{invalid_public_key}` (500) whatever else is wrong with the token. |

### 8.5 Normative check order

<a id="inbound-32"></a>**INBOUND-32. Check order of the Booster and CheckBet parsers.** A parser MUST run these checks in
this order and report the first that fails ([P-check-order](#p-check-order)). Every failure except those of step 1 and
the run-time key failure of steps 2.6 and 4.2 is wrapped in `invalid_<token>`. The step numbers are stable.

1. **Key configuration.**
   1. The BoostX public key is usable (INBOUND-60), else `{invalid_public_key}`.
   2. The partner key list holds at least one usable key, else `{invalid_public_key}` (INBOUND-30, INBOUND-59).
2. **JWS** (the general order is [KEYS-67](#keys-67)).
   1. Exactly three segments (INBOUND-02), else malformed.
   2. The header segment is canonical base64url, its bytes are strict UTF-8 with no byte order mark, they form one JSON
      value that is an object, and the text holds no lone-surrogate escape; else malformed. These sub-checks share one
      category, so their relative order is not observable, and any order meets this step (decoding comes first, since
      the others read its output).
   3. `alg` is the JSON string `"ES256"`, else `{invalid_<token>, invalid_signature}`.
   4. The header has no `crit` member, else `{invalid_<token>, invalid_signature}`.
   5. The signature segment is canonical base64url of exactly 64 bytes, else `{invalid_<token>, invalid_signature}`.
   6. ES256 verification with the BoostX key over `<header segment>.<payload segment>` as received succeeds, else
      `{invalid_<token>, invalid_signature}`; a run-time failure of the platform's verify operation is
      `{invalid_public_key}` alone (INBOUND-60).
   7. The payload segment passes the same sub-checks as the header in 2.2, else malformed.
3. **Claims.** This step is the claim routine extraction also runs ([KEYS-49](#keys-49)).
   1. The root (`booster` or `checkbet`) is present, else `missing_claim` (field: the root); it is a JSON object, else
      `invalid_claim` (field: the root).
   2. `gid` is present in the root, else `missing_claim` (field `gid`); it is an object whose `partner`, `user`, `bet`
      and `signature` are all JSON strings, else `invalid_gid`; `partner` is not empty, else `missing_claim` (field
      `gid.partner`).
   3. Booster only, in this order: `round`, `boost`, `final`, `jackpot`, each first for presence (`missing_claim`) and
      then for its value (`invalid_claim`), as 8.6 defines. A CheckBet has no fields of its own.
   4. `iat` is present at the top level, else `missing_claim` (field `iat`); it is an integer by value, else
      `invalid_claim` (field `iat`) ([KEYS-39](#keys-39)).
   5. `exp`, when present, is a JSON number greater than now, else `invalid_claim` (field `exp`) (INBOUND-43).
   6. `nbf`, when present, is a JSON number not greater than now, else `invalid_claim` (field `nbf`) (INBOUND-43).
4. **GID.**
   1. `gid.signature` is in the canonical form (INBOUND-25), else `{invalid_<token>, invalid_gid, invalid_signature}`.
   2. A usable listed partner key verifies the GID signature over the canonical bytes (INBOUND-27, INBOUND-29), else
      `{invalid_<token>, invalid_gid, invalid_signature}`; when no listed key returned a verdict, `{invalid_public_key}`
      alone (INBOUND-60).

Extraction runs steps 2.1, 2.7 and 3, in that order, and nothing else: no key, no header, no signature segment, no GID
verification. The claim checks of step 3 come before the GID because they reveal nothing about the partner keys, and
because extraction and parsing then share one claim routine; a token that fails a claim check and would also fail GID
verification is reported as the claim failure. (Vectors: `inbound.json`, `keys.json`, `gidgp.json`.)

### 8.6 Booster claims

These rules give the fields of the `booster` root, checked in the order of INBOUND-32 step 3.3. [HTTP-23](#http-23) is
the same set of rules as a handler answers them (400 `{"error":"invalid booster token"}`, nothing reaches the store).

<a id="inbound-33"></a>**INBOUND-33. `round` is required.** An absent `booster.round` is `{invalid_booster,
missing_claim}` with field `round`. A `round` that is present but not a JSON number (`null`, a string, a boolean, an
object, an array) is `{invalid_booster, invalid_claim}` with field `round` ([P-null-absent](#p-null-absent)). No default
is ever substituted. (Vectors: `inbound.json`, `http.json`.)

<a id="inbound-34"></a>**INBOUND-34. `round` range.** `booster.round` MUST be an integer in [1, 2^53−1], judged by value
(INBOUND-35); `0`, `-0`, a negative value, a fraction, or a value above 2^53−1 is `{invalid_booster, invalid_claim}`
with field `round`.

Implementation-defined: an SDK whose result type for `round` is narrower than 2^53−1 (Go `int` on a 32-bit platform) MAY
also refuse a `round` above that type's maximum with the same categories, and documents it; BoostX never comes near
either bound. (Vectors: `inbound.json`, `http.json`.)

<a id="inbound-35"></a><a id="verifykeys-35"></a><a id="verifykeys-43"></a>**INBOUND-35. Integer
claims are judged by value.** Every integer claim of every inbound token follows [P-integers](#p-integers): it MUST be a
JSON number; its text is converted to the nearest IEEE 754 binary64 value (round to nearest, ties to even, as the
platform's standard decimal conversion does); and it is valid when that value is integral, its magnitude is at most
2^53−1, and it lies in the claim's own range. So `3`, `3.0` and `3e0` are the same value. A text beyond the binary64
range becomes plus or minus Infinity, and one that underflows becomes `0` or `-0`, and is judged as that value (so `iat`
`1e-400` is `0` and valid, while `round` `1e-400` is refused). Strings, booleans and `null` are never numbers; a numeric
string such as `"3"` is not a number.

| Claim | Token | Range | A fault is |
|-------|-------|-------|------------|
| `round` | Booster | [1, 2^53−1] | `invalid_claim` (INBOUND-34) |
| `iat` | Booster, CheckBet | magnitude at most 2^53−1 | `invalid_claim` ([KEYS-39](#keys-39)) |
| `iat` | verify-keys request and response | magnitude at most 2^53−1 | reason `shape`; an integral value outside now ± window is `stale` |
| `nonce` | verify-keys request and response | [1, 2147483647] | reason `nonce-format` ([VERIFYKEYS-42](#verifykeys-42)) |

On verify-keys an absent or `null` `iat` reads as `0` and fails as `stale`, and every nonce fault (absent, `null`, not a
number, not integral, out of range) is `nonce-format`; the order of the verify-keys checks is
[VERIFYKEYS-46](#verifykeys-46). Also covers: VERIFYKEYS-35, VERIFYKEYS-43, HTTP-40. (Vectors: `inbound.json`,
`verifykeys.json`, `http.json`.)

<a id="inbound-36"></a>**INBOUND-36. `boost` is required, and never defaulted.** An absent `booster.boost` is
`{invalid_booster, missing_claim}` with field `boost`. A `boost` that is present but not a JSON number, `null` included,
is `{invalid_booster, invalid_claim}` with field `boost` ([P-null-absent](#p-null-absent)). An SDK MUST NOT substitute
any value for an absent or `null` boost: a boost of `0` handed to a bet store turns into a wrong amount of money. BoostX
never sends a boost that is not finite and greater than 0 (8.9). (Vectors: `inbound.json`, `http.json`.)

<a id="inbound-37"></a>**INBOUND-37. `boost` range.** `booster.boost`, converted to the nearest binary64 (INBOUND-58), MUST
be finite and greater than 0. `0`, `-0`, a negative value, a text that underflows to `0` or `-0` (`1e-400`) and a text
that overflows to Infinity (`1e400`) are `{invalid_booster, invalid_claim}` with field `boost`. There is no upper bound
and no floor at 1: a boost below 1, exactly 1, or far above anything a regular round produces is valid.
(Vectors: `inbound.json`, `http.json`.)

<a id="inbound-38"></a>**INBOUND-38. `boost` is passed through, not interpreted.** `boost` is the round's accumulated
boost, a jackpot round's included. An SDK MUST return it as decoded and MUST NOT bound-check it beyond INBOUND-37,
derive a per-round factor from it, or compute X from it in the parser. Deriving X is the partner's, with the X helpers
of 7.6 ([GAMEPASS-38](#gamepass-38) onwards): `X = 1 + (xBase − 1) × boost`, floored. (Vectors: `inbound.json`.)

<a id="inbound-58"></a>**INBOUND-58. Decoding `boost`.** `boost` is decoded from its JSON number text to the nearest
IEEE 754 binary64 value and returned unrounded: `5e-324` is returned as the smallest subnormal and `1e308` as itself.
Underflow and overflow give the values INBOUND-37 refuses. (Vectors: `inbound.json`.)

<a id="inbound-39"></a>**INBOUND-39. `final` and `jackpot` are required JSON booleans.** They are checked in the order
`final`, then `jackpot`. An absent one is `{invalid_booster, missing_claim}` naming it. One that is present but not the
JSON literal `true` or `false` (`null`, `0`, `1`, `"true"`, `"false"`) is `{invalid_booster, invalid_claim}` naming it.
`null` is never read as `false` ([P-null-absent](#p-null-absent)). (Vectors: `inbound.json`, `http.json`.)

<a id="inbound-40"></a>**INBOUND-40. No combination checks.** An SDK MUST NOT refuse a Booster for its combination of
flags or for any relation between `round` and the flags: `jackpot: true` with `final: false`, for example, is accepted.
BoostX sends only (`final: false`, `jackpot: false`), (`final: true`, `jackpot: false`) and (`final: true`,
`jackpot: true`); interpreting the flags is the bet store's business. (Vectors: `inbound.json`.)

### 8.7 iat, exp and nbf

| Id | Written as | Here |
|----|------------|------|
| INBOUND-41 | [KEYS-39](#keys-39) | The top-level `iat` is required on both tokens: absent is `missing_claim` (field `iat`); not a JSON number, or not an integer of magnitude at most 2^53−1 by value (INBOUND-35), is `invalid_claim` (field `iat`). No sign, age or skew check applies. |
| INBOUND-42 | [KEYS-39](#keys-39) | A verified Booster and CheckBet carry `iat` as received, in integer Unix seconds (JS `iat`, Go `IssuedAt`). The SDK applies no age, future-skew or window check to them; an age check is the partner's choice and must allow for retries, which re-send the same token ([P-iat-exposed](#p-iat-exposed)). |

Implementation-defined: an `iat` written as `-0` is the integer 0; an SDK whose result type is a binary64 number may
return it as `-0` (the vectors compare numbers with `==`, FORMAT.md section 5.3).

<a id="inbound-43"></a>**INBOUND-43. `exp` and `nbf` are enforced when present; other registered claims are ignored.** On
a BoosterJWT and a CheckBetJWT, `exp` and `nbf` are optional top-level claims ([P-exp-nbf](#p-exp-nbf),
[KEYS-42](#keys-42)). Absent, they set no limit. Present, each MUST be a JSON number (not necessarily an integer), and
`null` or any other type is `{invalid_<token>, invalid_claim}` naming it. A token with `exp <= now` or `nbf > now` is
`{invalid_<token>, invalid_claim}` naming that claim, where now is the current time in whole Unix seconds (rounded
down) and no leeway applies; a value beyond the binary64 range compares as plus or minus Infinity. The checks run after
`iat`, `exp` before `nbf`, at extraction as at parse, so extraction depends on the clock. `iss`, `aud`, `sub`, `jti`
and every other top-level member are ignored on these tokens (INBOUND-16). BoostX never sends `exp` or `nbf` on them,
so the rule only ever meets hand-made tokens. (Vectors: `inbound.json`.)

### 8.8 Errors and answers

<a id="inbound-44"></a>**INBOUND-44. Everything but a key fault is in the token category.** Every refusal by a Booster
or CheckBet extractor or parser carries `invalid_<token>`, except a key configuration fault, which is
`{invalid_public_key}` alone and is never wrapped (INBOUND-23, INBOUND-30, INBOUND-60; [HTTP-56](#http-56)). A malformed
token carries nothing else; claim, GID and signature faults carry their cause as well (INBOUND-45, INBOUND-46). The
causes form a chain the language's standard check walks ([P-taxonomy](#p-taxonomy)). (Vectors: `inbound.json`.)

<a id="inbound-45"></a>**INBOUND-45. Claim failures carry their cause.** Every claim failure carries one of these causes
inside `invalid_<token>`, and none is reported without one:

| Fault | Categories | Field |
|-------|------------|-------|
| Root absent | `invalid_<token>`, `missing_claim` | `booster` or `checkbet` |
| Root not an object | `invalid_<token>`, `invalid_claim` | `booster` or `checkbet` |
| `gid` absent | `invalid_<token>`, `missing_claim` | `gid` |
| `gid` not an object of four strings | `invalid_<token>`, `invalid_gid` | none |
| `gid.partner` empty | `invalid_<token>`, `missing_claim` | `gid.partner` |
| `round`, `boost`, `final`, `jackpot` or `iat` absent | `invalid_<token>`, `missing_claim` | the claim |
| Any of those present with the wrong JSON type or out of range | `invalid_<token>`, `invalid_claim` | the claim |
| `exp` or `nbf` not a number, or in force against the token | `invalid_<token>`, `invalid_claim` | the claim |

(Vectors: `inbound.json`.)

<a id="inbound-46"></a>**INBOUND-46. A token signature failure and a GID failure differ.** A JWS signature fault
(INBOUND-32 steps 2.3 to 2.6) is `{invalid_<token>, invalid_signature}` and never carries `invalid_gid`. A GID fault,
of form or of verification (step 4), is `{invalid_<token>, invalid_gid, invalid_signature}`. The presence of
`invalid_gid` tells a partner whether the BoostX key or its own partner keys failed. (Vectors: `inbound.json`.)

<a id="inbound-47"></a>**INBOUND-47. Handler answers.** A handler answers any extraction failure, and any parse failure
that carries `invalid_<token>`, with 400 `{"error":"invalid booster token"}` on `/set-boost` or
`{"error":"invalid checkbet token"}` on `/check-bet`. It answers `invalid_public_key` with 500
`{"error":"failed to verify token"}`; INBOUND-44 leaves a parser no third kind of failure, so testing for either
category decides the answer. Those wordings are normative ([P-http-errors](#p-http-errors)). Nothing reaches the bet
store in either case. BoostX reads any non-2xx answer as a failed call: a refused `/set-boost` voids the round, and a
refused `/check-bet` before a round refuses that round (8.9). (Vectors: `inbound.json`.)

<a id="inbound-54"></a>**INBOUND-54. Size and depth.** The extractors and parsers impose no token size limit of their
own. The handlers cap the request body at 65536 bytes and answer a longer one 400 `{"error":"invalid request body"}`
([HTTP-07](#http-07)), which bounds every token that reaches them through a handler. An adapter given an
already-parsed body (JS `handleSetBoost`, `handleCheckBet`) applies no cap, which is then its caller's
([P-body](#p-body)). JSON nesting depth follows [P-one-value](#p-one-value): every SDK reads a payload nested 64
levels deep (decision [JSON nesting depth](#decision-json-depth)). BoostX's tokens nest three levels deep (payload,
root, `gid`). (Vectors: `inbound.json` for the depth floor; the body cap is pinned under HTTP-07 in `http.json`.)

| Id | Written as | Here |
|----|------------|------|
| INBOUND-57 | [KEYS-51](#keys-51) | An unserved partner id is answered 400 `{"error":"unknown partner \"<id>\""}`: status, shape and wording are normative, the id appears between double quotes, and only the escaping inside the id is implementation-defined ([P-http-errors](#p-http-errors)). |

### 8.9 Round semantics and what the SDK sees from BoostX (informative)

These rules describe what BoostX sends and how it reads the answers. They explain the rules above and the bet store
contract; apart from the SDK duty stated in INBOUND-51, they are not requirements on an SDK.

<a id="inbound-48"></a>**INBOUND-48. Round numbering.** `round` counts committed rounds from the partner's view. A
regular round is the number of committed regular rounds plus 1. A jackpot round is the triggering regular round `N` plus
1, sent right after `N`, which is committed first; no round `N + 2` follows. (Informative.)

<a id="inbound-49"></a>**INBOUND-49. `final`.** `final: true` marks the last round: a regular round whose floored X, on
the `xBase` of the entry during which it was first sent, is outside `[xrange.min, xrange.max]`, or a jackpot round. Once
a final round is committed no further round is played, but an unacknowledged final round is sent again, under the same
round number and with the same boost, a jackpot one included, and keeps its `xBase` ([GAMEPASS-44](#gamepass-44)).
(Informative.)

<a id="inbound-50"></a>**INBOUND-50. One round can arrive more than once.** (a) After a network error or a 502, 503, 504
or 525, BoostX retries up to three times (after about 200, 500 and 1000 ms) with the identical token, `iat` included.
(b) A round the partner did not acknowledge is played again at the player's next spin after reopening, as a new token
with the same `gid`, `round`, `boost` and `final` and a fresh `iat`. (c) A failed jackpot round is re-sent under the
same `round` `N + 1`, still `jackpot: true, final: true`, with the same boost, and regular round `N` is not re-sent.
BoostX fixes a jackpot round's `xBase` and boost before it first sends the round, so a later gamepass's `x` does not
recalculate them. (d) Concurrent requests can deliver one round twice, and a delayed copy of an older round can arrive
after a newer one. Hence INBOUND-07, the absence of an age check (INBOUND-42) and the replay rule of INBOUND-51.
(Informative.)

<a id="inbound-51"></a>**INBOUND-51. Every verified round reaches the bet store.** A handler MUST hand every verified
Booster to the bet store, replays and late rounds included: an SDK neither filters replays nor tracks rounds
([HTTP-29](#http-29)). It answers 200 `{"result":{"ok":true}}` when the store returns normally ([HTTP-19](#http-19)),
400 `{"error":"round rejected"}` when the store signals the round-rejected error (JS `RoundRejectedError`, Go
`handlers.ErrRoundRejected`) anywhere in the cause chain, and 500 `{"error":"failed to set boost"}` for any other store
error ([HTTP-27](#http-27)). The store, which is partner code, applies a round only when it is greater than the stored
one, returns normally for any other, and signals the round-rejected error, without writing, for a round it will not
apply. BoostX records a round only on 200 with `result.ok` the JSON boolean `true`.
(Vectors: `inbound.json` for the handler answers.)

<a id="inbound-52"></a>**INBOUND-52. CheckBet.** A CheckBetJWT carries only `iat` and `checkbet.gid`. BoostX sends it
only when the partner's `/check-bet` switch is on, whenever a game opens and before every round. Before a round, the
verdict `false` refuses the round, and so does any answer that gives no verdict ([HTTP-50](#http-50)); a handler
therefore answers a store verdict that is not a boolean 500 rather than pass it on (11.6). (Informative.)

**What BoostX sends.**

- Both tokens have the protected header exactly `{"alg":"ES256"}` and the payload `{"checkbet":{"gid":…},"iat":…}` or
  `{"booster":{"gid":…,"round":…,"boost":…,"final":…,"jackpot":…},"iat":…}`, with `iat` in integer seconds and no
  `exp`, `nbf`, `iss` or `aud`. Their segments are canonical unpadded base64url and the signature a 64-byte `r || s`.
- The `gid` is the creating gamepass's signed GID, exactly its four members, echoed for the game's life. BoostX refuses
  a gamepass whose ids are not well-formed Unicode when the game opens (decision [lone-surrogate
  ids](#decision-lone-surrogates)), so a lone surrogate never reaches these tokens. It also refuses a gamepass whose ids
  contain `:` or are longer than their limits ([GID-09](#gid-09), [GID-10](#gid-10); decision [ids hold no `:` and have
  bounded lengths](#decision-gid-id-rules)), so such ids reach these tokens only from a game opened before that rule.
- `boost` is always finite and greater than 0: BoostX never signs a Booster whose boost is not, which keeps JSON `null`
  off the wire (decision [minimum stake 0.01](#decision-minimum-stake)).
- The calls are `POST` with `Content-Type: application/json` and the body `{"checkbetJWT": …}` or
  `{"boosterJWT": …}`. One token is built per call and re-sent unchanged on each retry. BoostX reads no body of a
  non-2xx answer.

## 9. Settlement (SETTLE)

A settlement travels one way, partner to BoostX. The SDK builds a SettlementJWT from a flat parameter set and, through
its settlement client, posts it to BoostX in one attempt and classifies the answer. No SDK parses a SettlementJWT
(SETTLE-67). This section is the authority for SDK behaviour: what an SDK checks, in which order, with which error
category, and how the client reads BoostX's answer. The partner docs describe the same token and endpoint for people
(Settlement).

| Operation | Neutral name | JS | Go |
|-----------|--------------|----|----|
| Build a token | `createSettlementToken` | `createSettlementToken(privateKey, params): Promise<string>` | `tokens.CreateSettlementToken(privateKey, params) (string, error)` |
| Construct the client | `newClient` | `new BoostxClient(keyStore, options?)` | `client.New(ks, opts...)` |
| Submit one settlement | `submitSettlement` | `client.submitSettlement(params, { signal }?): Promise<void>` | `(*client.Client).SubmitSettlement(ctx, params) error` |

### 9.1 Token

<a id="settle-01"></a>**SETTLE-01. Compact JWS, ES256, fixed header.** A SettlementJWT MUST be a compact JWS signed
ES256 with the partner private key the builder is given. Its header MUST carry exactly the members `alg` `"ES256"` and
`typ` `"JWT"`, in any order, and no `kid` ([KEYS-20](#keys-20)); the three segments are canonical unpadded base64url
and the signature is the raw 64-byte `r || s` ([KEYS-25](#keys-25), [KEYS-29](#keys-29)). BoostX verifies ES256 only
and never reads `typ`. (Vectors: settle.json; every accepted builder result is checked for the header, the segments
and the signature.)

<a id="settle-02"></a>**SETTLE-02. Root claims.** The payload MUST be a JSON object whose only members are `iat` and
`settlement`. The SDK MUST NOT emit `exp`, `nbf`, `iss`, `aud`, `sub`, `jti` or any other root member. The order of the
two members is free ([P-emitted-bytes](#p-emitted-bytes), [KEYS-61](#keys-61)). (Vectors: settle.json.)

<a id="settle-03"></a>**SETTLE-03. iat.** `iat` MUST be present and MUST be the signing time in whole Unix seconds (the
current time floored to a second), written as an integer JSON number ([KEYS-38](#keys-38)). The SDK applies no age rule
to it, and BoostX applies no age window to it ([SETTLE-66](#settle-66)). (Vectors: settle.json, through the clock rule
of FORMAT.md section 3.1.)

<a id="settle-04"></a>**SETTLE-04. No exp or nbf.** The SDK MUST NOT emit `exp` or `nbf` (SETTLE-02). The reason is on
BoostX's side: BoostX enforces an `exp` or `nbf` it finds against its own clock, with no tolerance. (Vectors:
settle.json, by the root-member check of SETTLE-02.)

<a id="settle-05"></a>**SETTLE-05. The settlement object.** `settlement` MUST be a JSON object with exactly these
members: `gid` (`{partner, user, bet, signature}`, all strings), `status`, `payout` (`{amount, currency}`), `version`,
`xSettle` when given (SETTLE-27), and `settledAt`. Member order is free ([KEYS-61](#keys-61)); both SDKs write the order
listed. Members of the parameter set other than the nine of section 9.2 MUST be ignored and MUST NOT reach the token (a
statically typed parameter struct cannot carry any); the one exception is the neutral spelling of a member the SDK
spells otherwise, which [GAMEPASS-50](#gamepass-50) lets it refuse instead. (Vectors: settle.json, `payload` and
`absent`.)

<a id="settle-06"></a>**SETTLE-06. No demo flag.** A settlement MUST NOT carry a demo flag, and the parameter set has
none. BoostX determines a settlement's demo value itself. (Vectors: settle.json, `absent`.)

<a id="settle-07"></a>**SETTLE-07. Partner identity.** The token names its partner only through `gid.partner`, which
MUST be the `partner` parameter exactly as given (SETTLE-73). The SDK has no other identity field and sends no
authentication header (SETTLE-42). A settlement for an id BoostX does not know is answered 404
`{"status":404,"error":"not found"}`: BoostX does not know this partner id, and the partner checks it
([SETTLE-75](#settle-75)). An SDK never sends an empty partner: the builder refuses it (SETTLE-10). (Vectors:
settle.json.)

<a id="settle-08"></a>**SETTLE-08. The GID is signed afresh.** Every token MUST carry a signed GID built from the
`partner`, `user` and `bet` parameters with the same private key that signs the token, at the time of the call. The
builder MUST NOT accept a precomputed or stored GID. The client signs with whatever key the store holds at that
attempt (SETTLE-59). BoostX verifies the GID against the one partner public key it holds now; there is no rotation
list on this path, unlike the SDK's own GID verification of inbound tokens. (Vectors: settle.json; every accepted
builder result's payload `gid` must verify with the signing key's public half.)

<a id="settle-09"></a>**SETTLE-09. GID canonical bytes and signature form.** The GID signature MUST be computed over
the canonical bytes of [GID-02](#gid-02) and [GID-03](#gid-03) and written as the 86-character canonical unpadded
base64url of [GID-14](#gid-14). BoostX answers 401 to a settlement whose `gid.signature` is not canonical. (Vectors:
settle.json, through the GID check on every accepted result; the canonical bytes themselves are pinned in the GID
group.)

<a id="settle-19"></a>**SETTLE-19. Number spelling.** The spelling of numbers in the payload is not canonical. A
negative zero MAY be written `0` or `-0`, and an integral value `150`, `150.0` or in exponent form, provided the text
parses to the specified binary64 value ([P-emitted-bytes](#p-emitted-bytes)). BoostX compares parsed values, so `-0`
and `0` are the same amount, version or `xSettle` there.

Implementation-defined: number spelling in the settlement payload, `-0` included. JS writes `0` for `-0`; Go writes
`-0` for `amount` and `xSettle`. (Vectors: settle.json compares numbers as binary64, so either spelling passes.)

<a id="settle-34"></a>**SETTLE-34. Payload bytes are not canonical.** Same rule as [KEYS-61](#keys-61) (duplicate
set KEYS-61, GID-38, SETTLE-34, HTTP-70), applied to the settlement: member order, string escaping (`<`, `>`, `&`,
U+2028, U+2029 included), number spelling and whitespace of the payload are implementation-defined, as long as it is
valid JSON carrying the specified values. Only the GID signing input has canonical bytes, and BoostX rebuilds those
from the parsed ids, so payload escaping never affects acceptance. (Vectors: settle.json compares parsed values only.)

### 9.2 Parameters

The builder takes the private key first and one parameter set. In a language that tells null from absence, null means
absent for every parameter ([P-null-absent](#p-null-absent)). A missing parameter set (absent, null, or not an
object) reads as an empty one, so the first failure after the key is `missing_claim` for `partner`
([GAMEPASS-48](#gamepass-48)); a language whose parameter set is a struct value cannot express it.

| Neutral | JS | Go `SettlementParams` | Wire | Required | Absent or null | Field named in the error |
|---------|----|-----------------------|------|----------|----------------|--------------------------|
| `partner` | `partner` | `Partner string` | `settlement.gid.partner` | yes | `missing_claim` | `partner` |
| `user` | `user` | `User string` | `settlement.gid.user` | yes | `missing_claim` | `user` |
| `bet` | `bet` | `Bet string` | `settlement.gid.bet` | yes | `missing_claim` | `bet` |
| `status` | `status` | `Status string` | `settlement.status` | yes | `invalid_claim` | `status` |
| `amount` | `amount` | `Amount float64` | `settlement.payout.amount` | yes | `invalid_claim` (Go: sent as 0) | `amount` |
| `currency` | `currency` | `Currency string` | `settlement.payout.currency` | yes | `missing_claim` | `currency` |
| `version` | `version` | `Version int64` | `settlement.version` | yes | `invalid_claim` (Go: sent as 0) | `version` |
| `xSettle` | `xSettle` | `XSettle *float64` | `settlement.xSettle` | no | left out of the token | `xsettle` |
| `settledAt` | `settledAt` | `SettledAt int64` | `settlement.settledAt` | yes | `missing_claim` | `settledAt` |

The last column is the field token the error message carries after `missing required claim: ` or
`invalid claim value: ` (section 4.5); conformance vectors read it. Note `xsettle`, in lower case, which both SDKs
write and which matches BoostX's `invalid-xsettle` code.

**What the values mean (informative).** These are the meanings an SDK's documentation of the parameter set draws on;
the SDK checks none of them beyond the rules below.

`status` is the bet's outcome as the partner settled it. BoostX attaches no arithmetic to any status: `amount`
(`payout.amount`) is always what actually reached the player, in major units of `currency`, and the status explains
why it relates to the stake as it does.

| `status` | The bet | `amount` |
|----------|---------|----------|
| `win` | won | what the player was paid |
| `lose` | lost | normally 0; a positive amount is still valid ([SETTLE-15](#settle-15)) |
| `half_win` | won on half of it | what the player was paid, already halved by the partner: BoostX applies no factor of 0.5 |
| `half_lose` | lost on half of it | what the player got back, already halved by the partner, likewise |
| `cancelled` | was cancelled | what reached the player |
| `refund` | was refunded | the amount refunded |
| `cashout` | was cashed out before it settled | the cash-out amount |
| `unsettled` | ended with no result | exactly 0 ([SETTLE-17](#settle-17)) |

`xSettle` is the partner's own base X in force at settlement, before the boost: the same quantity as the `xBase` a
partner passes to `playerX` ([GAMEPASS-44](#gamepass-44)), resolved to the one value the bet settled on. It is left
unset for a status with no settled base X, most commonly `cancelled`, `refund` and `unsettled`; unset and `null` mean
the same. Unlike the `x` of a gamepass, which BoostX bounds ([GAMEPASS-19](#gamepass-19)), it has no floor: any finite
value from 0 up is valid. A value below 1 means the partner's own coefficient settled below the stake, and 0 means the
player lost everything. The X the boost gives is the general form of [GAMEPASS-49](#gamepass-49), not `playerX`: above 1
it is `1 + (xSettle - 1) × boost`, floored as `floorX` floors with the bet's decimals; at 1 or below the boost has
nothing to act on, and that X is `xSettle` itself, whatever the boost.

`version` orders the settlements of one bet ([SETTLE-24](#settle-24)), `settledAt` is when the partner settled the
bet, not when BoostX receives the settlement, and `currency` is normally the gamepass's stake currency, unless the
payout really happened in another one.

<a id="settle-10"></a>**SETTLE-10. Ids are required strings.** Same rule as [GAMEPASS-07](#gamepass-07) (duplicate set
GAMEPASS-07, GID-35, SETTLE-10; [P-builder-ids](#p-builder-ids)), applied to the settlement. `partner`, `user` and `bet`
are checked in that order, each first for presence, then for type: absent, null or `""` is `missing_claim`; any other
non-string, a number included, is `invalid_claim` and is never converted to text. The builder refuses an empty id
because one is almost always a fault in the caller's code. (Vectors: settle.json.)

<a id="settle-11"></a>**SETTLE-11. Ids are well-formed Unicode.** An id that is not well-formed Unicode MUST be refused
with `invalid_claim` naming that id, before anything is signed ([P-surrogates](#p-surrogates), decision [lone-surrogate
ids](#decision-lone-surrogates)). In a language with UTF-16 strings that means an unpaired surrogate (JS
`isWellFormed()`); in a language with byte strings, invalid UTF-8 (Go `utf8.ValidString`). The check runs in step 12 of
SETTLE-31, after every other parameter check, on `partner`, `user` and `bet` in that order, each id ahead of its own `:`
and length checks. (Vectors: settle.json, with the `$illFormed` input of FORMAT.md section 4.)

<a id="settle-12"></a>**SETTLE-12. No `:`; whitespace is not checked.** The builder MUST refuse an id that contains
U+003A `:` with `invalid_claim` naming that id ([GID-10](#gid-10)), and MUST NOT refuse whitespace in any id. A
settlement is identified by its `partner`, `user`, `bet` and `version` as four separate values. (Vectors: settle.json.)

<a id="settle-13"></a>**SETTLE-13. Status set.** `status` MUST be exactly one of `win`, `lose`, `cancelled`, `refund`,
`half_win`, `half_lose`, `cashout`, `unsettled`: compared code unit for code unit, case-sensitive and untrimmed. Any
other value, a non-string included, is `invalid_claim` naming `status`. BoostX answers any other value 400
`invalid-status`. (Vectors: settle.json.)

<a id="settle-70"></a>**SETTLE-70. Status has no missing case.** An absent, null or empty `status` is `invalid_claim`,
never `missing_claim`, unlike the ids, `currency` and `settledAt`. A generated SDK must keep this asymmetry, since it
is easy to "fix". BoostX answers a missing status 400 `invalid-status`. (Vectors: settle.json.)

<a id="settle-15"></a>**SETTLE-15. No status arithmetic.** The builder MUST NOT relate `amount` to `status` except
through the `unsettled` rule (SETTLE-17): any amount `>= 0` is legal for every other status, a `lose` with a positive
payout included. BoostX attaches no arithmetic to statuses either (`half_win` and `half_lose` carry no factor).
(Vectors: settle.json.)

<a id="settle-16"></a>**SETTLE-16. Amount domain.** `amount` MUST be a finite number `>= 0`. NaN, plus or minus
infinity, a negative number and any non-number (a string, a JS `bigint`, a boolean) are `invalid_claim` naming
`amount`. BoostX answers 400 `invalid-payout` when `payout` is missing or not an object with a numeric, finite,
non-negative `amount`. (Vectors: settle.json.)

<a id="settle-17"></a>**SETTLE-17. Zero amounts and `unsettled`.** An amount of 0 is legal for every status. When
`status` is `unsettled`, `amount` MUST equal 0, compared as a number, so `-0` counts as 0; any other amount is
`invalid_claim` naming `amount`. BoostX applies the same rule (400 `invalid-payout`). (Vectors: settle.json.)

<a id="settle-18"></a>**SETTLE-18. Amount and version have no default.** `amount` and `version` are required and 0 is
a legal value for both ([P-zero](#p-zero)). Where the language can represent an absent value (undefined, null, None,
a missing key), an absent `amount` or `version` MUST be refused with `invalid_claim`. Where an unset field cannot be
told apart from 0 (Go struct zero values), the SDK sends 0, and its documentation MUST say so for both fields (Go
README, `SettlementParams` comments). BoostX answers a truly absent field 400 `invalid-payout` or `invalid-version`,
and accepts 0. (Vectors: settle.json, with `wantZeroValue` for the struct case.)

<a id="settle-20"></a>**SETTLE-20. Amount precision.** `amount` is in major units of `currency`. The SDK MUST NOT
round it, limit its decimals or convert it to minor units; it writes the binary64 value it was given. BoostX stores
the double as sent. (Vectors: settle.json.)

<a id="settle-21"></a>**SETTLE-21. Currency shape.** `currency` follows [P-currency](#p-currency): absent, null or
`""` is `missing_claim`; otherwise it MUST match `^[A-Z]{3,4}$` exactly (ASCII, case-sensitive, untrimmed, no
trailing newline), and anything else, a non-string included, is `invalid_claim` naming `currency`. No case mapping is
applied. BoostX answers a failing code 400 `invalid-currency`. (Vectors: settle.json.)

<a id="settle-22"></a>**SETTLE-22. Shape only.** The builder MUST NOT check `currency` against a list of served
currencies or against the game's stake currency. (Vectors: settle.json.)

<a id="settle-23"></a>**SETTLE-23. Version domain.** `version` MUST be an integer in `[0, 2^53-1]`; 0 is legal. A
non-integer, NaN, an infinity, a negative value, a value above `2^53-1` and any non-number are `invalid_claim` naming
`version`, never `missing_claim`. A `-0` is 0 and is accepted. A language with a fixed-size integer type range-checks
that type (Go `int64`). BoostX answers anything that is not a non-negative safe integer 400 `invalid-version`.
(Vectors: settle.json.)

<a id="settle-24"></a>**SETTLE-24. What version means (informative).** `version` orders the settlements of one bet
(partner, user, bet). It must increase between corrections but need not be sequential; a millisecond timestamp works.
BoostX keeps every version and reads the highest at read time, whatever the arrival order, so a lower version sent after
a higher one is stored, answered 200 and never wins. (Informative.)

<a id="settle-25"></a>**SETTLE-25. Re-sending a version (informative).** Re-sending a version BoostX already holds, with
the same `status`, `payout.amount`, `payout.currency`, `xSettle` and `settledAt`, is a no-op answered 200. `iat`, the
signatures, BoostX's receipt time and the demo stamp are not compared, so signing each attempt afresh is safe. This is
what makes the retry guidance of SETTLE-64 harmless. (Informative.)

<a id="settle-26"></a>**SETTLE-26. Conflicting re-send (informative).** Re-sending a version BoostX holds with a
different body is a conflict: BoostX keeps the original, discards the new values and still answers 200
`{"result":{"ok":true}}`; the partner gets no signal. A correction must go under a higher version, and a retry must
never re-stamp `settledAt`. (Informative.)

<a id="settle-27"></a>**SETTLE-27. xSettle is optional.** An absent or null `xSettle` MUST leave the `xSettle` member
out of the token; the SDK never writes `null` ([P-null-absent](#p-null-absent)). A given value, 0 included, MUST be
written. Go expresses absence with a nil `*float64`. BoostX treats an absent member and `null` alike. (Vectors:
settle.json, `absent`.)

<a id="settle-28"></a>**SETTLE-28. xSettle domain.** A given `xSettle` MUST be a finite number `>= 0`, with no upper
bound and no decimals rule; values below 1, 0 included, are legal. NaN, an infinity, a negative value and any
non-number are `invalid_claim` with the field token `xsettle`. BoostX answers 400 `invalid-xsettle`. (Vectors:
settle.json.)

<a id="settle-29"></a>**SETTLE-29. settledAt range.** `settledAt` MUST be an integer number of epoch milliseconds in
`[1e12, now + 86400000]`, inclusive at both ends, where `now` is the SDK's local clock in milliseconds at the time of
the call, read when the token is built (in `client.submit`, after the key-store lookup, [SETTLE-59](#settle-59)). The
floor (2001-09-09) refuses a seconds-scale timestamp; the ceiling refuses a micro- or nanosecond-scale one and any
far-future value, which would sit at the top of the partner's dashboard for good. Backdating is unrestricted down to the
floor. BoostX applies the same range against its own clock at receipt (400 `invalid-settled-at`). (Vectors: settle.json,
with the millisecond clock rule of FORMAT.md section 3.1.)

<a id="settle-30"></a>**SETTLE-30. settledAt categories.** An absent or null `settledAt`, and 0 (`-0` included), MUST
be `missing_claim` naming `settledAt`: 0 is outside the domain, so it reads as "not given", which is also all a Go
zero value can say. A negative, non-integer or out-of-range value, and any non-number, is `invalid_claim` naming
`settledAt`. `settledAt` is the one numeric parameter whose absence is `missing_claim`; `amount` and `version` are
`invalid_claim` when absent because 0 is legal for them (SETTLE-18). BoostX answers all of these 400
`invalid-settled-at`. (Vectors: settle.json.)

<a id="settle-73"></a>**SETTLE-73. Ids are used exactly as given.** The SDK MUST use `partner`, `user` and `bet`
exactly as given, with no trimming, case folding or Unicode normalisation, in the token, in the GID signing bytes and
in the client's key-store lookup. The in-memory key store matches the partner id byte for byte (KEYS group). BoostX
matches `gid.partner` byte for byte too, with no normalisation. (Vectors: settle.json.)

<a id="settle-74"></a>**SETTLE-74. Id length; no token length limit.** The builder MUST refuse an id longer than its
[GID-09](#gid-09) limit, 32 for `partner`, 64 for `user` and 96 for `bet` Unicode scalar values, with `invalid_claim`
naming that id. The SDK MUST NOT limit the token's length ([KEYS-43](#keys-43)). (Vectors: `settle.json`.)

<a id="settle-31"></a>**SETTLE-31. Builder check order.** The settlement form of [KEYS-19](#keys-19) (duplicate set
KEYS-19, GAMEPASS-08, GID-34, SETTLE-31; [P-check-order](#p-check-order)). The builder MUST run these checks in this
order and report the first that fails:

1. The private key, as far as it can be checked without signing (SETTLE-33): `invalid_private_key`.
2. `partner`: presence, then type (SETTLE-10).
3. `user`: presence, then type.
4. `bet`: presence, then type.
5. `status` (SETTLE-13, SETTLE-70).
6. `amount` domain (SETTLE-16).
7. The `unsettled` rule (SETTLE-17).
8. `currency`: presence, then shape (SETTLE-21).
9. `version` (SETTLE-23).
10. `xSettle`, when given (SETTLE-28).
11. `settledAt`: presence, then range (SETTLE-29, SETTLE-30).
12. `partner`, then `user`, then `bet`, each: well-formed (SETTLE-11), no `:` (SETTLE-12), within its length
    (SETTLE-74).
13. Signing the GID and the token: a key that passed step 1 but cannot sign is `invalid_private_key` (SETTLE-33).

This order binds SDKs only; BoostX's own order is not part of this specification. (Vectors: settle.json, keys.json,
cases with several faults.)

### 9.3 Keys

<a id="settle-33"></a>**SETTLE-33. The private key is checked first and never crashes.** The settlement form of
[KEYS-63](#keys-63) (duplicate set KEYS-63, GID-45, SETTLE-33; [P-key-usability](#p-key-usability)) and of
[KEYS-19](#keys-19). Before any parameter, the builder MUST refuse with `invalid_private_key` a missing key and any
key that is not a usable ECDSA P-256 private key as far as the platform lets it check without signing: in JS a
`CryptoKey` of type `private`, algorithm ECDSA, curve P-256, with the `sign` usage; in Go a non-nil key on
`elliptic.P256()` with `D`, `X` and `Y` set and a valid scalar (`ECDH()` succeeds). A key that passes those checks but
fails at signing MUST also be `invalid_private_key`, raised at that point. A key MUST never crash the caller (no
panic, no unclassified runtime error). (Vectors: settle.json.)

<a id="settle-59"></a>**SETTLE-59. Submit order.** Each `submitSettlement` call MUST run these steps in this order. A
failing step ends the call with that step's outcome, and no HTTP request is sent unless step 6 is reached:

1. An absent cancellation handle means none (SETTLE-69).
2. A handle already cancelled fails with that cancellation (SETTLE-62).
3. The per-attempt time limit starts (SETTLE-61).
4. The key store is asked for the partner private key of `params.partner`, passed as given, with no validation
   first (SETTLE-73; [KEYS-55](#keys-55)). A missing parameter set reads as an empty one
   ([GAMEPASS-48](#gamepass-48)), so the store is then asked for an absent partner id, in the language's way (JS
   `undefined`, Python `None`). A store error ends the call (SETTLE-60, SETTLE-58).
5. The token is built with that key and the parameters (SETTLE-31). A builder error ends the call.
6. One POST is sent (SETTLE-42, SETTLE-43).
7. At most the first 65 536 bytes of the body are read (SETTLE-55).
8. The answer is classified (SETTLE-50 to SETTLE-56).

Because the lookup comes first, an unknown partner is reported before an invalid field, and an absent, empty or
non-string `partner` reaches the store (the in-memory store answers `unknown_partner` for each, [KEYS-58](#keys-58)).
(Vectors: settle.json, `keyStoreCalled` and `requests`.)

<a id="settle-60"></a>**SETTLE-60. Client key-store outcomes.** The settlement form of [KEYS-58](#keys-58) (duplicate
set KEYS-58, SETTLE-60; [P-taxonomy](#p-taxonomy)). A client key store MUST fail with `unknown_partner` for a partner
it does not serve and MUST NOT fall back to a default key. For a partner it serves but holds no private key for, the
in-memory store fails with `invalid_private_key`. A store that returns no key (JS `undefined` or `null`, Go
`(nil, nil)`) leads to `invalid_private_key` from the builder's key check. The client consults the store on every
attempt and keeps no key between calls. A store's error reaches the caller with its category intact (SETTLE-58).
(Vectors: settle.json, keys.json.)

<a id="settle-65"></a>**SETTLE-65. Key rotation.** Because the client looks the key up and signs afresh on every
attempt (SETTLE-59, SETTLE-08), a retry after a partner key rotation is signed with the key the store holds then. A
token built once with `createSettlementToken` and stored is answered 401 by BoostX after a rotation, every time; the
cure is to build it again with the same version and values. The SDK README MUST tell partners to queue parameters,
not tokens, and the builder's documentation MUST say a stored token must be rebuilt after a rotation (JS TSDoc of
`createSettlementToken`, Go doc comment of `CreateSettlementToken`). (No vector: documentation and BoostX behaviour.)

### 9.4 Client construction

<a id="settle-35"></a>**SETTLE-35. A key store is required.** The client MUST be given a key store that can look up a
partner private key. An absent store (undefined, null, None, nil), and in a dynamically typed language one without a
callable lookup (JS: `partnerPrivateKey` not a function), MUST be refused when the client is constructed, with
`invalid_claim` ([P-taxonomy](#p-taxonomy); JS throws `invalid_claim`). Go's `client.New` panics instead
([HTTP-48](#http-48)), and also panics for a nil `*keys.MemoryKeyStore`.

Implementation-defined: a language with typed nil pointers MAY leave a typed-nil pointer of the partner's own store
type undetected at construction, provided its documentation says so (Go README and `New` doc comment). (Vectors:
settle.json, `at: "construct"`.)

<a id="settle-68"></a>**SETTLE-68. Transport injection.** The client MUST let the caller inject the HTTP transport;
the conformance runner depends on it. JS: the `fetch` option; a non-function is `invalid_claim` at construction,
absent or null means the global `fetch`, and the function is called unbound (Workers refuse a `fetch` invoked as a
method of another object). Go: `client.WithHTTPClient(hc)`; nil keeps the default client, and a given client is used
with its own transport and settings but copied for each attempt, so the caller's client is never modified (SETTLE-49).
(Vectors: settle.json, through every `client.submit` case.)

Implementation-defined: the layer at which the transport is injected and its shape: the platform's request function (JS
`fetch`), an HTTP client together with its transport (Go `http.Client`, with the transport below it), or a small
interface of the SDK's own, from a request to a status, headers and a body that can be read and stopped. Fixed whatever
the layer: the client follows no redirect ([SETTLE-49](#settle-49)), the time limit and cancellation stop every step,
the body read included ([SETTLE-61](#settle-61), [SETTLE-62](#settle-62)), and the failures pass through as
[SETTLE-58](#settle-58) says. The vectors check these through the injected transport, so they reach the default
transport only as far as it is the layer the fake replaces or sits under: an interface of the SDK's own carries the
no-follow setting on every request, as JS passes `redirect: 'manual'` to `fetch`, so that a fake can read it (FORMAT.md
section 6.6); the default transport behind such an interface is never what a fake replaces, so the SDK's own suite is
where it is shown to honour that setting, the time limit and cancellation.

Implementation-defined: the HTTP library behind the default transport, the platform's own or a third-party one (Python's
standard library has no asynchronous client, section 14.16).

<a id="settle-36"></a>**SETTLE-36. Default base URL.** An absent base URL (undefined, null, None, or no
`client.WithBaseURL`) MUST select `https://partners-s2s.boostx.cloud`, BoostX production. An empty string is not absent
(SETTLE-39). Exporting the default as a named constant is optional surface ([HTTP-63](#http-63); JS `DEFAULT_BASE_URL`,
Go `client.DefaultBaseURL`). (Vectors: settle.json, `options.baseURL: null`.)

<a id="settle-37"></a>**SETTLE-37. Base URL normalisation.** A given base URL MUST be normalised in exactly these steps,
in this order:

1. Remove leading and trailing characters of the set of SETTLE-38.
2. Remove every trailing `/`.
3. Remove one trailing `/api/integration/settlement`, compared case-sensitively, once.

So the forms accepted are a scheme and host, a scheme, host and path prefix, and the Settlement endpoint the
partner's dashboard shows. Slashes before a removed suffix stay (`https://h//api/integration/settlement` posts to
`https://h//api/integration/settlement`), an upper-case suffix is not removed, the suffix is not removed twice, and a
query or fragment is kept as written (SETTLE-41). (Vectors: settle.json, `request.url`.)

<a id="settle-38"></a>**SETTLE-38. The trimmed characters.** Step 1 of SETTLE-37 trims exactly U+0009, U+000A, U+000B,
U+000C, U+000D and U+0020, and no other character: a BOM, NEL (U+0085), NBSP and the other Unicode spaces stay. A URL
starting with one fails step 1 of SETTLE-39; one ending with one is left to the platform's parser (the
implementation-defined residue of [SETTLE-39](#settle-39): JS refuses a trailing NEL at construction, Go accepts it
there). The set is explicit because every language's default trim differs. (Vectors: settle.json.)

<a id="settle-39"></a>**SETTLE-39. Base URL validation.** After normalisation the base URL MUST satisfy all of:

1. It begins with `http://` or `https://`, the scheme compared ASCII case-insensitively.
2. The character after the `//` is neither `/` nor `\`.
3. The platform's URL parser accepts it and yields a non-empty host.

Otherwise the client MUST refuse construction ([P-taxonomy](#p-taxonomy): `invalid_claim` in JS, a panic in Go's
`client.New`). An empty or whitespace-only value is refused, never replaced by the default
([P-null-absent](#p-null-absent)). Steps 1 and 2 make the check exact across parsers: a WHATWG parser repairs
`http:/x`, `https:example.com` and `http:///x` into URLs with a host, while Go's `url.Parse` does not.

Implementation-defined: what the platform's parser accepts beyond steps 1 and 2. A URL that one parser reads differently
from another MAY be refused at construction, or accepted and then fail every submit or be sent where the platform's
parser resolves it. Measured cases: a `\` later in the authority (`https://host\path`: JS accepts it and fetch posts to
`https://host/path/api/integration/settlement`; Go refuses it), an out-of-range port (`https://host:99999`: JS refuses,
Go accepts and fails at send), a C0 control character (`https://host\x01`: JS accepts and fails at send, Go refuses),
non-ASCII or NEL in the host (accepted or refused per parser).

Implementation-defined: a dynamically typed SDK MAY convert a non-string base URL to text before normalising it (JS
`String(baseURL)`); the result is then validated like any other. An SDK that does not convert refuses a non-string base
URL at construction, as any other invalid one.

Implementation-defined: when several construction options are invalid at once, which one is reported (all are the same
category). (Vectors: settle.json, `at: "construct"`.)

<a id="settle-40"></a>**SETTLE-40. Scheme.** `http://` and `https://` are both accepted; the SDK does not enforce
HTTPS. Any other scheme is refused at construction by SETTLE-39. An `http://` URL to BoostX meets a redirect, which
the client does not follow, so it fails as an `api_error` carrying the 3xx (SETTLE-49); the READMEs tell partners to
use `https://`. (Vectors: settle.json.)

<a id="settle-41"></a>**SETTLE-41. The request URL.** The request URL MUST be the normalised base URL followed by
`/api/integration/settlement`, joined by plain text concatenation, never by URL resolution. A query or fragment in
the base therefore ends up before the path, and the platform reads the result as it reads any URL (a fragment hides
the path, so such a client posts to the root and meets BoostX's plain-text 404). (Vectors: settle.json,
`request.url`.)

### 9.5 Request

<a id="settle-42"></a>**SETTLE-42. Method and headers.** The request MUST be a `POST` with `Content-Type:
application/json` exactly, with no parameter such as `charset`. The SDK MUST NOT send an `Authorization` header or any
other credential; authentication is the token's two signatures. The SDK sets no other header itself: `Host`,
`Content-Length`, `User-Agent`, `Accept`, `Accept-Encoding` and the like are whatever the platform's HTTP stack sends
(Node fetch: `user-agent: node`, `accept: */*`; Go: `Go-http-client/1.1`). BoostX checks neither the content type nor
the user agent. (Vectors: settle.json, `request.method` and `request.contentType`.)

<a id="settle-43"></a>**SETTLE-43. Body.** The body MUST be a JSON object whose only member is `settlementJWT`, a
string holding the token. A token holds only base64url characters and dots, so every encoder writes the same bytes,
`{"settlementJWT":"<jwt>"}`. BoostX answers a body that is not JSON 400 `invalid JSON body` and a missing, empty or
non-string `settlementJWT` 400 `settlementJWT is required`; extra members are ignored. (Vectors: settle.json,
`request`.)

<a id="settle-47"></a>**SETTLE-47. Any GID.** The client sends a settlement for whatever `partner`, `user` and `bet` its
parameters give; the SDK keeps no record of games. (Informative.)

### 9.6 Response, acceptance and errors

<a id="settle-49"></a>**SETTLE-49. Redirects are not followed.** The client MUST NOT follow a redirect: a followed
301, 302 or 303 turns the POST into a GET without its body. A 3xx is classified like any other non-2xx answer
(SETTLE-56). JS passes `redirect: 'manual'` to `fetch`; Go copies the `http.Client` for each attempt and sets
`CheckRedirect` to return `http.ErrUseLastResponse`, leaving the caller's client unmodified. An injected transport
that follows redirects on its own (a custom `fetch` that ignores `redirect`) is the partner's responsibility. (Vectors:
settle.json; the runner checks the no-follow request on every case.)

<a id="settle-55"></a>**SETTLE-55. Body cap.** The client MUST read at most the first 65 536 bytes of the response
body, as the platform's HTTP stack delivers it (after any transfer or content decoding the platform applies), and
discard the rest. The acceptance test and the error member test apply to those bytes only. An absent body (a 204, or
a response whose body is null) is empty. A body truncated by the cap is usually not valid JSON, and then it is
neither an acceptance nor an error envelope. BoostX's own bodies are under 100 bytes; the cap only matters for a
responder that is not BoostX.

Implementation-defined: what happens to the rest of the body and to the connection after the cap (JS cancels the
stream; Go closes the body without draining it). (Vectors: settle.json, `padTo` and `padAt`.)

<a id="settle-54"></a>**SETTLE-54. Strict UTF-8 and no BOM.** [P-utf8](#p-utf8) applies to the capped bytes: they
MUST be well-formed UTF-8 (RFC 3629) and MUST NOT begin with EF BB BF, or the body is treated as not valid JSON. Bad
bytes are never replaced with U+FFFD, and a BOM is never stripped. On a 2xx that means `unexpected response`; on any
other status, the fallback text `HTTP <status>`. A cap that cuts a multi-byte sequence makes the bytes ill-formed.
The outcome is a visible retry, never a lost settlement. [P-surrogates](#p-surrogates) does not apply to a settlement
response: an unpaired surrogate escape inside it is not checked. (Vectors: settle.json.)

<a id="settle-53"></a>**SETTLE-53. Exact names, last duplicate wins.** In a response the member names `result`, `ok`
and `error` MUST be matched exactly, code unit for code unit after JSON unescaping ([P-names](#p-names)), so
`{"Result":{"OK":true}}` is not an acceptance and `{"Error":"x"}` carries no error member. When a name repeats within
one object, its last occurrence counts, `null` included, and objects are never merged
([P-duplicates](#p-duplicates)): `{"result":{"ok":true},"result":null}` is not an acceptance. The body and `result`
must each be exactly one JSON value and an object where this section needs one ([P-one-value](#p-one-value)).
(Vectors: settle.json, http.json.)

<a id="settle-50"></a>**SETTLE-50. Acceptance.** An answer is an acceptance exactly when all of these hold
([P-settlement-acceptance](#p-settlement-acceptance)):

1. The status is in `[200, 299]` (SETTLE-51).
2. The capped body passes SETTLE-54.
3. It is exactly one JSON value, optionally surrounded by JSON whitespace (space, tab, LF, CR), and that value is an
   object.
4. Its member `result` (SETTLE-53) is an object.
5. That object's member `ok` is the JSON literal `true`.

Other members, at either level, are ignored. The response headers, `Content-Type` included, play no part (SETTLE-71).
On an acceptance `submitSettlement` completes without a value (JS resolves `undefined`, Go returns nil). (Vectors:
settle.json.)

JSON nesting depth follows [P-one-value](#p-one-value) (decision [JSON nesting depth](#decision-json-depth)): a body
nested 64 levels deep or less is read like any other, and one nested deeper than the SDK's own limit is treated as not
valid JSON, so it is not an acceptance on a 2xx and gives the fallback text of SETTLE-56 otherwise.

<a id="settle-51"></a>**SETTLE-51. Any 2xx.** Every 2xx status with the acceptance body is an acceptance, 201 and 206
included. BoostX only ever answers 200; the SDK accepts the class so that a proxy or a future BoostX status within 2xx
does not turn a stored settlement into a retry. The SDK documentation says 2xx (JS README and `BoostxAPIError` TSDoc; Go
README and `APIError` doc comment). (Vectors: settle.json.)

<a id="settle-52"></a>**SETTLE-52. A 2xx that is not an acceptance.** A 2xx answer that fails SETTLE-50 MUST be an
`api_error` carrying that status and the error text `unexpected response`. Examples: an HTML page, `{}`,
`{"result":{}}`, `{"result":{"ok":"true"}}`, `{"result":{"ok":1}}`, `{"result":{"ok":false}}`, `{"result":null}`,
`null`, `{"ok":true}`, an empty body, a 204, a BOM before the acceptance body. A 2xx is never read for an `error`
member. (Vectors: settle.json.)

<a id="settle-56"></a>**SETTLE-56. Error text.** Every answer that is not an acceptance MUST be an
`api_error` carrying the HTTP status and one error text ([P-settlement-acceptance](#p-settlement-acceptance)):

| Answer | Error text |
|--------|------------|
| 2xx, not an acceptance | `unexpected response` |
| Any other status, whose capped body passes SETTLE-54 and is a JSON object whose member `error` (SETTLE-53) is a non-empty string | that string, unchanged |
| Any other status, otherwise (no body, not JSON, not an object, `error` absent, `null`, empty or not a string) | `HTTP ` followed by the status in decimal, e.g. `HTTP 404` |

Neither the server's reason phrase nor a table of canonical phrases is used: that keeps BoostX's plain-text
`Not Found` 404 (a wrong URL) apart from its JSON `not found` 404 (an unknown partner). The body's `status` member is
ignored. The wording of the error's message around the status and text is informative ([HTTP-60](#http-60)); both
SDKs write `boostx api error <status>: <text>`. Also covers: HTTP-59.

Implementation-defined: an `error` string holding an unpaired surrogate escape is carried in the language's string
type, so a language whose strings cannot hold one substitutes U+FFFD (JS keeps the lone surrogate; Go's decoder writes
U+FFFD). Vectors avoid such a string. (Vectors: settle.json, http.json, `status` and `apiError`.)

<a id="settle-57"></a>**SETTLE-57. The API error.** The API error MUST carry the category `api_error` and no other
category (section 4), the HTTP status as an integer, and the error text of SETTLE-56. JS: `BoostxAPIError`, which
extends `BoostxError`, with `code` `'api_error'`, `name` `'BoostxAPIError'`, `status` and `error`. Go:
`*client.APIError{StatusCode, Message}`, found with `errors.As`, wrapping no sentinel. Neither exposes the raw body,
the headers or the body's `status` member, and none of them is required. Whatever its status, an API error means the
settlement is not delivered yet (SETTLE-63). (Vectors: settle.json.)

<a id="settle-58"></a>**SETTLE-58. Failures that are not API errors.** Only an HTTP answer becomes an `api_error`.
Every other failure MUST reach the caller unchanged, or wrapped so that the platform's standard check still matches
it, and none is classified as retryable or final:

| Failure | Reported as | JS | Go |
|---------|-------------|----|----|
| Key-store error | the store's error, category intact | propagated unchanged | wrapped `resolve settlement key: %w` |
| Builder refusal | its taxonomy category (SETTLE-31) | `BoostxError` | wrapped `create settlement token: %w` |
| Transport failure (DNS, TLS, reset, a scheme the transport refuses) | the transport's error | the `fetch` `TypeError` | `*url.Error`, wrapped `send request: %w` |
| A failed body read, whatever the status | the read's error | propagated | wrapped `read response: %w` |
| Time limit | the platform's timeout error (SETTLE-61) | `TimeoutError` | matches `context.DeadlineExceeded` |
| Cancellation | the platform's cancellation (SETTLE-62) | the signal's reason | matches `context.Canceled` |

The wrapping prefixes are informative. (Vectors: settle.json, `failure`.)

<a id="settle-71"></a>**SETTLE-71. Response headers are ignored.** The client MUST NOT depend on the response
`Content-Type` or any other response header. BoostX's answers do not share one content type: its JSON answers, its
plain-text 404 `Not Found` and the page of an unhandled failure each carry their own. (Vectors: settle.json, `headers`.)

### 9.7 Time limit and cancellation

<a id="settle-61"></a>**SETTLE-61. One time limit per attempt.** The settlement form of [KEYS-54](#keys-54) (duplicate
set KEYS-54, SETTLE-61; [P-cancellation](#p-cancellation), [P-zero](#p-zero)). Each attempt MUST have one time limit,
started no later than the key-store lookup and covering the lookup, signing, sending and reading the capped body. Its
default is 30 seconds. An absent, null or 0 limit means the default. A negative or non-finite limit MUST be refused at
construction ([P-taxonomy](#p-taxonomy): `invalid_claim` in JS, a panic in Go's `client.New`). A value that is not a
number, where the language can pass one (a string), is no limit either and is refused the same way, as
[VERIFYKEYS-39](#verifykeys-39) says of the window (JS refuses it with the same check). Where the store interface
carries a cancellation handle or deadline (Go: `ctx`), the client MUST pass the attempt's bounded handle to it;
otherwise (JS) the client stops waiting for the store when the limit expires. No request is sent once the limit has
expired. Expiry is reported as the platform's timeout error (SETTLE-58), never as `api_error`. A caller's own deadline
or cancellation also bounds the attempt (SETTLE-62).

JS: the `timeoutMs` option. Go: the `Timeout` of the `http.Client` given to `client.WithHTTPClient` (the default
client's is 30 s), applied as a context deadline that starts before the lookup; a store must honour its `ctx` for the
limit to bound it, as the Go documentation says.

Implementation-defined: the limit's unit and representable range. JS takes an integer number of milliseconds in
`[1, 2^31-1]` (the platform timer's maximum) and refuses any other non-zero value, a fraction included, with
`invalid_claim`; Go takes any positive `time.Duration`. The limits the vectors expect to be accepted are integer
milliseconds in `[1, 2^31-1]`; their default and refusal cases also pass 0, `null`, -1, NaN and Infinity. (Vectors:
settle.json, keys.json, `options.timeoutMs` with `delayMs` and `bodyDelayMs`.)

<a id="settle-62"></a>**SETTLE-62. Cancellation.** A call whose cancellation handle is already cancelled MUST fail
with that cancellation before the key store is consulted: nothing is looked up, signed or sent. A cancellation during
the call MUST stop it at once, in any step, the body read included; nothing further is sent, and the call fails with
the platform's own cancellation error, unchanged or wrapped so that the platform's standard check matches it. JS: the
signal's `reason`, propagated unchanged (an `AbortError` for `controller.abort()`); the store receives no signal, and
the client stops waiting for it. Go: the context's error, returned as is before the lookup and wrapped after it, so
`errors.Is(err, context.Canceled)` holds. (Vectors: settle.json, `cancel`.)

<a id="settle-76"></a>**SETTLE-76. Cancellation and time limits in other languages.** The submit call MUST take the
platform's standard cancellation primitive: a handle passed to the call (an abort signal, a context, a cancellation
token), or cancelling the task that runs the call where that is the platform's way. Where the platform has none, the SDK
MUST define a token type of its own that the caller can cancel, and MUST document it. Where the primitive is cancelling
the task (Python's asyncio), the call takes no handle: an absent handle and `null` are the same, no cancellation, and a
task cancelled before it starts never runs the call, which meets steps 1 and 2 of [SETTLE-59](#settle-59) since no store
is consulted. Whatever the primitive, [SETTLE-62](#settle-62) applies unchanged: a cancellation stops the call at once
in any step of [SETTLE-59](#settle-59), the key-store lookup, the wait for the answer and the body read included, and
the call fails with the platform's cancellation error, or with the SDK token's, unchanged or wrapped so that the
platform's standard check matches it. An expired time limit ([SETTLE-61](#settle-61)) fails with the platform's timeout
error, or the one its HTTP stack raises when a request's time limit expires, and never with `api_error`. Where the
platform reports a cancellation and an expired limit with one error type (.NET raises `OperationCanceledException` for
both), the SDK MUST document how a caller tells them apart, for example by whether the caller's own handle was
cancelled. This rule restates SETTLE-61, SETTLE-62 and SETTLE-69 for a platform without JS's abort signal or Go's
context and never relaxes them; a conformance runner records the same choices (FORMAT.md, "Bringing up a new language").
(Vectors: settle.json, through its `cancel` and `options.timeoutMs` cases, which a runner drives with the SDK's own
primitive.)

Implementation-defined: the cancellation primitive, where the platform has no standard one; how a caller tells a
cancellation from an expired time limit that shares its error type; and, where the platform has more than one timeout
error, which one reports an expired limit (a Go expiry matches `context.DeadlineExceeded` or is a `net.Error` whose
`Timeout()` is true; Java offers `java.util.concurrent.TimeoutException` and `java.net.http.HttpTimeoutException`,
among others, section 14.17). The SDK documents each, since a partner's error handling is written against it.

<a id="settle-69"></a>**SETTLE-69. An absent handle means none.** An absent cancellation handle MUST mean no
cancellation ([P-null-absent](#p-null-absent)): JS options absent or null, or `signal` absent or null; a nil Go
context. It never raises a type error and never reaches the key store as nil (Go substitutes
`context.Background()` before anything else). (Vectors: settle.json.)

### 9.8 One attempt per call, retry guidance

<a id="settle-63"></a>**SETTLE-63. One attempt, no classifier.** A `submitSettlement` call MUST make at most one HTTP
request (none when a step before sending fails) and MUST offer no retry, no retry helper and no retryable or final
classification of its errors (no `isRetryable`, no `isFinal`). The only success is the acceptance of SETTLE-50. Every
other outcome, any status, a 4xx included, a network or timeout error, a key-store error, a parameter refused before
sending, means the settlement is not delivered yet ([P-settlement-acceptance](#p-settlement-acceptance)). This is the
decision [retry until ok](#decision-retry-until-ok): a 4xx can come from a BoostX release that a later fix undoes, and a
re-send of a version BoostX holds is a no-op (SETTLE-25), so retrying costs nothing while stopping can lose a
settlement. (Vectors: settle.json, `requests`.)

<a id="settle-64"></a>**SETTLE-64. Retry and diagnosis guidance.** The SDK README MUST tell partners:

- Queue the parameters, not a signed token, and send the same parameters again until accepted: the same `version`,
  `status`, `amount`, `currency`, `xSettle` and `settledAt`, never re-stamped; each attempt is signed afresh.
- Use a backoff over a window, for example after 1 minute, 5 minutes and 30 minutes, then hourly for 3 days; when the
  window ends without acceptance, raise an alert and contact BoostX.
- A correction is not a retry: it goes under a strictly higher version.
- Status and error text serve diagnosis only: `401` means the keys or the partner id; a `404` whose text is
  `not found` means a partner id BoostX did not assign; a 3xx, a `404` with any other text (BoostX's plain-text 404
  reads `HTTP 404`) or a 2xx without the acceptance body means the base URL; a `400` with an `invalid-*` text names the
  field; a 5xx is BoostX's side.

Both READMEs carry this today (JS README, Submitting Settlements; Go README, settlement section), and the partner docs
say the same (Settlement, POST /api/integration/settlement and Retries). (No vector: documentation.)

<a id="settle-66"></a>**SETTLE-66. No age limit.** The SDK MUST NOT refuse a settlement for its age: `iat` is the
signing time and is never checked, and only the `settledAt` floor of 1e12 bounds the past. BoostX applies no age
limit either, so a settlement for a bet settled long ago is accepted on the strength of its signatures. (Vectors:
settle.json, a `settledAt` far in the past.)

### 9.9 Surface

<a id="settle-14"></a>**SETTLE-14. The statuses are exposed.** The SDK MUST expose the eight statuses of SETTLE-13
publicly, in the order listed there. JS: `SETTLEMENT_STATUSES` (a read-only tuple) and the type `SettlementStatus`. Go:
the constants `tokens.StatusWin`, `StatusLose`, `StatusCancelled`, `StatusRefund`, `StatusHalfWin`, `StatusHalfLose`,
`StatusCashout`, `StatusUnsettled`, also on the `boostx` facade.

Implementation-defined: the form they take, in the language's idiom (an exported list, an enum or named constants), and
whether the `status` parameter takes that form or stays a plain string. (No vector: API surface.)

<a id="settle-67"></a>**SETTLE-67. No settlement parser; generic helpers optional.** The settlement form of
[KEYS-62](#keys-62) (duplicate set KEYS-62, GID-42, SETTLE-67, HTTP-62; [P-optional-surface](#p-optional-surface)).
An SDK needs no SettlementJWT parser, since a partner never receives one. Generic JWT sign and parse helpers are
optional: Go exports `tokens.SignJWT`, `tokens.ParseJWT` and `tokens.RegisteredClaims`, with which a partner can read
its own settlement token back; JS exports none. (No vector: optional surface.)

The settlement surface of this section:

| Concept | Required | JS | Go |
|---------|----------|----|----|
| Builder | yes | `createSettlementToken` | `tokens.CreateSettlementToken` |
| Parameter set | yes | `SettlementParams` | `tokens.SettlementParams` |
| Status set | yes | `SETTLEMENT_STATUSES`, `SettlementStatus` | `tokens.Status*` |
| Client and constructor | yes | `BoostxClient`, `new BoostxClient(keyStore, options?)` | `client.Client`, `client.New(ks, opts...)` |
| Client options | yes: base URL, transport, time limit | `ClientOptions {baseURL, fetch, timeoutMs}` | `client.WithBaseURL`, `client.WithHTTPClient` (its `Timeout`) |
| Submit | yes | `submitSettlement(params, { signal }?)` | `SubmitSettlement(ctx, params)` |
| API error | yes | `BoostxAPIError` | `client.APIError` |
| Client key-store contract | yes | `ClientKeyStore` | `client.KeyStore` |
| Default base URL constant | no | `DEFAULT_BASE_URL` | `client.DefaultBaseURL` |
| Money type | no | none (flat `amount`, `currency`) | `tokens.Money` (the payload field type) |
| Generic JWT helpers | no | none | `tokens.SignJWT`, `tokens.ParseJWT` |
| Settlement parser | no, none defined | none | none |

### 9.10 What the SDK sees from BoostX (informative)

None of this binds an SDK; it explains the rules above.

<a id="settle-32"></a>**SETTLE-32. Field errors only after both signatures.** BoostX returns a field-level 400 only
after the outer JWT signature and the GID signature both verify, and answers a token that fails to verify 401
(SETTLE-46). A 400 `invalid-*` therefore proves the keys are configured correctly.

<a id="settle-44"></a>**SETTLE-44. Route.** BoostX serves `POST /api/integration/settlement`, the path the client sends
([SETTLE-41](#settle-41)). A method or path it does not serve answers 404 with the plain-text body `Not Found`, which
the client reports as `HTTP 404` ([SETTLE-56](#settle-56)).

<a id="settle-45"></a>**SETTLE-45. Answers.** 200 `{"result":{"ok":true}}` with no `status` member. Every JSON error is
`{"status":<http>,"error":"<code>"}`: 400 `invalid JSON body`, `settlementJWT is required` and the six `invalid-*`
codes (`invalid-status`, `invalid-version`, `invalid-xsettle`, `invalid-settled-at`, `invalid-payout`,
`invalid-currency`); 401 `unauthorized`; 404 `not found`, which means BoostX does not know the partner id
(SETTLE-75); 500 `not-stored`. An unhandled failure on BoostX's side becomes a non-JSON 500, which the client reads as
`HTTP 500`.

<a id="settle-46"></a>**SETTLE-46. What 401 covers.** 401 `unauthorized` means the signature or the token is wrong: the
token could not be read as a settlement, or its signature or its GID's signature did not verify. A token the SDK builds
is readable, so for it a 401 points at the keys or the partner id ([SETTLE-64](#settle-64)).

<a id="settle-48"></a>**SETTLE-48. not-stored.** When a valid settlement was not stored, BoostX answers 500
`{"status":500,"error":"not-stored"}`. Re-sending the same settlement is safe.

<a id="settle-72"></a>**SETTLE-72. Concurrent submissions.** Of concurrent submissions of one version (the same
`partner`, `user`, `bet` and `version`), one is stored; every other is answered 200, as a no-op when its body matches
and otherwise as the conflict of SETTLE-26. Two parallel identical attempts both get 200, so parallel retries of one
settlement are harmless.

<a id="settle-75"></a>**SETTLE-75. Unknown partner.** A settlement whose `gid.partner` names a partner id BoostX does
not know is answered 404 `{"status":404,"error":"not found"}`. It means BoostX does not know this partner id; the
partner checks the id it sends.

Further BoostX facts the rules above rely on: BoostX enforces `exp` and `nbf` when present (SETTLE-04); it stamps demo
itself (SETTLE-06); it verifies with one partner public key, so a token signed before a rotation fails (SETTLE-08,
SETTLE-65); it refuses a non-canonical GID signature with 401 (SETTLE-09; decision [canonical GID
signatures](#decision-canonical-gid-signatures)); it stores `amount` as sent (SETTLE-20); it only ever answers 200 on
success (SETTLE-51); it applies no age limit (SETTLE-66); and it answers an `http://` request with a redirect
(SETTLE-40).

## 10. Verify-keys (VERIFYKEYS)

The verify-keys exchange is the signed round trip behind Test integration. BoostX sends a **request** token (signed with
the BoostX private key held for the partner, `iss` `"boostx"`, `aud` the partner id) to `POST /verify-keys`; the partner
answers with a **response** token (signed with the partner private key, `iss` the partner id, `aud` `"boostx"`) that
echoes the request's nonce. This section defines the builders, the unverified extraction, the parsers, the reason
strings, the error mapping and the endpoint. For SDK behaviour this section is the authority; the partner docs describe
the same exchange for people (Keys and Test integration).

Neutral names used below, with both spellings:

| Neutral name | JS | Go (package `tokens` unless noted; the `boostx` facade re-exports each) | Surface |
|---|---|---|---|
| request builder | `createVerifyKeysRequestToken(boostxPrivateKey, partnerID, nonce): Promise<string>` | `tokens.CreateVerifyKeysRequestToken(boostxPriv, partnerID string, nonce int32) (string, error)` | required (a test aid) |
| response builder | `createVerifyKeysResponseToken(partnerPrivateKey, partnerID, nonce): Promise<string>` | `tokens.CreateVerifyKeysResponseToken(partnerPriv, partnerID string, nonce int32) (string, error)` | required |
| request extractor | `extractVerifyKeysRequestPartner(token): string` | `tokens.ExtractVerifyKeysRequestPartner(token string) (string, error)` | required |
| request parser | `parseVerifyKeysRequestToken(token, boostxPublicKey, partnerID, { maxSkewSeconds }?): Promise<VerifyKeysRequest>` | `tokens.ParseVerifyKeysRequestToken(token, boostxPub, partnerID string, maxSkew time.Duration) (*VerifyKeysRequest, error)` | required |
| response parser | `parseVerifyKeysResponseToken(token, partnerPublicKey, partnerID, { maxSkewSeconds }?): Promise<VerifyKeysResponse>` | `tokens.ParseVerifyKeysResponseToken(token, partnerPub, partnerID string, maxSkew time.Duration) (*VerifyKeysResponse, error)` | required (a test aid) |
| reason mapper | `verifyKeysReason(err)` | `tokens.VerifyKeysReason(err) string` | required |
| endpoint, router | `createFetchHandler(options)`; `createNodeHandler(options)` from the `/node` entry | `handlers.Mount(mux, prefix, betStore, keyStore)` (`boostx.MountHandlers`) | required |
| endpoint, per-endpoint | `handleVerifyKeys(body, { keyStore })` on a parsed body | `handlers.NewVerifyKeysHandler(keyStore)` (`boostx.NewVerifyKeysHandler`, an `http.Handler`) | optional ([Optional SDK surface](#p-optional-surface)) |
| BoostX identity | `BOOSTX_IDENTITY` | `tokens.BoostxIdentity` | optional (named constant) |
| default window | `DEFAULT_VERIFY_KEYS_MAX_SKEW_SECONDS` (30) | none | optional (named constant) |
| reason strings | type `VerifyKeysReason` only | `tokens.VerifyKeysReasonShape`, `…IssAud`, `…Stale`, `…NonceFormat`, `…Signature` | optional (named constants) |
| failure category | `BoostxError` with code `invalid_verify_keys` and `.reason` | `tokens.ErrInvalidVerifyKeys`, wrapped by `ErrVerifyKeysShape`, `ErrVerifyKeysIssAud`, `ErrVerifyKeysStale`, `ErrVerifyKeysNonce`; a signature failure wraps `ErrInvalidSignature` instead of a reason sentinel | required (the category) |

The five wire reasons, each the exact lowercase ASCII string:

| Reason | Covers |
|---|---|
| `shape` | A malformed token (segment count, a header or payload segment's encoding, bytes, JSON or object, a lone surrogate escape); a claim of the wrong JSON type; a present `exp` or `nbf` that is `null` or not a number; and, in extraction only, an `aud` that names no partner |
| `signature` | `alg` not the string `"ES256"`, any `crit`, a signature segment that is not canonical or not 64 bytes, a failed ECDSA verification; also what the reason mapper returns for an unusable verifying key |
| `iss-aud` | `iss` or `aud` not exactly the expected value (absent or `null` reads as `""`); in a handler, an `aud` the key store does not serve |
| `stale` | `iat` outside the window (absent or `null` reads as `0`), `exp <= now`, `nbf > now` |
| `nonce-format` | `verifyKeys.nonce` absent, `null`, not a JSON number, not integral, or outside `[1, 2147483647]`; an absent or `null` `verifyKeys` counts as an absent nonce |

Principles this section applies: [Exact JSON member names](#p-names), [Repeated member names: the last occurrence
wins](#p-duplicates), [One JSON value, and an object where the spec needs one](#p-one-value), [Strict UTF-8 and no
byte order mark](#p-utf8), [Ill-formed Unicode (lone surrogates)](#p-surrogates), [Canonical unpadded base64url
everywhere](#p-base64url), [Signature failure versus malformed token](#p-signature-vs-shape), [Integer claims are
judged by value](#p-integers), [Null versus absent](#p-null-absent), [What 0 means for an optional
number](#p-zero), [Check order is normative; configuration before input](#p-check-order), [Unverified extraction
before any key lookup](#p-extraction), [Key usability: never crash, refuse at startup](#p-key-usability), [Closed
error taxonomy](#p-taxonomy), [HTTP error strings and echoed ids](#p-http-errors), [exp and nbf are enforced when
present](#p-exp-nbf), [Verify-keys window](#p-window), [iat is exposed, never age-checked by the SDK](#p-iat-exposed),
[Emitted bytes are not canonical, except the GID payload](#p-emitted-bytes), [Optional SDK
surface](#p-optional-surface), [Request body](#p-body), [Routing and methods](#p-routing).

Vectors: the token-level rules of this section are pinned by `verifykeys.json` (operations `verifykeys.createRequest`,
`verifykeys.createResponse`, `verifykeys.extractRequest`, `verifykeys.parseRequest`, `verifykeys.parseResponse`); the
endpoint rules by `http.json` (operation `http.serve` with `endpoint` `verify-keys`).

### 10.1 Protocol

<a id="verifykeys-01"></a>**VERIFYKEYS-01. The request BoostX sends.** BoostX calls `POST` on the partner's API URL
with one trailing `/` removed, followed by `/verify-keys`, with `Content-Type: application/json`, no `Authorization`
header, and the body `{"verifyKeysJWT":"<token>"}`. An SDK handler MUST read the token from the body member named
exactly `verifyKeysJWT` ([VERIFYKEYS-56](#verifykeys-56)) and MUST NOT require any header, credential or other body
member. (Vectors: `verifykeys.json`.)

<a id="verifykeys-02"></a>**VERIFYKEYS-02. When the exchange runs (informative).** BoostX runs the exchange only on
demand, from Test integration on the dashboard, never during play. Nothing in an SDK depends on this. (Informative.)

<a id="verifykeys-03"></a>**VERIFYKEYS-03. Concurrent requests; the endpoint is stateless.** Each run sends three
`POST`s at the same moment, the real exchange and the two probes of [VERIFYKEYS-62](#verifykeys-62), each a single
attempt with no retry. An SDK's verify-keys handler MUST answer each request on its own: it MUST keep no state between
requests (no nonce tracking, no memory of earlier failures), MUST NOT serialise or rate-limit requests, and MUST NOT
block or delay a caller after repeated signature failures. The iat window is the only replay defence
([VERIFYKEYS-66](#verifykeys-66)). (No vector: not observable through one request.)

<a id="verifykeys-04"></a>**VERIFYKEYS-04. No redirects.** An SDK's own code MUST answer at the path itself and MUST NOT
answer 3xx: BoostX expects its answer at the URL it calls. A host router may still redirect a path it normalises (a `//`
or a `..`), as [Routing and methods](#p-routing) allows. (No vector: the SDK part follows from
[VERIFYKEYS-58](#verifykeys-58).)

<a id="verifykeys-05"></a>**VERIFYKEYS-05. Nonces come from the caller.** BoostX draws each nonce uniformly from
`[1, 2^31-1]` and sends it as a JSON integer; it never sends 0 (informative). The SDK builders MUST take the nonce from
their caller and MUST NOT generate, cache or replace one; the response builder, as the handler calls it, signs the
nonce of the verified request ([VERIFYKEYS-11](#verifykeys-11) step 6). (No vector: informative.)

<a id="verifykeys-06"></a>**VERIFYKEYS-06. The request token.** The request builder MUST emit a compact JWS whose
protected header has exactly the members `alg` `"ES256"` and `typ` `"JWT"`, and whose payload has exactly the members
`verifyKeys` (an object whose only member is `nonce`, the given nonce as a JSON integer), `iss` `"boostx"`, `aud` the
given partner id and `iat` (the builder's clock in whole Unix seconds, rounded down). It MUST NOT emit `exp`, `nbf`,
`kid`, `jti` or any other member. BoostX's own request header is `{"alg":"ES256"}` alone: the request builder is a
test aid and does not reproduce that header, and receivers ignore `typ` ([KEYS-23](#keys-23)).

Implementation-defined: member order, string escaping, number spelling and whitespace, as [Emitted bytes are not
canonical, except the GID payload](#p-emitted-bytes) allows. (Vectors: `verifykeys.json`.)

<a id="verifykeys-07"></a>**VERIFYKEYS-07. The response token's payload.** The response builder MUST emit the payload
members `verifyKeys` (an object whose only member is `nonce`, the given nonce as a JSON integer), `iss` the given
partner id, `aud` `"boostx"` and `iat` (the builder's clock in whole Unix seconds, rounded down, read at signing), and
nothing else, neither at the root nor inside `verifyKeys`. Its header follows [VERIFYKEYS-69](#verifykeys-69).
(Vectors: `verifykeys.json`.)

<a id="verifykeys-08"></a>**VERIFYKEYS-08. BoostX's identity.** BoostX's identity in verify-keys tokens is the exact,
case-sensitive string `"boostx"`: the `iss` of a request and the `aud` of a response. Every comparison against it is
byte for byte (`"BOOSTX"` is a different string). An SDK MAY export it as a named constant ([HTTP-63](#http-63)).
(Vectors: `verifykeys.json`.)

<a id="verifykeys-17"></a>**VERIFYKEYS-17. How BoostX reads a refusal (informative).** BoostX takes the reason from a
JSON body's string `error` member: the text `invalid verifyKeysJWT:`, found anywhere in the string and matched
case-sensitively, then any whitespace, then the run of letters, digits, `_` and `-` that follows is the reason. It
reports `signature`, `iss-aud` and `stale` each with its own hint; `shape`, `nonce-format`, any other text and a body
without a string `error` are reported like `signature`, with the raw error quoted in the hint. This is why the refusal
text of [VERIFYKEYS-16](#verifykeys-16) is normative up to and including the reason, and free after it
([VERIFYKEYS-14](#verifykeys-14)). (Informative.)

<a id="verifykeys-18"></a>**VERIFYKEYS-18. How BoostX classifies an answer (informative), and what that requires.**
For the real exchange BoostX reports a network error as unreachable; status 404 or 405 as a missing endpoint whatever
the body; a body that is not JSON (an empty one included) with any other status as a malformed answer; a non-2xx JSON
body by the reason ([VERIFYKEYS-17](#verifykeys-17)); and any 2xx as success so far. Therefore an SDK
handler MUST answer success with 200, MUST answer 404 and 405 only as the routing rule says
([VERIFYKEYS-58](#verifykeys-58)), and MUST give every answer a JSON body ([VERIFYKEYS-68](#verifykeys-68)).
(Vectors: `http.json`.)

<a id="verifykeys-19"></a>**VERIFYKEYS-19. The success body.** The success answer MUST be status 200 with the JSON
body `{"result":{"responseJWT":"<response token>"}}` and no other members. BoostX requires `result` to be an object
holding a non-empty string `responseJWT` and ignores other members (informative). (Vectors: `verifykeys.json`.)

<a id="verifykeys-20"></a>**VERIFYKEYS-20. Which keys the exchange uses.** A request is verified with the BoostX
public key the key store holds for the request's `aud`, and the response is signed with the partner private key the
key store holds for that same id. The exchange involves no GID, and an SDK MUST NOT consult the partner public key
list for it. BoostX verifies the response with the one partner public key it stores (informative).
(Vectors: `verifykeys.json`.)

### 10.2 Partner id rules

<a id="verifykeys-09"></a>**VERIFYKEYS-09. The partner id argument.** The two builders and the two parsers take a
partner id (`partnerID`) and MUST check items 1 and 2 after the key and before anything else; a builder checks item 3
after the nonce ([VERIFYKEYS-49](#verifykeys-49), [VERIFYKEYS-46](#verifykeys-46) step A2):

1. Absent, `null`, a non-string (where the language can pass one) or the empty string is `missing_claim`, naming the
   field `partnerID`. This partner id is not a GID id: the category for a non-string is the one used for
   these functions, and the one an in-memory key store gives a partner id it cannot use ([KEYS-56](#keys-56)), not
   the `invalid_claim` that [Builder id rules](#p-builder-ids) gives a non-string GID id.
2. Exactly `"boostx"`, compared byte for byte, is `invalid_claim`, naming the field `partnerID`. A partner named
   `boostx` would make a request's `iss`/`aud` pair identical to a response's, leaving the signing key as the only
   thing telling the directions apart.
3. A builder MUST refuse a partner id that is a string but not well-formed Unicode (an unpaired surrogate, or invalid
   UTF-8 where the language's strings can hold it) with `invalid_claim`, naming `partnerID`, checked after the nonce,
   as [Ill-formed Unicode (lone surrogates)](#p-surrogates) requires of every id a builder signs and [Check order is
   normative; configuration before input](#p-check-order) places well-formedness last (decision
   [verify-keys partner id](#decision-verify-keys-partner-id)). A lone high or low surrogate (JS) and invalid UTF-8
   (Go) are refused alike; a high-then-low pair is one well-formed character and signs.

An SDK MUST NOT check the partner id's alphabet. BoostX itself reserves `boostx` (informative). A parser does not test
well-formedness: an ill-formed partner id never equals a claim (those are well-formed after step 1.9 of
[VERIFYKEYS-46](#verifykeys-46)) and fails as `iss-aud`. A language whose types forbid a non-string needs no check for
it, and a runner skips such a case. (Vectors: `verifykeys.json`.)

<a id="verifykeys-34"></a>**VERIFYKEYS-34. iss and aud are compared exactly.** The request parser expects `iss`
`"boostx"` and `aud` equal to its partner id; the response parser expects `iss` equal to its partner id and `aud`
`"boostx"`. Both comparisons MUST be exact string equality, code unit for code unit: no case folding, trimming or
Unicode normalisation. Any mismatch is `iss-aud`. (Vectors: `verifykeys.json`.)

<a id="verifykeys-72"></a>**VERIFYKEYS-72. The extracted aud goes to the key store unchanged.** The request extractor
refuses only an `aud` that is `""` or exactly `"boostx"` ([VERIFYKEYS-10](#verifykeys-10)). Every other `aud` (a case
variant such as `"BOOSTX"` or `"Partner-A"`, surrounding whitespace, punctuation or non-ASCII characters) MUST be
returned, and passed to the key store, exactly as decoded. The key store MUST match it byte for byte and fail with
`unknown_partner` for an id it does not serve ([KEYS-48](#keys-48), [KEYS-50](#keys-50)), so an honest store makes such
a request `400 invalid verifyKeysJWT: iss-aud (unknown partner …)` ([VERIFYKEYS-13](#verifykeys-13)). (Vectors:
`verifykeys.json`.)

### 10.3 Extraction and handler pipeline

<a id="verifykeys-10"></a>**VERIFYKEYS-10. The request extractor.** The request extractor returns the unverified
`aud` of a request token, for choosing keys only. It MUST run these steps in order and fail at the first, every
failure being `invalid_verify_keys` with reason `shape`:

1. The token is a string of exactly three `.`-separated segments ([VERIFYKEYS-24](#verifykeys-24)).
2. The payload segment passes step 1.9 of [VERIFYKEYS-46](#verifykeys-46): canonical unpadded base64url, strict
   UTF-8 without a byte order mark, exactly one JSON value that is an object, no lone surrogate escape.
3. The claim types pass step 2 of [VERIFYKEYS-46](#verifykeys-46). The nonce is not judged
   ([VERIFYKEYS-42](#verifykeys-42)).
4. `aud` (absent or `null` read as `""`) is neither `""` nor exactly `"boostx"`.

It MUST NOT read the header or the signature segment, and MUST NOT call a key store. It returns `aud` unchanged
([VERIFYKEYS-72](#verifykeys-72)). This is the verify-keys form of [Unverified extraction before any key
lookup](#p-extraction). A Booster or CheckBet token given to it fails at step 4, since it has no `aud`. (Vectors:
`verifykeys.json`.)

<a id="verifykeys-11"></a>**VERIFYKEYS-11. The handler pipeline.** After routing and the method check
([VERIFYKEYS-58](#verifykeys-58)), a verify-keys handler MUST run these steps in order, the first failure giving the
answer:

1. Read the body ([VERIFYKEYS-55](#verifykeys-55) to [VERIFYKEYS-57](#verifykeys-57)): a bad body is
   `400 {"error":"invalid request body"}`; otherwise the token is the `verifyKeysJWT` string, `""` when absent or
   `null`.
2. Extract the partner id with the request extractor ([VERIFYKEYS-10](#verifykeys-10)): any failure is
   `400 {"error":"invalid verifyKeysJWT: shape"}`, with no key-store call.
3. Look up the BoostX public key for that id: `unknown_partner` is the 400 of [VERIFYKEYS-13](#verifykeys-13); any
   other failure is `500 {"error":"failed to get boostx key"}` ([VERIFYKEYS-15](#verifykeys-15)).
4. Parse the token with the request parser, that key, the extracted id as `partnerID` and the fixed 30-second window
   ([KEYS-41](#keys-41)): an `invalid_public_key` error is `500 {"error":"failed to verify token"}`; an
   `invalid_verify_keys` error is `400 {"error":"invalid verifyKeysJWT: <reason>"}` ([VERIFYKEYS-16](#verifykeys-16)).
5. Look up the partner private key for that id: `unknown_partner` is the 400 of [VERIFYKEYS-13](#verifykeys-13); any
   other failure is `500 {"error":"failed to get partner private key"}`.
6. Sign the response with the response builder, that key, the extracted id as `partnerID` and the verified request's
   nonce unchanged: any failure is `500 {"error":"failed to sign response"}`.
7. Answer `200 {"result":{"responseJWT":"<token>"}}` ([VERIFYKEYS-19](#verifykeys-19)).

The private key is looked up only after the request verified, so a refused token is answered 400 even when that
partner's private key is missing. Unlike [HTTP-21](#http-21), which looks up both verifying keys before parsing, this
pipeline needs one verifying key and one signing key, in that order. The handler needs no bet store
([HTTP-46](#http-46)).

Implementation-defined: step 4 can raise nothing but the two categories named there (the partner id comes from step 2
and the window is fixed), so how an SDK would answer any other error from it is not specified. (Vectors:
`verifykeys.json`.)

<a id="verifykeys-12"></a>**VERIFYKEYS-12. The response iss is the matched aud.** The response
`iss` MUST be the partner id the deployment serves that the request's `aud` named: the `aud` is matched byte for byte
against the ids the deployment serves (no case folding, trimming or normalisation), and nothing is signed for an `aud`
that is not served. An SDK handler meets this by signing only after the key store returned keys for exactly the
extracted id (steps 3 and 5 of [VERIFYKEYS-11](#verifykeys-11)), with that id as `iss`; key stores match ids byte for
byte ([VERIFYKEYS-72](#verifykeys-72)). Echoing `aud` into `iss` without that match is forbidden. A deployment that
serves one id compares `aud` with it. BoostX cannot tell the two forms apart (it checks only that `iss` equals the
partner id), and its foreign-id probe catches a store that answers for any id ([VERIFYKEYS-62](#verifykeys-62)). Also
covers: HTTP-36. (Vectors: `http.json`, `verifykeys.json`.)

<a id="verifykeys-13"></a>**VERIFYKEYS-13. Unknown partner on either lookup.** When the key store reports the
extracted id as not served (`unknown_partner`) on the BoostX public key lookup or the partner private key lookup, the
handler MUST answer `400 {"error":"invalid verifyKeysJWT: iss-aud (unknown partner \"<id>\")"}`: an id this deployment
does not serve is an id mismatch on the wire, and BoostX reports it as an `iss-aud` failure on the real exchange and as
a pass on the foreign-id probe. The text after `iss-aud` follows [VERIFYKEYS-14](#verifykeys-14).
(Vectors: `verifykeys.json`.)

<a id="verifykeys-14"></a>**VERIFYKEYS-14. Text after the reason is free-form.** A verify-keys
refusal's `error` string MUST start with exactly `invalid verifyKeysJWT: ` followed by the reason. Anything after the
reason, such as ` (unknown partner "<id>")`, is diagnostic text that no reader may parse.

Implementation-defined: the wording after the reason, and how the echoed id is quoted and escaped (JSON escaping and Go
`%q` escaping give different texts for control characters, and Go's JSON encoder writes `<`, `>` and `&` as `\u003c`,
`\u003e`, `\u0026`); the SDKs write the parenthetical of [VERIFYKEYS-13](#verifykeys-13) with the id between double
quotes. BoostX reads only the reason ([VERIFYKEYS-17](#verifykeys-17)). See [HTTP error strings and echoed
ids](#p-http-errors). Also covers: HTTP-38. (Vectors: `http.json`, `verifykeys.json`, comparing a prefix.)

<a id="verifykeys-15"></a>**VERIFYKEYS-15. Server-side failures are 500.** The handler MUST answer:

| Failure | Answer |
|---|---|
| BoostX public key lookup fails with anything but `unknown_partner` | `500 {"error":"failed to get boostx key"}` |
| The returned BoostX public key is not usable (absent, `null`, not P-256, or refused by the platform) | `500 {"error":"failed to verify token"}` |
| Partner private key lookup fails with anything but `unknown_partner` (an in-memory store missing that role included) | `500 {"error":"failed to get partner private key"}` |
| The returned partner private key cannot sign (absent, `null`, not P-256) | `500 {"error":"failed to sign response"}` |

These strings are fixed, like the others of [HTTP error strings and echoed ids](#p-http-errors). BoostX reports any
of them like a `signature` refusal, with the error text in the hint (informative). (Vectors: `verifykeys.json`.)

<a id="verifykeys-16"></a>**VERIFYKEYS-16. Token refusals.** A token the request parser refuses MUST be answered
`400 {"error":"invalid verifyKeysJWT: <reason>"}` with the bare reason of [VERIFYKEYS-52](#verifykeys-52) and nothing
after it; an extraction failure is the same with reason `shape`. Only the unknown-partner answer appends text
([VERIFYKEYS-13](#verifykeys-13)). (Vectors: `verifykeys.json`.)

### 10.4 JWS and payload

The JWS rules are shared with every inbound token and written in 5.4 and 5.5; this subsection gives their verify-keys
outcomes. The normative order is [VERIFYKEYS-46](#verifykeys-46) (the verify-keys form of [KEYS-67](#keys-67)).

<a id="verifykeys-21"></a>**VERIFYKEYS-21. alg and signature length.** The header's `alg` MUST be exactly the JSON
string `"ES256"` and is checked before the signature segment; the signature segment MUST decode to exactly the 64
bytes `r || s`. Anything else (`"none"`, `"es256"`, `"ES384"`, a 63-byte signature) is reason `signature`, as
[Signature failure versus malformed token](#p-signature-vs-shape) requires. (Vectors: `verifykeys.json`.)

<a id="verifykeys-24"></a>**VERIFYKEYS-24. Segment count.** A token that is not exactly three `.`-separated segments
(empty, one, two, four or more) MUST be refused with reason `shape`, by the extractor and the parsers alike. A
non-string token, where the language can pass one, is refused the same way. (Vectors: `verifykeys.json`.)

<a id="verifykeys-27"></a>**VERIFYKEYS-27. No trimming.** The token MUST be used exactly as received: no trimming of
whitespace or line breaks, no unfolding, no other normalisation before it is split. Whitespace makes the segment that
holds it non-canonical ([Canonical unpadded base64url everywhere](#p-base64url)), and the reason follows the check
order of [VERIFYKEYS-46](#verifykeys-46):

| Where the whitespace is | Parser | Handler |
|---|---|---|
| In the header segment (leading whitespace included) | `shape` (step 1.2) | `shape` (step 1.2 of the parse; extraction reads no header) |
| In the signature segment (trailing whitespace or newline included) | `signature` (step 1.7) | `signature` |
| In the payload segment, added after signing | `signature` (step 1.8 fails before step 1.9) | `shape` (extraction, [VERIFYKEYS-11](#verifykeys-11) step 2) |
| In the payload segment, covered by the signature | `shape` (step 1.9) | `shape` (extraction) |

(Vectors: `verifykeys.json`, `http.json`.)

<a id="verifykeys-31"></a>**VERIFYKEYS-31. Repeated claim names.** When the payload (or `verifyKeys`) repeats a member
name, the last occurrence is the claim's value and replaces the earlier ones whole, a later `null` counting as `null`
([Repeated member names: the last occurrence wins](#p-duplicates)). So `"nonce":0,"nonce":5` reads as 5, and
`"aud":"x","aud":"boostx"` reads as `"boostx"`. The lone-surrogate check still covers the replaced occurrence
([Ill-formed Unicode (lone surrogates)](#p-surrogates)). (Vectors: `verifykeys.json`.)

<a id="verifykeys-32"></a>**VERIFYKEYS-32. Unknown members are ignored.** A parser and the extractor MUST ignore every
payload member other than `iss`, `aud`, `iat`, `exp`, `nbf` and `verifyKeys`, and every member of `verifyKeys` other
than `nonce`, whatever its type. The builders write nothing else ([VERIFYKEYS-06](#verifykeys-06),
[VERIFYKEYS-07](#verifykeys-07)). (Vectors: `verifykeys.json`.)

Shared rules written elsewhere, with their verify-keys outcome (these ids are anchored at their primary rule):

| Rule | Primary | Verify-keys outcome |
|---|---|---|
| VERIFYKEYS-22: the header is a JSON object (`null` is not); `alg` is read under the exact key `alg` and must be the JSON string `"ES256"` | [KEYS-22](#keys-22) | not an object: `shape`; `alg` absent, a non-string, or any other value (an `ALG` member is not `alg`): `signature` |
| VERIFYKEYS-23: a header with a `crit` member, whatever its value, is refused; other members except `alg` are ignored | [KEYS-23](#keys-23) | `signature` |
| VERIFYKEYS-25: header and payload segments are canonical unpadded base64url | [KEYS-26](#keys-26) | `shape` |
| VERIFYKEYS-26: the signature segment is canonical unpadded base64url of exactly 64 bytes | [KEYS-31](#keys-31) | `signature`, as for a signature that does not verify |
| VERIFYKEYS-28: the verified payload is exactly one JSON object (`null`, an array, a string, a number or trailing data is not) | [KEYS-32](#keys-32) | `shape` |
| VERIFYKEYS-29: decoded header and payload are strict UTF-8 without a byte order mark | [KEYS-35](#keys-35) | `shape` |
| VERIFYKEYS-30: claim names `iss`, `aud`, `iat`, `exp`, `nbf`, `verifyKeys` and `verifyKeys.nonce` are matched exactly | [KEYS-34](#keys-34) | a differently spelled member is not the claim (`AUD` leaves `aud` absent: `iss-aud`; `NONCE` leaves the nonce absent: `nonce-format`) |
| Lone surrogate escape in the header or payload JSON text (decision [lone-surrogate ids](#decision-lone-surrogates)) | [KEYS-37](#keys-37), [Ill-formed Unicode (lone surrogates)](#p-surrogates) | `shape`, in extraction and parsing alike |

### 10.5 Claims

<a id="verifykeys-33"></a>**VERIFYKEYS-33. iss and aud are strings.** `iss` and `aud` MUST be JSON strings. Absent or
`null` reads as `""`, which then fails the `iss`/`aud` comparison (`iss-aud`; in extraction, an empty `aud` is
`shape`). A number, boolean, array or object is `shape`; an `aud` array is not accepted even when it holds the expected
value. (Vectors: `verifykeys.json`, `http.json`.)

<a id="verifykeys-36"></a>**VERIFYKEYS-36. Absent or null required claims.** Verify-keys has no missing-claim reason,
so an absent or `null` required claim reads as a zero value and fails the check that reads it ([Null versus
absent](#p-null-absent)): `iss` and `aud` read as `""` (`iss-aud`), `iat` reads as `0` and is `stale`, and
`verifyKeys` reads as `{}`, whose nonce is then absent (`nonce-format`). This mapping is specific to verify-keys:
Booster and CheckBet keep `missing_claim` for an absent claim and `invalid_claim` for a `null` one. `exp` and `nbf` are
the exception: absent means no limit and `null` is `shape` ([KEYS-42](#keys-42)). (Vectors: `verifykeys.json`,
`http.json`.)

<a id="verifykeys-41"></a>**VERIFYKEYS-41. The nonce range.** `verifyKeys.nonce` is a JSON number holding an integer
in `[1, 2147483647]` (the positive half of a signed 32-bit integer). Both bounds are valid; 0 is not. (Vectors:
`verifykeys.json`.)

<a id="verifykeys-42"></a>**VERIFYKEYS-42. Every nonce fault is nonce-format.** A parser MUST refuse with
`nonce-format` every `verifyKeys.nonce` that is not a JSON number whose binary64 value is integral and in
`[1, 2147483647]` ([Integer claims are judged by value](#p-integers)): absent, `null`, zero, negative, fractional,
above the range (`2147483648`, `1e100`, and `1e400`, which reads as +Infinity), or not a number (a string such as
`"5"`, a boolean, an array, an object). An absent or `null` `verifyKeys` reads as an empty object, so its nonce is
absent ([VERIFYKEYS-45](#verifykeys-45)); a `verifyKeys` that is present and not an object is `shape`
([VERIFYKEYS-44](#verifykeys-44)). The nonce is judged last ([VERIFYKEYS-46](#verifykeys-46) step 5), and the
extractor never judges it, so a request whose only fault is its nonce passes extraction and is refused by the parse.
(Vectors: `verifykeys.json`, `http.json`.)

<a id="verifykeys-44"></a>**VERIFYKEYS-44. verifyKeys must be an object.** A `verifyKeys` that is present and not
`null` MUST be a JSON object; an array, number, string or boolean is `shape`. (Vectors: `verifykeys.json`.)

<a id="verifykeys-45"></a>**VERIFYKEYS-45. A token without verifyKeys.** A verify-keys token must carry the
`verifyKeys` root member: that member is the domain separation from the other token types. A token with `iss`, `aud`
and `iat` but no `verifyKeys` (or `verifyKeys` `null`) passes the type checks and is refused as `nonce-format`. A
Booster or CheckBet token sent to `/verify-keys` fails earlier, at extraction, as `shape`, because it has no `aud`.
(Vectors: `verifykeys.json`, `http.json`.)

Shared rules written elsewhere: VERIFYKEYS-35 and VERIFYKEYS-43 are anchored at [INBOUND-35](#inbound-35), the one
integer-claim rule. Their verify-keys outcomes: `iat` must be a JSON number whose binary64 value is integral with
magnitude at most `2^53-1` (so `1793436254`, `1793436254.0` and `1793436254e0` are one value), else `shape`, and an
integral `iat` outside the window is `stale`; a nonce is judged by its binary64 value (`5`, `5.0` and `5e0` are the
nonce 5, the string `"5"` is not a number), else `nonce-format`.

### 10.6 Window, exp and nbf

<a id="verifykeys-37"></a>**VERIFYKEYS-37. Freshness.** With `now` the receiver's own clock in whole Unix seconds
(rounded down) and `W` the window in whole seconds, a token is fresh when `now - W <= iat <= now + W`: both ends
inclusive, in both directions. Otherwise it is `stale`. The comparison MUST NOT overflow or wrap around for any `iat`
that passed step 2 of [VERIFYKEYS-46](#verifykeys-46). BoostX applies the same check, with
`W` = 30, to the response (informative). (Vectors: `verifykeys.json`.)

<a id="verifykeys-39"></a>**VERIFYKEYS-39. An invalid window is refused first.** A parse function given an invalid
window (negative or non-finite, or not a number where the language can pass one) MUST fail with `invalid_claim`
before it reads the token, after the key and partner id checks ([VERIFYKEYS-46](#verifykeys-46) step A3). The reason
mapper reads that error as `shape` ([VERIFYKEYS-52](#verifykeys-52)).

Implementation-defined: the window's type follows the language (JS seconds as a number in an options object, Go a
`time.Duration`), as long as it carries fractions of a second ([KEYS-41](#keys-41)), and the error message names the
language's own parameter (`maxSkewSeconds`, `maxSkew`), so a vector does not compare `field` for this error. (Vectors:
`verifykeys.json`.)

Shared rules written elsewhere:

| Rule | Primary | Verify-keys content |
|---|---|---|
| VERIFYKEYS-38: the parse functions' window parameter | [KEYS-41](#keys-41) ([Verify-keys window](#p-window)) | absent, `null` or exactly 0 means 30 s; negative or non-finite is `invalid_claim`; any other value is truncated toward zero to whole seconds, so a positive value under 1 s gives a zero-second window |
| VERIFYKEYS-40: the handler window | [KEYS-41](#keys-41) | handlers always apply 30 s and take no window option; only the parse functions take one, for tests and hand-written handlers |
| VERIFYKEYS-47: `exp` and `nbf` | [KEYS-42](#keys-42) ([exp and nbf are enforced when present](#p-exp-nbf)) | optional, absent means no limit; present and not a JSON number (`null` included) is `shape`; `exp <= now` or `nbf > now` is `stale`, checked after the `iat` window, no leeway; a value beyond binary64 range reads as ±Infinity and is compared as that; SDKs never emit either |

### 10.7 Normative check order

<a id="verifykeys-46"></a>**VERIFYKEYS-46. Check order of the parse functions.** The request parser and the response
parser MUST run these checks in this order, and report the first that fails. Step numbers are stable and cited by the
vectors.

Arguments, before the token is read ([Check order is normative; configuration before input](#p-check-order)):

- **A1.** The verifying public key is usable, as far as it can be checked without verifying ([Key usability: never
  crash, refuse at startup](#p-key-usability), [KEYS-46](#keys-46)): else `invalid_public_key`
  ([VERIFYKEYS-50](#verifykeys-50)).
- **A2.** The partner id ([VERIFYKEYS-09](#verifykeys-09)): else `missing_claim` or `invalid_claim`.
- **A3.** The window ([KEYS-41](#keys-41)): absent, `null` or 0 selects 30 s; else `invalid_claim`
  ([VERIFYKEYS-39](#verifykeys-39)).

1. Format and signature:
   1. Exactly three `.`-separated segments: else `shape`.
   2. The header segment is canonical unpadded base64url: else `shape`.
   3. The header bytes are strict UTF-8 and do not begin with a byte order mark: else `shape`.
   4. The header text is exactly one JSON value, an object, with no lone surrogate escape: else `shape`.
   5. `alg` (exact key) is the JSON string `"ES256"`: else `signature`.
   6. The header has no `crit` member: else `signature`.
   7. The signature segment is canonical unpadded base64url of exactly 64 bytes: else `signature`.
   8. ECDSA P-256 with SHA-256 verifies the signature over the octets of the received `header.payload` text (ASCII
      for base64url segments, otherwise the text's UTF-8 octets, [KEYS-29](#keys-29)): else `signature`. (A key the
      platform refuses only here is `invalid_public_key`, [KEYS-67](#keys-67).)
   9. The payload segment is canonical unpadded base64url, its bytes strict UTF-8 without a byte order mark, its text
      exactly one JSON value, an object, with no lone surrogate escape: else `shape`.
2. Claim types, all `shape`: `iss` and `aud` are strings, `iat` is a JSON number with an integral binary64 value of
   magnitude at most `2^53-1`, `verifyKeys` is an object, and `exp` and `nbf`, when present, are numbers. Absent or
   `null` `iss`, `aud`, `iat` and `verifyKeys` take their zero values (`""`, `""`, `0`, `{}`); a present `null` `exp`
   or `nbf` is `shape`. The order inside this step is not observable.
3. `iss` and `aud` equal the expected pair exactly ([VERIFYKEYS-34](#verifykeys-34)): else `iss-aud`.
4. `|now - iat| <= W` ([VERIFYKEYS-37](#verifykeys-37)), then, when present, `exp > now` and `nbf <= now`: else
   `stale`.
5. `verifyKeys.nonce` is a JSON number whose binary64 value is integral and in `[1, 2147483647]`
   ([VERIFYKEYS-42](#verifykeys-42)): else `nonce-format`.

So a token with a wrong `iss` and a string nonce is `iss-aud`; a malformed header with a bad signature is `shape`; a
malformed payload with a bad signature is `signature`. In a handler the extractor runs first
([VERIFYKEYS-10](#verifykeys-10)): it applies step 1.1, step 1.9 and step 2 to the unverified token and refuses an
`aud` that is `""` or `"boostx"`, all as `shape` and before any key lookup, so a payload fault is `shape` there even
when the signature is also bad. On success the parser returns the result of [VERIFYKEYS-54](#verifykeys-54). (Vectors:
`verifykeys.json`, `keys.json`, `http.json`.)

### 10.8 Builders

<a id="verifykeys-48"></a>**VERIFYKEYS-48. The builders' nonce.** Both builders MUST refuse, with `invalid_claim`
naming the field `nonce` and before anything is signed, a nonce that is not an integral number in `[1, 2147483647]`:
0, negative, fractional, above the range, `NaN`, a non-number or an absent or `null` nonce ([Null versus
absent](#p-null-absent): an absent required number is `invalid_claim`). This check is what bounds the values the
partner private key signs for a caller; without it the endpoint is a signing oracle. Where the language's type already
bounds the value (Go's `int32`), only what the type admits is checked, and a runner skips inputs the type cannot carry.
(Vectors: `verifykeys.json`.)

<a id="verifykeys-49"></a>**VERIFYKEYS-49. The builders' key and check order.** Both builders MUST check, in order,
and report the first failure:

1. The private key is an ECDSA P-256 private key that can sign, as far as that can be checked without signing
   ([KEYS-19](#keys-19)): else `invalid_private_key`. A key the platform refuses only when signing is
   `invalid_private_key` at that point.
2. The partner id ([VERIFYKEYS-09](#verifykeys-09) items 1 and 2): `missing_claim` or `invalid_claim`.
3. The nonce ([VERIFYKEYS-48](#verifykeys-48)): `invalid_claim`.
4. The partner id is well-formed Unicode ([VERIFYKEYS-09](#verifykeys-09) item 3): `invalid_claim`.

(Vectors: `verifykeys.json`.)

<a id="verifykeys-69"></a>**VERIFYKEYS-69. The response token.** The response builder MUST emit a compact JWS whose
protected header has exactly the members `alg` `"ES256"` and `typ` `"JWT"`, with the payload of
[VERIFYKEYS-07](#verifykeys-07), signed with ES256 over `header.payload` and the signature encoded as the 64-byte
`r || s` in canonical unpadded base64url. BoostX ignores `typ` (informative).

Implementation-defined: member order, escaping, number spelling and whitespace ([Emitted bytes are not canonical, except
the GID payload](#p-emitted-bytes)); today both SDKs emit the same header text `{"alg":"ES256","typ":"JWT"}` and the
payload members in the order `verifyKeys`, `iss`, `aud`, `iat` (informative). (Vectors: `verifykeys.json`, and
`http.json` through the `responseJWT` check.)

### 10.9 Errors and reasons

<a id="verifykeys-50"></a>**VERIFYKEYS-50. An unusable verifying key is a key error.** A parse function given a
verifying key that is not usable MUST fail with `invalid_public_key`, checked before the partner id, the window and
the token ([VERIFYKEYS-46](#verifykeys-46) step A1). That error is not wrapped in `invalid_verify_keys` and carries no
reason; its category set is exactly `{invalid_public_key}`. The reason mapper reads it as `signature`
([KEYS-60](#keys-60)); the handlers answer it 500 and never map it ([VERIFYKEYS-15](#verifykeys-15)). (Vectors:
`verifykeys.json`.)

<a id="verifykeys-52"></a>**VERIFYKEYS-52. The reason mapper.** The reason mapper takes any error value and MUST
return, walking the cause chain ([Closed error taxonomy](#p-taxonomy): the language's standard walk, or at least 16
levels when written by hand):

1. `signature` when `invalid_signature` or `invalid_public_key` is anywhere in the chain;
2. otherwise the verify-keys reason the error carries (`iss-aud`, `stale`, `nonce-format`, or `shape`); an error the
   SDK raises carries at most one;
3. otherwise `shape`: for `missing_claim`, `invalid_claim`, an error from outside the SDK, and an absent error (`null`,
   `nil`).

The `invalid_public_key` row is [KEYS-60](#keys-60) (also VERIFYKEYS-51, anchored there): a key that cannot verify is
reported like a signature that does not, which Test integration reads as a wrong BoostX public key. (Vectors:
`verifykeys.json`, through `want.reason`.)

<a id="verifykeys-53"></a>**VERIFYKEYS-53. One failure category carrying the reason.** Every token failure of the
extractor and the parsers MUST carry the category `invalid_verify_keys` and exactly one reason, exposed as a property
or a sub-category (JS `BoostxError.reason`; Go the sentinels `ErrVerifyKeysShape`, `ErrVerifyKeysIssAud`,
`ErrVerifyKeysStale`, `ErrVerifyKeysNonce`, each wrapping `ErrInvalidVerifyKeys`). A `signature` failure also carries
`invalid_signature` in its chain, so it matches both the verify-keys category and the generic signature category; Go
has no reason sentinel for it. The category sets are therefore exactly:

| Outcome | Category set |
|---|---|
| `shape`, `iss-aud`, `stale`, `nonce-format` | `{invalid_verify_keys}` |
| `signature` | `{invalid_verify_keys, invalid_signature}` |
| unusable verifying key | `{invalid_public_key}` |
| partner id absent, empty or a non-string | `{missing_claim}` |
| partner id `"boostx"`, invalid window | `{invalid_claim}` |

Implementation-defined: message texts ([HTTP-60](#http-60)); JS writes `invalid verifyKeysJWT: <reason> (<detail>)`
and Go `invalid VerifyKeys token: …`. (Vectors: `verifykeys.json`.)

### 10.10 Results

<a id="verifykeys-54"></a>**VERIFYKEYS-54. What the parse functions return.** A verified request yields `partnerID` (its
`aud`), `nonce` and `iat`; a verified response yields `partnerID` (its `iss`), `nonce` and `iat`, `iat` in integer Unix
seconds as received ([iat is exposed, never age-checked by the SDK](#p-iat-exposed)). Likewise a verified Booster yields
`gid` (`partner`, `user`, `bet`, `signature`), `round`, `boost`, `final`, `jackpot` and `iat`, and a verified CheckBet
yields `gid` and `iat` (8.6, 8.7). Argument order, overloads and nesting follow each language's idiom (section 3.4, Key
position and Names):

| Field | JS (`VerifyKeysRequest`, `VerifyKeysResponse`) | Go (`tokens.VerifyKeysRequest`, `tokens.VerifyKeysResponse`) |
|---|---|---|
| partner id | `partnerID: string` | `PartnerID string` |
| nonce | `nonce: number` | `Nonce int32` |
| iat | `iat: number` | `IssuedAt int64`, from the embedded `tokens.RegisteredClaims` |

The extractor returns the partner id alone. Also covers: HTTP-65. (Vectors: `verifykeys.json`.)

### 10.11 Handler body and routing

<a id="verifykeys-55"></a>**VERIFYKEYS-55. Body outcomes.** For `/verify-keys`:

| Body | Answer |
|---|---|
| Not JSON, empty, a JSON array, string, number or boolean | `400 {"error":"invalid request body"}` |
| `verifyKeysJWT` present and neither a string nor `null` | `400 {"error":"invalid request body"}` |
| `null`, `{}`, or `verifyKeysJWT` absent or `null` | the empty token, then `400 {"error":"invalid verifyKeysJWT: shape"}` |
| Other members beside `verifyKeysJWT` | ignored |

The byte-level and size rules are [HTTP-07](#http-07) to [HTTP-11](#http-11): invalid UTF-8
anywhere in the body is a bad body, never replaced. (Vectors: `verifykeys.json`.)

<a id="verifykeys-56"></a>**VERIFYKEYS-56. The body is one strict JSON value.** The body rules of section 11.2
apply to `/verify-keys` unchanged: [HTTP-08](#http-08) to [HTTP-15](#http-15) ([P-body](#p-body), [P-utf8](#p-utf8)).
The token is read from the member named exactly `verifyKeysJWT` ([P-names](#p-names)): `VerifyKeysJWT` is another
member. An absent or `null` member, or a `null` body, reads as the empty token, answered
`400 {"error":"invalid verifyKeysJWT: shape"}`. Same rule as HTTP-09 and HTTP-10. (Vectors: `http.json`,
`verifykeys.json`.)

<a id="verifykeys-57"></a>**VERIFYKEYS-57. The body cap.** The 65536-byte body cap of [HTTP-07](#http-07) applies
to `/verify-keys` unchanged. Same rule as HTTP-07. (Vectors: `http.json`, `verifykeys.json`.)

<a id="verifykeys-58"></a>**VERIFYKEYS-58. Routing and methods.** The routing and method rules of section 11.1 apply
to `/verify-keys` unchanged ([P-routing](#p-routing)): [HTTP-01](#http-01) (the served path), [HTTP-02](#http-02)
(path details), [HTTP-03](#http-03) (405 with `Allow: POST`, checked by every per-endpoint HTTP handler, Go's
`NewVerifyKeysHandler` included) and [HTTP-04](#http-04) (404, the path checked before the method). BoostX's self-test
reads a 404 or 405 as a missing endpoint whatever the body ([HTTP-53](#http-53), informative). Same rule as HTTP-01 to
HTTP-04. (Vectors: `http.json`, `verifykeys.json`.)

<a id="verifykeys-59"></a>**VERIFYKEYS-59. Content types.** A handler MUST NOT check the request's `Content-Type`, and
MUST send every answer, success and refusal alike, with `Content-Type: application/json`. BoostX sends
`application/json` and parses any answer as JSON whatever its content type (informative).

Implementation-defined: media-type parameters and a trailing newline after the JSON body. (Vectors: `http.json`, whose
requests carry no JSON content type; the answer's `Content-Type` is not compared.)

<a id="verifykeys-60"></a>**VERIFYKEYS-60. Invalid handler configuration.** The construction rule is
[HTTP-48](#http-48). The `/verify-keys` unit needs only the key store's BoostX public key and partner private key roles
and no bet store ([HTTP-46](#http-46)): JS `handleVerifyKeys(body, { keyStore })` checks just those two methods, and
Go's `NewVerifyKeysHandler` needs only a key store. Same rule as HTTP-48. (Vectors: `http.json`, `verifykeys.json`, with
`at: "construct"`.)

<a id="verifykeys-61"></a>**VERIFYKEYS-61. Framework adapters.** The adapter rule is [HTTP-16](#http-16). Same rule
as HTTP-16. (No vector: language-specific.)

<a id="verifykeys-71"></a>**VERIFYKEYS-71. A repeated body member.** A body that repeats `verifyKeysJWT` is read with
its last occurrence, which replaces the earlier ones whole ([Repeated member names: the last occurrence
wins](#p-duplicates)): a valid token followed by `"bad"` is `400 invalid verifyKeysJWT: shape`, and a token followed
by `null` reads as the empty token. (Vectors: `verifykeys.json`.)

### 10.12 Test helpers and examples

<a id="verifykeys-67"></a>**VERIFYKEYS-67. The BoostX half is a test aid under SDK rules.** The request builder and
the response parser let a partner test offline. They MUST apply the SDK's own rules (format, signature, header, claim
types, `iss`/`aud`, window, `exp`/`nbf`, nonce, in the order of [VERIFYKEYS-46](#verifykeys-46)) and MUST NOT emulate
BoostX's parser. Those rules accept no response BoostX refuses: where they differ, they are stricter. So a response
the response parser accepts with the default window is one BoostX accepts at the same moment with the same keys.
(Vectors: `verifykeys.json`.)

<a id="verifykeys-68"></a>**VERIFYKEYS-68. The answer table, hand-written handlers included.** Every `/verify-keys`
handler an SDK ships or documents as an example MUST answer as [VERIFYKEYS-11](#verifykeys-11) to
[VERIFYKEYS-16](#verifykeys-16) say, with JSON bodies `{"error": "…"}`:

| Situation | Status | `error` |
|---|---|---|
| Unreadable body ([VERIFYKEYS-56](#verifykeys-56), [VERIFYKEYS-57](#verifykeys-57)) | 400 | `invalid request body` |
| Token refused by extraction or parse | 400 | `invalid verifyKeysJWT: <reason>` |
| Either lookup reports an unknown partner | 400 | `invalid verifyKeysJWT: iss-aud (unknown partner "<id>")` |
| Any other lookup failure, or a key that cannot verify or sign | 500 | the texts of [VERIFYKEYS-15](#verifykeys-15) |
| Success | 200 | none; the body is `{"result":{"responseJWT":"…"}}` |

An example MUST also keep the 65536-byte body cap, so a copied handler does not read an unbounded body. BoostX reads a
plain-text refusal as a malformed answer, and a 404 for an unknown partner as a missing endpoint (informative).
(Vectors: `http.json`, `verifykeys.json` for the SDK handler; examples are checked by their own tests.)

<a id="verifykeys-70"></a>**VERIFYKEYS-70. The nonce check in other languages.** A nonce check MUST accept a JSON number
with an integral value in `[1, 2147483647]`, whatever its spelling, and refuse booleans, strings and every other type.
Where a language's JSON decoder gives integers, floats and booleans distinct types, that means accepting an integral
float and refusing a boolean even where the language treats booleans as integers: in Python, `(type(x) is int or
(type(x) is float and x.is_integer())) and 1 <= x <= 2147483647`, since `isinstance(x, int)` also accepts `True`.
(Vectors: `verifykeys.json`.)

### 10.13 What the SDK sees from BoostX (informative)

<a id="verifykeys-62"></a>**VERIFYKEYS-62. The two probes.** Beside the real exchange, the self-test sends two requests
a partner must refuse: the invalid-signature probe, for the partner's own id but signed with a key that is not BoostX's,
and the foreign-id probe, signed by BoostX for an `aud` the partner does not serve. Each needs an answer outside 2xx.
SDK handlers answer the first `400 invalid verifyKeysJWT: signature`; an `aud` they do not serve gets
`400 invalid verifyKeysJWT: iss-aud (unknown partner "…")` ([VERIFYKEYS-13](#verifykeys-13)).

<a id="verifykeys-63"></a>**VERIFYKEYS-63. Stages.** The self-test reports its checks in a fixed order, listed with
their hints in the Stages section of the partner docs. Reporting stops at the first failure, which carries a hint, and
every later check reads `skipped` even if its request was answered.

<a id="verifykeys-64"></a>**VERIFYKEYS-64. How BoostX reads the response token.** BoostX reports a response token that
fails with `signature`, `iss-aud` or `stale` with that reason's hint, one that fails with `nonce-format` or `shape` as a
malformed response, and a nonce that differs from the one sent as a nonce mismatch. The `iss-aud` hint tells the partner
to write `iss` as the partner id it serves, taking the request's `aud` only after matching it against its own
configuration ([VERIFYKEYS-12](#verifykeys-12)).

<a id="verifykeys-65"></a>**VERIFYKEYS-65. Nonce echo.** BoostX compares the response nonce with the one it sent by
strict equality. The SDK side of this is step 6 of [VERIFYKEYS-11](#verifykeys-11): the handler signs the verified
request's nonce unchanged.

<a id="verifykeys-66"></a>**VERIFYKEYS-66. No nonce tracking.** Neither side tracks nonces: the ±30 s `iat` window is
the only replay defence, which keeps the endpoint stateless. The SDK side of this is
[VERIFYKEYS-03](#verifykeys-03).

Other BoostX facts the rules above rely on: BoostX never signs a request whose nonce is outside `[1, 2^31-1]`; the URL
is the API URL with one trailing `/` removed, followed by `/verify-keys`; the three requests start together, each a
single attempt. BoostX refuses `boostx` as a partner id.

## 11. HTTP handlers (HTTP)

This section defines the partner side of the three calls BoostX makes: `POST /set-boost`, `POST /check-bet` and
`POST /verify-keys`. It covers routing, the request body, the normative check order, the two store contracts and every
answer's status and body. The token rules themselves (JWS, claims, GID, verify-keys reasons) are in sections 5, 6, 8 and
10; this section says only in which order they run inside a handler and how their outcomes are answered.

Terms used below:

| Term | Meaning |
|------|---------|
| router | The SDK entry point that serves all three endpoints (JS `createFetchHandler(options)`, `createNodeHandler(options)`; Go `handlers.Mount(mux, prefix, betStore, keyStore)`) |
| per-endpoint unit | An SDK unit that answers one endpoint, either an HTTP handler (Go `handlers.NewSetBoostHandler`, `NewCheckBetHandler`, `NewVerifyKeysHandler`) or a function on a parsed body (JS `handleSetBoost`, `handleCheckBet`, `handleVerifyKeys`) |
| host router | The partner's own HTTP router, when it answers a request before the SDK sees it (Go's `http.ServeMux` under `Mount`) |
| bet store | The partner's bet records as the handlers reach them (JS `BetStore`; Go `handlers.BetStoreUpdater`, `handlers.BetStoreChecker`) |
| key store | The handlers' key lookups by partner ID (JS `HandlersKeyStore`; Go `handlers.KeyStore`, `handlers.PartnerPublicKeysStore`) |
| answer | The HTTP status and JSON body a handler writes |

<a id="http-73"></a>**HTTP-73. The conformance core.** The vectored rules of this section are checked through one
framework-neutral core, the router of [HTTP-66](#http-66) seen as a function:

```
handle(method, path, bodyBytes, cancel?) -> {status, headers, body}
```

`method` is the request method; `path` the request target as sent, the path with its query if any and no scheme or host;
`bodyBytes` the raw body, empty when there is none; and `cancel` the request's own cancellation, which the router passes
to the stores where the platform does ([HTTP-31](#http-31)), and which a platform that cancels by cancelling the task
does not have. The result is the answer's status, its headers and its body bytes. An SDK need not offer `handle` as
public API, and no public API has to change for it: its conformance runner MAY reach the core through an adapter of its
own over the router the SDK offers. JS `createFetchHandler`, from `Request` to `Response`, is the core in substance; a
Go runner calls `handlers.Mount` on a new `http.ServeMux` and serves the request into an `httptest.ResponseRecorder`.
Framework adapters stay optional ([HTTP-16](#http-16)). FORMAT.md section 6.7 says how the vectors drive the core.
(Vectors: `http.json`, through every `http.serve` case.)

### 11.1 Routing, methods, mounting and construction

<a id="http-01"></a>**HTTP-01. The served path.** BoostX calls each endpoint at the partner's API URL with one trailing
`/` removed, followed by `/set-boost`, `/check-bet` or `/verify-keys`. An SDK entry point MUST serve exactly that path
for each endpoint it serves. Same rule as [VERIFYKEYS-58](#verifykeys-58) for `/verify-keys`. Applies
[P-routing](#p-routing). (Vectors: `http.json`.)

Implementation-defined: what an entry point does with other paths that end in `/<name>`. A router that dispatches on the
last path segment serves them (JS `createFetchHandler`); one given a prefix answers them 404 (Go `Mount`, which
registers exact `<prefix>/<name>` patterns). The path is not a security boundary; the token is.

<a id="http-02"></a>**HTTP-02. Path details.** The endpoint name is matched exactly and case-sensitively, so
`/SET-BOOST` is not served. The query string is ignored. A path with a `/` after the name (`/set-boost/`) is not served
and is answered 404. (Vectors: `http.json`, `verifykeys.json`.)

Implementation-defined: percent-decoding of the path, and the handling of `//`, `.` and `..` segments, redirects
included. They follow the host router or the SDK's own dispatch: JS does not percent-decode and serves `/api//set-boost`
by its last segment; Go's `ServeMux` decodes `%2D` before matching and redirects an unclean path to the clean one with a
307. Partners are told to set an API URL without `//`, so BoostX's calls do not meet such a redirect.

<a id="http-03"></a>**HTTP-03. Method.** A request with any method other than `POST` to a served path MUST be answered
405 with the header `Allow: POST` and the body `{"error":"method not allowed"}`. Every per-endpoint HTTP handler MUST
check the method itself, also when the partner registers it on a router of their own (Go
`handlers.NewSetBoostHandler(store, keyStore)`, `NewCheckBetHandler`, `NewVerifyKeysHandler(keyStore)`). Where a host
router rejects the method before the SDK sees the request (the method patterns `Mount` registers on `ServeMux`), the
router's own 405 body is acceptable; the status and `Allow: POST` are still required. A function on a parsed body
([HTTP-61](#http-61)) never sees the method. `HEAD` is answered like any other method: 405 with `Allow: POST`; the
answer the core returns still holds the body, which an HTTP server then leaves out, as it does for every answer to
`HEAD` (RFC 9110 section 9.3.2), and `http-set-boost-head-not-allowed` compares no body. The method is compared exactly,
case-sensitively (methods are case-sensitive, RFC 9110 section 9.1), as the SDK receives it: `post` is not `POST`,
unless the platform normalised it before the SDK saw it, as the Fetch API's `Request` upper-cases `post` (no vector,
since that differs by platform). Applies [P-routing](#p-routing) and [P-http-errors](#p-http-errors). (Vectors:
`http.json`, `verifykeys.json`.)

<a id="http-04"></a>**HTTP-04. Unknown paths.** Where the SDK dispatches itself, a path it does not serve MUST be
answered 404 `{"error":"not found"}`, and the path check runs before the method check, so a `GET` on an unknown path is
404, not 405. Where a host router owns unknown paths (Go `Mount` on the partner's `ServeMux`), the router's 404 and its
body stand. (Vectors: `http.json`.)

<a id="http-05"></a>**HTTP-05. `/check-bet` only with a check.** `/check-bet` is served only when the bet store
implements the optional check (JS `BetStore.checkBet`; Go `handlers.BetStoreChecker`). Otherwise that path MUST be
answered 404, on every method and before the body is read, like an unknown path ([HTTP-04](#http-04)). Why: BoostX calls
`/check-bet` only when the partner switches it on, and then reads any non-2xx as no verdict ([HTTP-50](#http-50)), so a
store that cannot check never answers a guessed verdict. (Vectors: `http.json`.)

Implementation-defined: whether the SDK decides this once at construction (Go `Mount`) or per request (JS).

<a id="http-48"></a>**HTTP-48. Construction.** An entry point that is constructed (a router or a per-endpoint HTTP
handler) MUST refuse, at construction, configuration that cannot serve a request: a missing bet store or one without the
update method, and a missing key store or one without a lookup the entry point needs. It does so by exception
(`invalid_claim`) or by panic ([P-taxonomy](#p-taxonomy)). A stateless per-call function ([HTTP-61](#http-61)), which is
given its configuration on every call, MUST instead answer 500 `{"error":"internal server error"}` on every call while
its configuration is invalid. What each entry point needs: the router, a bet store with the update method and a key
store with all three lookups; the `/set-boost` unit, a bet store and a key store; the `/check-bet` unit, a bet store
with the check and a key store; the `/verify-keys` unit, only the key store ([HTTP-46](#http-46)). JS
`createFetchHandler` and `createNodeHandler` throw `invalid_claim`; Go `Mount` and the `New*Handler` constructors panic
on an untyped nil store. Same rule as [VERIFYKEYS-60](#verifykeys-60). (Vectors: `http.json`, `verifykeys.json`, a
construction error.)

Implementation-defined: whether a constructor refuses by raising `invalid_claim` or by a panic or abort, as the language
prefers. JS throws `invalid_claim`; Go panics, in `Mount`, the `New*Handler` constructors and the settlement client's
`client.New` alike ([SETTLE-35](#settle-35), [SETTLE-61](#settle-61), [HTTP-68](#http-68)).

Implementation-defined: which defects can be detected at construction depends on the type system. Go detects an untyped
nil and enforces method sets at compile time; a typed nil pointer passes construction and panics at request time, which
[HTTP-28](#http-28) places outside the contract.

<a id="http-66"></a>**HTTP-66. Entry points.** An SDK MUST offer one router that serves all three endpoints, in its
platform's idiom: JS `createFetchHandler(options)` for fetch-style servers and `createNodeHandler(options)` from the
`@boostxinnovation/partner-sdk/node` entry for `node:http` and Express; Go
`handlers.Mount(mux, prefix, betStore, keyStore)`, re-exported as `boostx.MountHandlers`. On a platform with no single
server interface (Python's WSGI and ASGI frameworks; Java, whose Servlet and Jakarta APIs are not part of the JDK and
stand beside the JDK's own `com.sun.net.httpserver` and each framework's handlers; PHP's PSR-15 middleware and plain
scripts), one function of the shape of the core of [HTTP-73](#http-73), taking the method, the path, the body bytes
and, where the platform passes one, the request's cancellation ([HTTP-31](#http-31)), and returning the status, the
headers and the body, is a router in the platform's idiom; adapters to particular frameworks or server interfaces
stay optional ([HTTP-16](#http-16)), and the caller then reads the body as [HTTP-07](#http-07) says. Such a function is
built from the stores, returned by a factory or bound to a router object made from them (as JS
`createFetchHandler(options)` returns its handler), and building it is the construction of [HTTP-48](#http-48):
configuration that cannot serve a request is refused there, as the `at: "construct"` cases expect, never answered 500
call by call, which HTTP-48 asks only of a function on a parsed body ([HTTP-61](#http-61)). It MUST also offer a
unit per endpoint for routers other than its own, in one of two forms: an HTTP handler, which then follows every rule of
this section including the method check (Go `handlers.NewSetBoostHandler`, `NewCheckBetHandler`, `NewVerifyKeysHandler`;
where the router is the core-shaped function above, the same function built for one endpoint, taking the method and the
body bytes but no path), or a function on a parsed body ([HTTP-61](#http-61); JS `handleSetBoost(body, options)`,
`handleCheckBet`, `handleVerifyKeys`). The SDK's documentation MUST warn that a store wrapper that does not forward the
optional check makes `/check-bet` answer 404 ([HTTP-05](#http-05)), which with check-bet switched on refuses every
round.

Implementation-defined: the router's form in the platform's idiom (a fetch-style handler, a mount on the platform's
multiplexer, or the core-shaped function above) and which of the two per-endpoint forms the SDK offers. (Vectors:
`http.json`, for the router.)

<a id="http-68"></a>**HTTP-68. Mount prefix.** An entry point that takes a prefix removes one trailing `/` from it and
then accepts only an empty prefix or a clean path: it starts with `/`, has no empty, `.` or `..` segment (path cleaning
returns it unchanged), and contains no character the host router treats as pattern syntax (for `ServeMux`: `{`, `}`,
space and tab; a router that matches the path literally has none). The prefix is matched literally. Any other prefix
MUST be refused at construction with a clear error (`invalid_claim`, or a panic where the language prefers,
[HTTP-48](#http-48)); Go `Mount` panics. So every entry point that takes a prefix accepts the empty prefix, `/`, `/api`,
`/api/` and `/a/b`, and refuses `api`, `/api//v1`, `/api/./v1` and `/api/../v1`. An entry point that takes no prefix has
nothing to validate: JS dispatches on the last path segment, and so may a bare function of the shape of
[HTTP-73](#http-73) ([HTTP-66](#http-66)). Why: `ServeMux` reads a prefix without a leading `/` as a host name, `{x}` as
a wildcard, and refuses an unclean pattern only when it is registered; an early, named error beats a route that silently
never matches. (Vectors: `http.json`, for the accepted prefixes; JS takes no prefix, so a refused prefix is tested by
each SDK's own suite, with the refused examples above.)

Implementation-defined: further characters a prefix can never match in the SDK's own dispatch, which it MAY also refuse
at construction, such as `?` and `#` for a router that strips the query and does not percent-decode the path before
matching. Go accepts both, since `ServeMux` decodes `%3F` and `%23` in a request path and so can match them.

Implementation-defined: whether an entry point that takes a prefix requires one or defaults to the empty prefix, the
root (Go's `Mount` takes it as an argument, which may be empty; a default of the root is as valid).

### 11.2 Request body

These rules apply to every SDK unit that reads the raw body ([P-body](#p-body)). Every failure is answered 400
`{"error":"invalid request body"}`, so the order of the checks below is not observable. Same rules as
[VERIFYKEYS-56](#verifykeys-56) and [VERIFYKEYS-57](#verifykeys-57) for `/verify-keys`.

<a id="http-06"></a>**HTTP-06. Content-Type is not checked.** An SDK MUST NOT refuse a request for its `Content-Type` or
for the lack of one; the body is read as JSON whatever the header says. BoostX sends `application/json`. (Vectors:
`http.json`, whose requests carry no JSON content type.)

<a id="http-07"></a>**HTTP-07. Body cap.** An SDK reads at most 65536 bytes of the body, counted over every byte
received: whitespace and anything after the JSON value count. A body of 65536 bytes is read; a longer one MUST be
answered 400 `{"error":"invalid request body"}`, whatever its first 65536 bytes hold, and the SDK SHOULD stop reading
once the count passes the cap. A router that receives the body already read (the function of [HTTP-66](#http-66) that
takes the body bytes) counts the bytes it is given and answers more than 65536 with this 400; the reading, and so the
stop the SHOULD asks for, are then the caller's: reading at most 65537 bytes is enough for the router to tell an
over-cap body. (Vectors: `http.json`, `verifykeys.json`.)

Implementation-defined: what happens to the rest of the body and to the connection. Go's `net/http` closes the
connection after the 400; JS `createFetchHandler` cancels the stream; JS `createNodeHandler` discards the rest so the
connection stays usable.

<a id="http-08"></a>**HTTP-08. An object or null.** The value MUST be an object or `null`. An array, string, number or
boolean is answered 400 `{"error":"invalid request body"}`. A `null` body reads as an object with no token member
([HTTP-13](#http-13)), the one exception [P-one-value](#p-one-value) names. (Vectors: `http.json`.)

<a id="http-09"></a>**HTTP-09. One JSON value.** The body MUST be exactly one JSON value, optionally surrounded by JSON
whitespace (space, tab, LF, CR). An empty body, whitespace alone, text that is not JSON, and anything after the value
(`{…} x`, `{…}{}`) are answered 400 `{"error":"invalid request body"}`. Applies [P-one-value](#p-one-value), whose depth
floor means a body nested 64 levels deep or less is read like any other (decision
[JSON nesting depth](#decision-json-depth)). (Vectors: `http.json`.)

<a id="http-10"></a>**HTTP-10. No byte order mark.** A body that begins with the bytes EF BB BF MUST be answered 400
`{"error":"invalid request body"}`. Applies [P-utf8](#p-utf8). (Vectors: `http.json`.)

<a id="http-11"></a>**HTTP-11. Strict UTF-8.** A body that is not well-formed UTF-8 ([P-utf8](#p-utf8): no overlong
form, no encoded surrogate, nothing above U+10FFFF) MUST be answered 400 `{"error":"invalid request body"}`. Invalid
bytes are never replaced with U+FFFD. (Vectors: `http.json`.)

<a id="http-12"></a>**HTTP-12. The token member.** The token MUST be read from the member named exactly, code unit for
code unit after JSON unescaping, `boosterJWT` on `/set-boost`, `checkbetJWT` on `/check-bet` and `verifyKeysJWT` on
`/verify-keys`. A member whose name differs in any way, letter case included, is an unknown member
([HTTP-15](#http-15)). When the name repeats, the last occurrence is the member ([P-duplicates](#p-duplicates); the
verify-keys case is [VERIFYKEYS-71](#verifykeys-71)). Applies [P-names](#p-names). Primary rule for claim names inside
the token: [KEYS-34](#keys-34). (Vectors: `http.json`, `inbound.json`, `verifykeys.json`.)

<a id="http-13"></a>**HTTP-13. The empty token.** A `null` body, an absent token member and a `null` token member all
read as the empty token `""` ([P-null-absent](#p-null-absent)). The SDK does not refuse it at the body step; extraction
refuses it, so the answer is 400 `{"error":"invalid booster token"}`, `{"error":"invalid checkbet token"}` or
`{"error":"invalid verifyKeysJWT: shape"}`. (Vectors: `http.json`.)

<a id="http-14"></a>**HTTP-14. Token type.** A token member that is present with any value other than a string or `null`
MUST be answered 400 `{"error":"invalid request body"}`. (Vectors: `http.json`.)

<a id="http-15"></a>**HTTP-15. Unknown members.** Members other than the token member MUST be ignored, whatever their
name, type or value, as long as the body passes [HTTP-07](#http-07) to [HTTP-09](#http-09). A lone-surrogate escape
(`"\ud800"`) in such a member is valid JSON and no body fault: [P-surrogates](#p-surrogates) governs a token's own
header and payload texts, not the request body. (Vectors: `http.json`.)

<a id="http-16"></a>**HTTP-16. Framework adapters.** An SDK reads the raw body itself wherever its platform lets it, and
[HTTP-06](#http-06) to [HTTP-15](#http-15) then apply in full. An adapter for a framework that has already consumed the
body works from what the framework hands it and applies the checks it still can: at least the 65536-byte cap on what it
measures, and 400 `{"error":"invalid request body"}` when nothing was left for it. Checks the framework's parser already
made are not repeated, so the result follows that parser where it differs from [HTTP-08](#http-08) to
[HTTP-11](#http-11). An adapter still answers 404 and 405 by the routing rules. JS `createNodeHandler` reads the stream
unless it has ended; then it uses `req.body` (bytes and strings as they are, `undefined` as an empty body, any other
value serialised with `JSON.stringify`), and answers every method other than `POST` as the router does (404 or 405). Go
has no adapter (`net/http` only). Optional for a third SDK (section 3.2). Same rule as [VERIFYKEYS-61](#verifykeys-61).
(Vectors: none; the adapters sit outside `http.serve`.)

<a id="keys-43"></a>**KEYS-43. No token length limit.** Parsers and extractors MUST NOT refuse a token for its length
alone. The handlers' 65536-byte body cap ([HTTP-07](#http-07)) is the only size limit. (Vectors: none; a long valid
token is not a useful case.)

### 11.3 Answers

<a id="http-17"></a>**HTTP-17. Headers and bytes.** Every answer the SDK writes MUST carry
`Content-Type: application/json`; a 405 also carries `Allow: POST`. The body is any valid JSON serialisation of the
envelope. (Vectors: `http.json`, for `Allow: POST` on a 405; the cases compare parsed bodies, never bytes, and do not
compare `Content-Type`.)

Implementation-defined: whitespace, a trailing newline, member order and optional escapes such as `<`, `>`, `&`, U+2028
and U+2029 ([P-emitted-bytes](#p-emitted-bytes)). Go's encoder escapes the HTML characters and adds a newline; JS writes
them raw. BoostX parses every answer as JSON.

<a id="http-18"></a>**HTTP-18. The envelope.** Every answer the SDK writes MUST be a JSON object with exactly one
member: `result` on success, always with status 200, and `error`, a string, on refusal. No other top-level member is
written. (Vectors: `http.json`.)

<a id="http-19"></a>**HTTP-19. `/set-boost` success.** When the bet store accepts the round (resolves, or returns no
error), a replay included, the answer MUST be 200 `{"result":{"ok":true}}`, with `ok` the JSON `true`. (Vectors:
`http.json`.)

<a id="http-32"></a>**HTTP-32. `/check-bet` success.** The answer to a check the store answered MUST be 200
`{"result":{"active":<verdict>}}`, where the verdict is the store's boolean, unchanged. (Vectors: `http.json`.)

<a id="http-35"></a>**HTTP-35. `/verify-keys` success.** The answer MUST be 200 `{"result":{"responseJWT":"<token>"}}`.
The token is a verify-keys response token (section 10.8): header members exactly `alg` `"ES256"` and `typ` `"JWT"`;
payload `verifyKeys.nonce` the request's nonce ([HTTP-44](#http-44)), `iss` the matched partner ID
([HTTP-36](#http-36)), `aud` `"boostx"` and `iat` the current time in whole Unix seconds; signed with the partner
private key. Member order and bytes are free ([HTTP-70](#http-70), [KEYS-61](#keys-61)). (Vectors: `http.json`.)

**The complete answer list.** An SDK MUST NOT answer with a status or an error text outside this table. The wording is
normative ([P-http-errors](#p-http-errors)); in the rows that echo a partner ID, the ID stands between double quotes and
its inner escaping is implementation-defined ([HTTP-24](#http-24)), and the parenthetical of the verify-keys
unknown-partner row is diagnostic. The only exceptions are a host router's own 404 and 405 bodies ([HTTP-03](#http-03),
[HTTP-04](#http-04)) and its redirect of an unclean path ([HTTP-02](#http-02)). An SDK never answers 502, 503, 504 or
525, which BoostX would retry ([HTTP-51](#http-51)).

| Status | `error` | Endpoints | When | Rule |
|--------|---------|-----------|------|------|
| 200 | none: `{"result":{"ok":true}}` | set-boost | The store accepted the round | [HTTP-19](#http-19) |
| 200 | none: `{"result":{"active":…}}` | check-bet | The store gave a verdict | [HTTP-32](#http-32) |
| 200 | none: `{"result":{"responseJWT":…}}` | verify-keys | The request verified and the response was signed | [HTTP-35](#http-35) |
| 400 | `invalid request body` | all | The body fails 11.2 | [HTTP-07](#http-07) to [HTTP-14](#http-14) |
| 400 | `invalid booster token` | set-boost | Extraction or parsing refuses the token | [HTTP-22](#http-22) |
| 400 | `invalid checkbet token` | check-bet | Extraction or parsing refuses the token | [HTTP-22](#http-22) |
| 400 | `unknown partner "<id>"` | set-boost, check-bet | A key lookup raised `unknown_partner` | [HTTP-24](#http-24) |
| 400 | `round rejected` | set-boost | The store raised the round-rejected marker | [HTTP-27](#http-27) |
| 400 | `invalid verifyKeysJWT: <reason>` | verify-keys | Extraction (`shape`) or parsing refuses the request | [HTTP-37](#http-37), [HTTP-42](#http-42) |
| 400 | `invalid verifyKeysJWT: iss-aud (unknown partner "<id>")` | verify-keys | A key lookup raised `unknown_partner` | [HTTP-38](#http-38) |
| 404 | `not found` | all | An unknown path; `/check-bet` without a check | [HTTP-04](#http-04), [HTTP-05](#http-05) |
| 405 | `method not allowed` | all | Not `POST`; with `Allow: POST` | [HTTP-03](#http-03) |
| 500 | `failed to get boostx key` | all | The BoostX-key lookup failed otherwise | [HTTP-25](#http-25), [HTTP-39](#http-39) |
| 500 | `failed to get partner key` | set-boost, check-bet | The partner-public-keys lookup failed otherwise | [HTTP-25](#http-25) |
| 500 | `failed to get partner private key` | verify-keys | The partner-private-key lookup failed otherwise | [HTTP-39](#http-39) |
| 500 | `failed to verify token` | all | No key the store returned can verify | [HTTP-26](#http-26), [HTTP-39](#http-39) |
| 500 | `failed to set boost` | set-boost | The store failed with anything but the marker | [HTTP-27](#http-27) |
| 500 | `failed to check bet` | check-bet | The store failed, or its verdict is not a boolean | [HTTP-33](#http-33), [HTTP-34](#http-34) |
| 500 | `failed to sign response` | verify-keys | The response could not be signed | [HTTP-39](#http-39) |
| 500 | `internal server error` | all | A per-call function's configuration is invalid; any other fault the SDK catches | [HTTP-48](#http-48), [HTTP-28](#http-28) |

### 11.4 Normative pipeline

<a id="http-20"></a>**HTTP-20. Verification is always on.** The handlers MUST verify the BoostX signature on the token
and, on `/set-boost` and `/check-bet`, the GID signature against the partner public keys, before the bet store is
called. An SDK MUST NOT offer an option that skips either. (Vectors: `http.json`.)

<a id="http-21"></a>**HTTP-21. Check order.** A handler runs these steps in order, and the first failing step decides
the answer, so an input with several faults has exactly one defined answer ([P-check-order](#p-check-order)). Same steps
for `/set-boost` and `/check-bet`:

1. **Route.** An unknown path, or `/check-bet` without a check, is 404 ([HTTP-04](#http-04), [HTTP-05](#http-05)); then
   a method other than `POST` is 405 ([HTTP-03](#http-03)).
2. **Body.** Read the body and take the token (11.2). A failure is 400 `invalid request body`.
3. **Unverified extraction.** Run the payload format rules and the full claim routine on the unverified payload and take
   `gid.partner` ([INBOUND-21](#inbound-21), [P-extraction](#p-extraction)). A failure is 400 `invalid booster token` or
   `invalid checkbet token`, and no key-store method is called.
4. **Key lookups.** Look up the BoostX public key and the partner public keys for that partner ID, concurrently or one
   after the other ([KEYS-52](#keys-52)). When both fail, the BoostX-key outcome decides. `unknown_partner` is 400
   `unknown partner "<id>"` ([HTTP-24](#http-24)); any other failure is 500 `failed to get boostx key` or
   `failed to get partner key` ([HTTP-25](#http-25)).
5. **Parse.** Check the keys first, the BoostX key and then the partner list (500 `failed to verify token` when no key
   can verify, [HTTP-26](#http-26)), then the JWS, the claims and the GID ([INBOUND-32](#inbound-32)). A token failure
   is 400 `invalid booster token` or `invalid checkbet token` ([HTTP-22](#http-22)).
6. **Bet store.** Call the store with the verified result (11.6), and answer 200 ([HTTP-19](#http-19),
   [HTTP-32](#http-32)) or the store failure's answer.

For `/verify-keys`:

1. **Route**, as above.
2. **Body**, as above.
3. **Unverified extraction** of `aud` ([HTTP-37](#http-37)). A failure is 400 `invalid verifyKeysJWT: shape`, and no
   key-store method is called.
4. **BoostX-key lookup.** `unknown_partner` is the 400 of [HTTP-38](#http-38); any other failure is 500
   `failed to get boostx key`.
5. **Parse** under [VERIFYKEYS-46](#verifykeys-46) with the fixed window ([HTTP-43](#http-43)). An absent or unusable
   BoostX key is 500 `failed to verify token`; any token failure is 400 `invalid verifyKeysJWT: <reason>`
   ([HTTP-42](#http-42)).
6. **Partner-private-key lookup.** `unknown_partner` is the 400 of [HTTP-38](#http-38); any other failure is 500
   `failed to get partner private key`.
7. **Sign** the response ([HTTP-35](#http-35)). A failure is 500 `failed to sign response`.

(Vectors: `http.json`, `keys.json`.)

Implementation-defined: the scheduling of the two lookups in step 4 of the first list, and so whether the second lookup
runs after the first has failed ([KEYS-52](#keys-52)). The key-store contract therefore includes concurrent calls, and
calls made after another lookup has failed.

<a id="http-22"></a>**HTTP-22. Token faults.** On `/set-boost` and `/check-bet`, every extraction failure, and every
parse failure that carries the token's category (`invalid_booster`, `invalid_checkbet`), MUST be answered 400
`{"error":"invalid booster token"}` or `{"error":"invalid checkbet token"}`. An unusable verifying key is never a token
fault: it is `invalid_public_key`, never wrapped in the token's category ([HTTP-56](#http-56)), and is answered 500
([HTTP-26](#http-26)). (Vectors: `http.json`.)

<a id="http-23"></a>**HTTP-23. Claim gates, as a handler sees them.** A Booster MUST carry `round`, an integral value
from 1 to 2^53−1; `boost`, a finite number greater than 0; and `final` and `jackpot`, JSON booleans (`null` refused).
Booster and CheckBet MUST carry `iat`, an integral value whose magnitude is at most 2^53−1. Values are judged by value,
not spelling, so `100`, `100.0` and `1e2` are equal ([P-integers](#p-integers)). An absent claim is `missing_claim`;
`null` or a wrong type is `invalid_claim` ([P-null-absent](#p-null-absent)); `exp` and `nbf` follow
[P-exp-nbf](#p-exp-nbf). In a handler these gates run at extraction (step 3 of [HTTP-21](#http-21)), so a failing token
is answered 400 `{"error":"invalid booster token"}` or `{"error":"invalid checkbet token"}` before any key-store call,
and nothing reaches the store. Also covers [INBOUND-33](#inbound-33), [INBOUND-34](#inbound-34),
[INBOUND-36](#inbound-36), [INBOUND-37](#inbound-37), [INBOUND-39](#inbound-39), where the claim rules are written in
full. Why the `boost` gate matters: a lenient reader hands a `null` boost to the store as 0. BoostX never signs a
Booster whose boost is not finite and positive (decision [minimum stake 0.01](#decision-minimum-stake)); the gate keeps
the store safe regardless. (Vectors: `http.json`, `inbound.json`.)

### 11.5 Key-store answers

<a id="http-69"></a>**HTTP-69. Signalling an unknown partner.** The key-store contract names one SDK error that a store
raises for a partner ID it does not serve: `unknown_partner` (JS a `BoostxError` with the code `unknown_partner`; Go an
error that wraps `keys.ErrUnknownPartner`, re-exported as `boostx.ErrUnknownPartner`). A handler MUST recognise it
anywhere in the error's cause chain ([P-taxonomy](#p-taxonomy): JS walks `cause` 16 levels, Go uses `errors.Is`, which
includes `errors.Join`). Any other key-store error is answered 500 ([HTTP-25](#http-25)). A store matches the ID byte
for byte and never falls back to a fixed key set; the SDK's documentation MUST say both. (Vectors: `http.json`.)

Implementation-defined: whether the walk enters a container of several errors, such as Go's `errors.Join`, Python's
`ExceptionGroup` (from `asyncio.TaskGroup`, for example) or JS's `AggregateError`. Go's `errors.Is` enters
`errors.Join`; JS walks `cause` alone and does not enter an `AggregateError`; Python's `__cause__` chain does not enter
an `ExceptionGroup`, and a Python SDK may stop there or also search the group's members. Where the walk does not enter
it, a store's `unknown_partner` inside such a container is answered 500, as any other store error; the same holds for
the round rejection of [HTTP-27](#http-27). No vector builds such a container. A store that wants its answer the same
in every SDK raises `unknown_partner` itself, or chains it through the cause.

<a id="http-24"></a>**HTTP-24. Unknown partner on `/set-boost` and `/check-bet`.** When either lookup raises
`unknown_partner`, the answer MUST be 400 `{"error":"unknown partner <ID>"}`, where `<ID>` is the extracted partner ID
written between double quotes. The wording is normative ([P-http-errors](#p-http-errors)). Primary rule
[KEYS-51](#keys-51); also covers [GID-44](#gid-44) and [INBOUND-57](#inbound-57). (Vectors: `http.json`, `gidgp.json`,
by prefix.)

Implementation-defined: how characters inside the ID are escaped. JS quotes with `JSON.stringify`, Go with `%q`; they
differ only for characters such as C0 controls, DEL and U+2028, which no real partner ID contains. Nobody parses the ID:
BoostX reads only the status of a non-2xx.

<a id="http-25"></a>**HTTP-25. Other lookup failures.** A key-store lookup that fails with anything but
`unknown_partner` MUST be answered 500 with the text for that lookup: `failed to get boostx key` or
`failed to get partner key` on `/set-boost` and `/check-bet`, and `failed to get boostx key` or
`failed to get partner private key` on `/verify-keys` ([HTTP-39](#http-39)). An in-memory store's lookup of a role it
was not given fails with that role's invalid-key error ([HTTP-58](#http-58)) and is answered here. A lookup that
succeeds without a usable key is not a lookup failure: parsing refuses it ([HTTP-26](#http-26)). (Vectors: `http.json`.)

<a id="http-26"></a>**HTTP-26. Keys that cannot verify.** When no key the store returned can verify, the answer MUST be
500 `{"error":"failed to verify token"}`. That is the case when the BoostX key is absent or unusable, or when the
partner key list is empty or holds no usable key; unusable keys in a partner list are skipped
([P-key-usability](#p-key-usability)). Parsing checks the keys before the token, the BoostX key first
([KEYS-46](#keys-46), the primary rule; also covers [GID-25](#gid-25), [INBOUND-31](#inbound-31)). In a handler, a token
that unverified extraction refuses has already been answered 400 before any lookup ([HTTP-21](#http-21)). (Vectors:
`http.json`, `keys.json`, `inbound.json`, `verifykeys.json`.)

<a id="http-64"></a>**HTTP-64. Partner public keys as a list.** The handlers' key store returns a partner's public keys
as a list, the current key first (JS `HandlersKeyStore.partnerPublicKeys(partner)`; Go
`handlers.PartnerPublicKeysStore.PartnerPublicKeys(ctx, partner)`), and a single-key store returns a one-element list.
GID verification tries each key and skips unusable ones. Go keeps a compatibility exception: `handlers.KeyStore` still
declares the single-key `PartnerPublicKey(ctx, partner)`, which the handlers use as a one-element list when the store
does not implement `PartnerPublicKeysStore`; a Go store that wraps another has to forward `PartnerPublicKeys`, and the
SDK's documentation says so. A new SDK's key store MUST return the list; the single-key lookup exists only as Go's
compatibility exception. Why: after a partner key rotation, games started earlier carry a GID signed with the earlier
key, and they keep verifying only if that key stays listed. (Vectors: `http.json`.)

### 11.6 Bet store

<a id="http-27"></a>**HTTP-27. Round rejection.** When the bet store's error is the round-rejected marker (JS
`RoundRejectedError`; Go `handlers.ErrRoundRejected`, re-exported as `boostx.ErrRoundRejected`), or wraps it anywhere in
its cause chain, the answer MUST be 400 `{"error":"round rejected"}` with that fixed text; the error's own message is
never sent. The cause chain is the language's explicit wrapping: `errors.Is` in Go (`errors.Join` included), `cause` in
JS and Java, `InnerException` in C#, `__cause__` in Python (not `__context__`), walked at least 16 levels where the walk
is written by hand. Any other store error MUST be answered 500 `{"error":"failed to set boost"}`. The marker is an input
the store raises, not an SDK error category ([HTTP-54](#http-54)). Why the fixed text: it keeps store text off the wire,
and BoostX ignores the body anyway: both statuses void the round and neither is retried. (Vectors: `http.json`.)

<a id="http-28"></a>**HTTP-28. Failures through the error channel.** A failure that a store or key store reports through
the language's normal error channel (a returned error, a thrown exception, a rejected promise) MUST be answered: with
the step's 500, or with the 400 of [HTTP-24](#http-24) or [HTTP-27](#http-27). A handler never fails without answering
for such a failure, and SHOULD answer 500 `{"error":"internal server error"}` for any other fault it catches. A Go panic
is a programming fault outside the contract and is left to `net/http`, which closes the connection without an answer.
Why both are safe: BoostX retries a connection that ends without an answer on `/check-bet` and `/set-boost` with the
same token, and a store that follows [HTTP-29](#http-29) heals a voided round on the replay. (Vectors: `http.json`, for
the error channel; a panic is not a case.)

<a id="http-29"></a>**HTTP-29. Replays reach the store.** The SDK MUST NOT filter, deduplicate or track rounds: every
verified Booster reaches the bet store, repeated and older rounds included. The store contract requires idempotence: a
round at or below the stored one changes nothing and succeeds, so it is answered 200 `{"result":{"ok":true}}`. The SDK's
documentation MUST state this. Why: BoostX re-sends a round after a lost answer or a voided round, and a store that
answers such a replay 400 wedges the bet. (Vectors: `http.json`, an early round that reaches the store; idempotence
belongs to the partner's store.)

<a id="http-31"></a>**HTTP-31. Request cancellation.** Where the platform's request carries a cancellation handle that
store APIs conventionally take (Go's `context.Context`, from `r.Context()`), the SDK MUST pass it to every bet-store and
key-store call. Otherwise this is not required, and JS passes none. Where the platform cancels a request by
cancelling the task that runs it (Python's asyncio), there is no handle to pass: the store call the task awaits is
cancelled with it, which meets this rule, and the router takes no cancellation argument. The handlers set no timeout
of their own ([P-cancellation](#p-cancellation), [HTTP-52](#http-52)). (Vectors: none; not observable through
`http.serve`.)

<a id="http-33"></a>**HTTP-33. The verdict is a boolean.** The store contract makes the check verdict a boolean. An SDK
whose language lets a store return anything else MUST answer any other value 500 `{"error":"failed to check bet"}`,
never forwarding or coercing it. JS does so; Go's `CheckBet` returns a `bool`, so the case cannot arise. Why: only a
boolean is a verdict; a 500 is read as no verdict ([HTTP-50](#http-50)), where a forwarded value of another type could
be read as one. (Vectors: `http.json` where the store type can express it; a typed runner skips the case.)

<a id="http-34"></a>**HTTP-34. Check failures.** A store whose check fails MUST be answered 500
`{"error":"failed to check bet"}`. The store contract says a bet the partner does not know is answered `false`, not an
error, and the SDK's documentation says so. (Vectors: `http.json`.)

### 11.7 iat

<a id="http-30"></a>**HTTP-30. iat reaches the store.** The verified Booster handed to the store and the verified
CheckBet MUST carry `iat` as received, in Unix seconds (JS `Booster.iat`, `CheckBet.iat`; Go `Booster.IssuedAt`,
`CheckBet.IssuedAt`). The SDK MUST NOT apply an age check ([P-iat-exposed](#p-iat-exposed)). A store that checks the age
must allow for retries, which re-send the same token. Primary rule [KEYS-39](#keys-39); also covers
[INBOUND-41](#inbound-41), [INBOUND-42](#inbound-42). (Vectors: `http.json`.)

### 11.8 The verify-keys endpoint

<a id="http-36"></a>**HTTP-36. The response `iss` is the matched ID.** The handler MUST sign the response with the
partner ID that extraction read from `aud`, and only after the key store has served both of its lookups for that exact
ID. Since a key store matches IDs byte for byte ([HTTP-69](#http-69)), the signed `iss` is the configured ID the
request's `aud` matched, and the SDK never signs for an `aud` it has not matched. Primary rule
[VERIFYKEYS-12](#verifykeys-12). (Vectors: `http.json`, `verifykeys.json`.)

<a id="http-37"></a>**HTTP-37. Extraction failures.** A request whose unverified payload fails the format rules or the
claim-type checks, or whose `aud` is absent, `null`, empty or `"boostx"`, MUST be answered 400
`{"error":"invalid verifyKeysJWT: shape"}` before any key-store call. What extraction checks is
[VERIFYKEYS-46](#verifykeys-46)'s extraction step. (Vectors: `http.json`.)

<a id="http-38"></a>**HTTP-38. Unknown partner on `/verify-keys`.** When either lookup raises `unknown_partner`, the
answer MUST be 400 `{"error":"invalid verifyKeysJWT: iss-aud (unknown partner <ID>)"}`. Everything up to and including
the reason `iss-aud` is normative. Primary rule [VERIFYKEYS-14](#verifykeys-14). Why `iss-aud`: BoostX's self-test then
reports the partner-ID configuration rather than the keys, and its foreign-ID probe passes.
(Vectors: `http.json`, `verifykeys.json`, by prefix.)

Implementation-defined: the parenthetical is diagnostic text, and the escaping of `<ID>` inside it is free, as in
[HTTP-24](#http-24).

<a id="http-39"></a>**HTTP-39. Internal failures on `/verify-keys`.** A BoostX-key lookup that fails otherwise MUST be
answered 500 `failed to get boostx key`; an absent or unusable BoostX key, 500 `failed to verify token`; a
partner-private-key lookup that fails otherwise, 500 `failed to get partner private key`; and a signing failure (an
absent or unusable private key), 500 `failed to sign response`. (Vectors: `http.json`.)

<a id="http-40"></a>**HTTP-40. Reasons and their order.** Verify-keys checks follow [VERIFYKEYS-46](#verifykeys-46), and
the first failure wins. An absent or `null` `iss` or `aud` reads as `""` (`iss-aud`), and an absent or `null` `iat` as 0
(`stale`). `iat` MUST be integral by value with magnitude at most 2^53−1, else `shape`. Every nonce fault is
`nonce-format`: absent, `null`, not a number, not integral, or outside [1, 2147483647]. Integral values are judged by
value, so `5.0` is 5 ([P-integers](#p-integers)). Primary rule [INBOUND-35](#inbound-35); also covers
[VERIFYKEYS-35](#verifykeys-35), [VERIFYKEYS-43](#verifykeys-43). (Vectors: `verifykeys.json`, `http.json`.)

<a id="http-41"></a>**HTTP-41. Canonical segments.** Each of the three JWS segments MUST be canonical unpadded base64url
([P-base64url](#p-base64url)). A header or payload segment that fails is a malformed token (reason `shape`); a signature
segment that fails, or does not decode to exactly 64 bytes, is a signature failure (reason `signature`, wrapping
`invalid_signature`). Primary rule [KEYS-26](#keys-26). (Vectors: `http.json`.)

<a id="http-42"></a>**HTTP-42. The refusal body.** A verify-keys parse failure MUST be answered 400 with the error text
exactly `invalid verifyKeysJWT: <reason>`, where the reason is the mapper's ([HTTP-57](#http-57)) and one of
`signature`, `shape`, `iss-aud`, `stale` and `nonce-format`. Only the unknown-partner answer ([HTTP-38](#http-38))
appends text after the reason. BoostX reads the reason that follows that text ([VERIFYKEYS-17](#verifykeys-17)).
(Vectors: `http.json`.)

<a id="http-43"></a>**HTTP-43. A fixed 30-second window.** The handlers MUST accept a request whose `|now − iat|` is at
most 30 whole seconds and refuse a larger one as `stale`, and MUST NOT offer an option that changes the window. The
parse functions take one, which a call may leave out, under [P-window](#p-window): absent or 0 means 30, a negative or
non-finite value is `invalid_claim`, any other value is truncated to whole seconds. Primary rule [KEYS-41](#keys-41);
also covers [VERIFYKEYS-38](#verifykeys-38), [VERIFYKEYS-40](#verifykeys-40). (Vectors: `http.json`, `verifykeys.json`.)

<a id="http-44"></a>**HTTP-44. The nonce echo.** The response MUST carry the request's nonce unchanged. Signing a
response refuses a nonce outside [1, 2^31−1] with `invalid_claim`; from the handler that cannot happen, since parsing
has already refused such a nonce as `nonce-format`. (Vectors: `http.json`.)

<a id="http-45"></a>**HTTP-45. `boostx` and the empty ID.** The verify-keys create and parse functions MUST refuse the
partner ID `""` with `missing_claim` and `"boostx"` with `invalid_claim`. A request addressed to `aud` `"boostx"` is
refused at extraction as `shape` ([HTTP-37](#http-37)). (Vectors: `http.json`.)

<a id="http-46"></a>**HTTP-46. What `/verify-keys` needs.** Answering `/verify-keys` uses only two key-store lookups,
the BoostX public key and the partner private key. An SDK MUST NOT require a bet store for its `/verify-keys` unit (JS
`handleVerifyKeys(body, {keyStore})`; Go `handlers.NewVerifyKeysHandler(keyStore)`). The router still requires a bet
store, since it also serves `/set-boost` ([HTTP-48](#http-48)). Whether the key-store type also declares the
partner-public-keys lookup follows the SDK's key-store contract. (Vectors: `http.json`, through the router, where
`/verify-keys` calls no bet-store method and no partner-public-keys lookup; a unit without a bet store is outside
`http.serve`.)

<a id="http-47"></a>**HTTP-47. Stateless.** The handlers MUST keep no state between requests and MUST NOT apply a rate
limit, serialisation or blocking: concurrent and repeated verify-keys requests are each answered on their own. BoostX's
self-test sends three requests at once, two of them deliberately invalid. (Vectors: none; informative for the SDK.)

### 11.9 Error model and surface

The error taxonomy and the surface are written in sections 3 and 4. These entries state what the HTTP layer relies on.

<a id="http-54"></a>**HTTP-54. Error categories.** The SDK error categories are `invalid_private_key`,
`invalid_public_key`, `invalid_booster`, `invalid_checkbet`, `invalid_verify_keys`, `invalid_gid`, `invalid_signature`,
`missing_claim`, `invalid_claim`, `unknown_partner` and `api_error`, plus `invalid_gamepass` only where a gamepass
parser is offered (Go's deprecated one). The store's round-rejected marker is a separate input type, not an SDK error. A
verify-keys failure carries one reason (`signature`, `shape`, `iss-aud`, `stale`, `nonce-format`), exposed as a property
(JS `BoostxError.reason`) or a sub-category (Go `ErrVerifyKeysShape`, `ErrVerifyKeysIssAud`, `ErrVerifyKeysStale`,
`ErrVerifyKeysNonce`, and `ErrInvalidSignature` for `signature`). Mapping table: section 4.2. (Vectors: every file.)

<a id="http-55"></a>**HTTP-55. A bad GID signature is both.** A GID signature that is not canonical, or that no listed
key verifies, MUST fail as both `invalid_gid` and `invalid_signature`, both present in the token error's chain. Primary
rule [KEYS-47](#keys-47); also covers [GID-17](#gid-17), [INBOUND-26](#inbound-26).
(Vectors: `gidgp.json`, `http.json`.)

<a id="http-56"></a>**HTTP-56. An unusable key is never a token error.** A key that cannot verify MUST be reported as
`invalid_public_key` alone, never wrapped in `invalid_booster`, `invalid_checkbet` or `invalid_verify_keys`, so the
handlers answer it 500 and not 400 ([HTTP-26](#http-26)). (Vectors: `http.json`.)

<a id="http-57"></a>**HTTP-57. The reason mapper.** The verify-keys reason mapper (JS `verifyKeysReason(err)`; Go
`tokens.VerifyKeysReason(err)`, re-exported as `boostx.VerifyKeysReason`) MUST return `signature` for a signature
failure or an unusable verifying key, otherwise the error's own reason (`iss-aud`, `stale`, `nonce-format`), and `shape`
for anything else. Primary rule [KEYS-60](#keys-60); also covers [VERIFYKEYS-51](#verifykeys-51). (Vectors:
`verifykeys.json`, `http.json`.)

<a id="http-58"></a>**HTTP-58. The in-memory key store, as handlers see it.** Registration MUST refuse an empty partner
ID (`missing_claim`), a supplied key that is not a usable ECDSA P-256 key of its role (`invalid_public_key`,
`invalid_private_key`) and an empty partner public key list (`invalid_public_key`). A lookup of a role that was left out
fails with that role's invalid-key error, which the handlers answer 500 `failed to get …` ([HTTP-25](#http-25)); an
unknown ID fails with `unknown_partner`, answered 400 ([HTTP-24](#http-24), [HTTP-38](#http-38)). Primary rule
[KEYS-57](#keys-57); also covers [GID-26](#gid-26). (Vectors: `keys.json`, `http.json`, `gidgp.json`.)

<a id="http-59"></a>**HTTP-59. Settlement API error text.** Any settlement answer other than an acceptance is
`api_error` with the status and an error text: the body's `error` member when that is a non-empty string,
`unexpected response` for a 2xx that is not an acceptance, and otherwise exactly `HTTP <status>`. The surrounding
message wording is informative. Primary rule [SETTLE-56](#settle-56). (Vectors: `http.json`.)

<a id="http-60"></a>**HTTP-60. Messages are not contract.** Implementation-defined: the message texts of SDK errors,
which are not part of the contract and MAY differ between SDKs; partners match errors by category.

The error strings of HTTP answers and the verify-keys reasons are part of the contract, with two exceptions: the
escaping of an echoed ID ([HTTP-24](#http-24)), and any text after a verify-keys reason
([VERIFYKEYS-14](#verifykeys-14)). The `missing required claim: <field>` and `invalid claim value: <field>` phrasing
that conformance runners read is [HTTP-72](#http-72), in section 4.5. (Vectors: none; messages are compared only through
`field`.)

<a id="http-61"></a>**HTTP-61. Functions on a parsed body.** An SDK MAY offer per-endpoint functions that take an
already-parsed JSON body and return a status and a body (JS `handleSetBoost(body, options)`, `handleCheckBet`,
`handleVerifyKeys`, resolving to `HandlerResult {status, body}`). If it does, each result MUST equal the router's answer
for a request carrying the same body, routing, method and body size are the caller's, and the function never fails
without a result ([HTTP-48](#http-48) for invalid options). Go offers none. Applies
[P-optional-surface](#p-optional-surface). (Vectors: none; `http.serve` drives the router.)

<a id="http-62"></a>**HTTP-62. Low-level helpers are optional.** Raw JWT signing, parsing and extraction, standalone GID
verification and gamepass parsing are optional (Go exports them from `tokens`: `SignJWT`, `ParseJWT`,
`ExtractJWTClaims`, `VerifyGID`, `ParseGamePassToken`; JS exports none). An SDK that exports one applies ES256 only,
canonical base64url, the byte rules, the `alg` and `crit` rules and the key rules; mapping claims into a structure the
caller supplies follows the language's decoder, while claims the spec defines are read by exact name. Primary rule
[KEYS-62](#keys-62); also covers [GID-42](#gid-42), [SETTLE-67](#settle-67). (Vectors: none.)

<a id="http-63"></a>**HTTP-63. Contract constants.** The spec fixes these values: the identity `"boostx"`; the
verify-keys reasons `signature`, `shape`, `iss-aud`, `stale` and `nonce-format`; the default settlement base URL
`https://partners-s2s.boostx.cloud`; the settlement statuses `win`, `lose`, `cancelled`, `refund`, `half_win`,
`half_lose`, `cashout` and `unsettled`; and the 30-second verify-keys window.

Implementation-defined: which of them an SDK exports as named constants, except the settlement statuses, which it
exposes ([SETTLE-14](#settle-14)). (Vectors: `http.json`, for the default base URL; the other values are pinned under
their own rules.)

<a id="http-65"></a>**HTTP-65. Result shapes.** A verified Booster yields `gid` (`partner`, `user`, `bet`, `signature`),
`round`, `boost`, `final`, `jackpot` and `iat`; a CheckBet yields `gid` and `iat`; a verify-keys parse yields
`partnerID`, `nonce` and `iat`. Argument order, overloads and nesting follow each language's idiom (section 3.4, Key
position and Names; Go embeds the GID fields and names `iat` `IssuedAt`). Section 3.3 has the per-language field names.
Primary rule [VERIFYKEYS-54](#verifykeys-54). (Vectors: `verifykeys.json`, `http.json`.)

<a id="http-67"></a>**HTTP-67. The JWS header.** The header segment MUST decode to a JSON object, or the token is
malformed (reason `shape`). Its member named exactly `alg` MUST be the string `"ES256"`, and it MUST carry no member
named exactly `crit`; either fault is a signature failure (reason `signature`). Other header members are ignored.
Primary rule [KEYS-22](#keys-22); also covers [KEYS-24](#keys-24), [KEYS-65](#keys-65), [INBOUND-05](#inbound-05),
[INBOUND-55](#inbound-55), [VERIFYKEYS-22](#verifykeys-22). (Vectors: `http.json`.)

<a id="http-70"></a>**HTTP-70. Signed payload bytes are free.** A token the SDK signs, the verify-keys response
included, MAY use any valid JSON serialisation of its payload; the signature covers the bytes the SDK produced, and
verifiers compare decoded values. The canonical GID signing bytes are the one exception. Primary rule
[KEYS-61](#keys-61); also covers [GID-38](#gid-38), [SETTLE-34](#settle-34). (Vectors: none; bytes are not compared.)

<a id="http-71"></a>**HTTP-71. Unknown claims are ignored.** A receiver MUST ignore claims and members beyond the ones
the spec defines on inbound Booster and CheckBet tokens, at the root, inside `booster` or `checkbet` and inside `gid`.
`exp` and `nbf` are not unknown: when present they are enforced ([P-exp-nbf](#p-exp-nbf), [KEYS-42](#keys-42)). BoostX
never sets either on its tokens. (Vectors: `http.json`.)

### 11.10 What the SDK sees from BoostX (informative)

These describe what BoostX sends and how it reads answers. They explain the rules above and are not requirements on an
SDK.

<a id="http-49"></a>**HTTP-49. How BoostX reads `/set-boost`.** A round counts only on a 2xx JSON body whose `result.ok`
is the JSON boolean `true`. Anything else, a 2xx that is not JSON included, voids the round, and the round is played
again after the game is reopened ([INBOUND-50](#inbound-50)).

<a id="http-50"></a>**HTTP-50. How BoostX reads `/check-bet`.** A non-2xx answer, a body that is not JSON, or one
without `result` gives no verdict, and before a round no verdict refuses the round. With check-bet switched off BoostX
makes no call.

<a id="http-51"></a>**HTTP-51. Retries.** BoostX retries `/check-bet` and `/set-boost` up to three times, after 200, 500
and 1000 ms, only on a network error or a 502, 503, 504 or 525, re-sending the same token. Any other status, a 4xx or a
plain 500 included, is taken as the partner's answer. The self-test makes a single attempt per request.

<a id="http-52"></a>**HTTP-52. No timeout in the handlers.** The SDK handlers impose no timeout on the stores
([HTTP-31](#http-31)). A round waits for the partner's answer, so a partner's store is best kept fast.

<a id="http-53"></a>**HTTP-53. How the self-test reads `/verify-keys`.** A 404 or 405 fails as a missing endpoint,
whatever the body. A non-JSON body fails as a malformed answer. A non-2xx whose `error` carries the reason
`signature`, `iss-aud` or `stale` fails with that reason's hint; any other non-2xx fails like `signature`, with the
error text in the hint. The invalid-signature probe and the foreign-ID probe pass on any non-2xx. A connection closed
without an answer fails as unreachable. The Stages section of the partner docs lists the checks and their hints.

Why the rules look the way they do, in short: BoostX reads only the status of a refusal on `/set-boost` and
`/check-bet`, so the error texts are fixed for partners' own logs and for conformance, not for BoostX; it reads the
verify-keys reason from the error text, which is why that text is normative up to the reason; and it retries only
gateway statuses and dropped connections, which is why an SDK answers its own failures with 500 and never with 502 to
504.

## 12. Conformance vectors

### 12.1 What they are

The conformance vectors are this spec in executable form: language-neutral JSON cases, each naming the rule ids it
exercises, the operation it calls, its inputs and the expected outcome. Every SDK runs all of them with a small runner
of its own. A new SDK is conformant when its runner passes every case, skipping only what FORMAT.md section 7 allows.

This repository holds the master copy, in `vectors/`, and a change starts there. Every SDK keeps an exact,
byte-for-byte mirror of the whole directory, golden files included, checked against a pinned commit of this repository,
the one that carries the spec version it implements, and changes its mirror only by moving the pin (FORMAT.md section
8). There is no other copy flow. The reference SDKs keep their mirrors here:

| SDK | Mirror of `vectors/` |
|-----|----------------------|
| JS SDK | `test/spec/` |
| Go SDK | `testdata/spec/` |

Passing the vectors is not the whole test. A conformant SDK takes its ECDSA and SHA-256 from a vetted library and writes
no point arithmetic (adding or multiplying curve points) of its own ([KEYS-69](#keys-69)), which no case can observe.
BoostX has no test environment for partners, so a partner then tests a new SDK end to end with demo games (a gamepass
built with `demo: true`, [GAMEPASS-32](#gamepass-32)) and with Test integration on the dashboard, which calls
`/verify-keys`.

### 12.2 Format

[`FORMAT.md`](vectors/FORMAT.md), next to the vectors, is the reference. In short:

- Each group file is `{ "group": …, "cases": [ … ] }`. A case has a unique `name`, its `rules`, an `op`, an `input`
  (members left out take the operation's defaults), optional named GID signatures `sigs`, a `want`, an optional
  `wantZeroValue` and a free-text `note`.
- Keys are named, never inlined: `testkeys.json` holds the test key pairs (`partner`, `partner2`, `boostx`, `other`,
  `p384`) and fixed GID signatures.
- Placeholders expand to times, bytes and GID signatures. The clock rule makes every time relative to the runner's own
  `now`, so no case depends on when it runs.
- Inbound tokens are described as token specs (header, payload, signing key, segment overrides) that the runner signs,
  so a case can carry exactly one fault.
- `want` has one of `ok` (members compared recursively, numbers as binary64), `error` (the exact set of categories over
  the cause chain, plus optional `field`, `reason`, `status`, `apiError`, `at`) or `failure` (`cancelled`, `timeout`,
  `network`), plus store checks (`keyStoreCalled`, `betStoreCalled`).
- Operations: `key.loadPrivate`, `key.loadPublic`, `keystore.register`; `gid.build`, `gamepass.create`,
  `settlement.create`, `verifykeys.createRequest`, `verifykeys.createResponse`; `x.floor`, `x.player`;
  `booster.extract`, `booster.parse`, `checkbet.extract`, `checkbet.parse`; `verifykeys.extractRequest`,
  `verifykeys.parseRequest`, `verifykeys.parseResponse`; `client.submit`; `http.serve`.
- A case with several faults expects the first in the spec's check order.

### 12.3 Files

| File | Cases | What it pins |
|------|-------|--------------|
| `testkeys.json` | (data) | The shared key pairs and fixed GID signatures |
| `keys.json` | 435 | Key loading (PEM framing, labels, DER structure, curves, points, scalars, embedded public keys), key usability, the in-memory store's registration and lookups, the builders' key checks, JWS segments and header (`alg`, `crit`, base64url, signature length), payload bytes and JSON, time claims, store answers in handlers and the client (sections 5, 11.5) |
| `gidgp.json` | 276 | `buildGID` and its canonical bytes, GID verification against key lists, the inbound `gid` shape, the gamepass builder's check order, ids, stake, currency, xrange, event title and demo, and the X helpers (sections 6, 7) |
| `inbound.json` | 393 | Booster and CheckBet extraction and parsing: framing, the root claim, the `gid`, keys, the normative check order, Booster claims, `iat`, `exp`, `nbf`, and their handler answers (section 8) |
| `settle.json` | 275 | The settlement builder's parameters and order, client construction, the request, acceptance, error text, time limit and cancellation (section 9) |
| `verifykeys.json` | 369 | Verify-keys builders, extraction, the request and response parsers, reasons and their order, the window, and the `/verify-keys` answers (section 10) |
| `http.json` | 362 | Routing, methods, the request body, the handler pipeline, key-store and bet-store answers, construction errors (section 11) |

Three golden files in `vectors/golden/` predate the format and are kept as they are:

- **X golden vectors**, `floor-x.json` and `player-x.json`, generated by BoostX. They pin `floorX` and `playerX`
  ([GAMEPASS-38](#gamepass-38) to [GAMEPASS-45](#gamepass-45)).
- **GID signature test vector**, `gid-signature.json`: the partner docs' Signature test vector, with its key pair, its
  signed GID and the canonical bytes in hex ([GID-39](#gid-39)). The canonical-bytes cases are in `gidgp.json`, in the
  shared format.

### 12.4 Running them

| SDK | Runner | Command |
|-----|--------|---------|
| JS | `test/conformance/<group>.test.ts`, one file per group, one test per case named as the case. The suite runs in two vitest projects, Node.js and workerd | `npm test`, or `npx vitest run test/conformance` |
| Go | `conformance_<group>_test.go` in the package that owns the group: `keys` (keys), `tokens` (gidgp, inbound, verifykeys), `client` (settle), `handlers` (http); test functions `TestConformance<Group>`, one subtest per case | `go test ./...`, or `go test -run TestConformance ./...` |

Runner rules, from FORMAT.md:

- A runner uses the SDK's public API only. It builds inputs, calls the SDK, and compares the outcome with `want`. The
  one exception is the runner's own check of the `gid` inside a built token, which may use a GID verifier of the SDK's,
  public or internal (FORMAT.md section 5.3).
- A case whose input some languages' static types cannot express (a number where the API takes a string, a fraction
  for a fixed-size integer, NaN or an infinity for a `time.Duration`, a missing parameter set for a struct), or whose
  ill-formed string some string types cannot hold, carries `needs` tags. A skip is permitted, never required: a runner
  may skip a case when at least one of its tags names an input its SDK cannot express, judged for that case's actual
  input rather than for everything the tag covers; where its SDK can express a tagged case's input it runs the case,
  and running more is always fine. It never skips a case without `needs`, and it reports every skip as skipped, with
  the case's tags, never as passed.
- A runner whose parameter structs cannot express absence uses `wantZeroValue` where a case has one ([P-zero](#p-zero)).

## 13. Decisions

Each entry gives the date, the decision and the rules it affects. Decisions win over any rule text that disagrees.

<a id="decision-gid-terminology"></a>**2026-10-18. GID terminology.** GID is the triple `partner`, `user`, `bet`; signed
GID is the triple plus `signature`. The partner docs and the
SDKs keep calling the signed object "GID" (`gid` claim). Affects: section 1.4 and section 6 throughout.

<a id="decision-canonical-gid-signatures"></a>**2026-10-30. Canonical GID signatures.** BoostX refuses a gamepass whose
`gid.signature` is not canonical unpadded base64url of 64 bytes when the game opens, answers such a settlement 401, and
treats the form exactly like a wrong signature. SDKs apply the same form to every GID they verify. Affects:
[P-base64url](#p-base64url), [KEYS-47](#keys-47), [GID-17](#gid-17), [INBOUND-25](#inbound-25), [SETTLE-09](#settle-09).

<a id="decision-retry-until-ok"></a>**2026-10-31. Retry until ok.** A settlement is delivered only when BoostX answers
2xx with `{"result":{"ok":true}}`. Every other outcome, a 4xx included, is retried with the same parameters within a
window (for example three days), then alerted on; no status is classified as final, since a 4xx can come from a BoostX
release that a later one fixes, and a re-send under the same `version` is idempotent. SDKs offer no retry helper and no
retryable classification. Affects: [P-settlement-acceptance](#p-settlement-acceptance), [SETTLE-63](#settle-63),
[SETTLE-64](#settle-64), [SETTLE-66](#settle-66).

<a id="decision-lone-surrogates"></a>**2026-11-01. Lone-surrogate ids are refused everywhere.** An inbound token whose
header or payload JSON text holds an unpaired `\uD800`-`\uDFFF` escape is a malformed token (`invalid_<token>`,
verify-keys reason `shape`), in extraction and parsing alike, and is never verified as a GID. An SDK scans the JSON text
for such escapes before decoding it. Builders refuse ids that are not well-formed Unicode. BoostX refuses such a
gamepass when the game opens. Affects: [P-surrogates](#p-surrogates), [KEYS-37](#keys-37), [GID-04](#gid-04),
[INBOUND-28](#inbound-28), [GAMEPASS-07](#gamepass-07), [GID-35](#gid-35).

<a id="decision-currency-case"></a>**2026-11-01. One uppercase currency rule.** `stake.currency` must match
`^[A-Z]{3,4}$`, like the settlement currency. BoostX does not upper-case a gamepass currency either, and refuses a
gamepass with a lower-case or mixed-case code when the game opens. Affects: [P-currency](#p-currency),
[GAMEPASS-14](#gamepass-14), [GAMEPASS-15](#gamepass-15), [GAMEPASS-47](#gamepass-47).

<a id="decision-minimum-stake"></a>**2026-11-01. Minimum stake 0.01.** `stake.amount` must be finite and at least 0.01
(compared as a binary64, `amount >= 0.01`) for every currency. The builders refuse anything else with `invalid_claim` on
`amount`, and BoostX refuses such a gamepass when the game opens. BoostX never signs a Booster whose boost is not finite
and greater than 0, so a non-finite boost never reaches the wire. Affects: [P-zero](#p-zero),
[GAMEPASS-10](#gamepass-10) to [GAMEPASS-13](#gamepass-13), [INBOUND-36](#inbound-36), [HTTP-23](#http-23).

<a id="decision-embedded-public-key"></a>**2026-11-01. A private key whose halves disagree is refused.** The optional
`[1]` public key of a SEC1 `ECPrivateKey`, in an `EC PRIVATE KEY` block or inside a PKCS#8 `PrivateKeyInfo`'s
`privateKey` octet string, must be exactly the 65-octet uncompressed encoding of the point the scalar derives, in a BIT
STRING with no unused bits. Any other `[1]` is `invalid_private_key`, fail closed: another key pair's point, and equally
a field that is not a valid uncompressed P-256 point (the own point compressed or hybrid, a point off the curve, the
point at infinity, another length) or not a BIT STRING at all. A key without the field still loads. An SDK compares
the field with the point it derives from the scalar. Affects: [KEYS-13](#keys-13), [KEYS-63](#keys-63).

<a id="decision-registration-order"></a>**2026-11-01. Registration checks the roles in parameter order.** The
in-memory key store checks the partner id, the partner public keys, the partner private key and then the BoostX public
key, and reports the first failure; with both the partner private key and the BoostX public key unusable it raises
`invalid_private_key`. Affects: [KEYS-57](#keys-57), [GID-26](#gid-26), [HTTP-58](#http-58).

<a id="decision-verify-keys-partner-id"></a>**2026-11-01. The verify-keys builders refuse an ill-formed partner id.**
Both builders refuse a partner id that is not well-formed Unicode (an unpaired surrogate, or invalid UTF-8 where the
language's strings can hold it) with `invalid_claim`, field `partnerID`, checked after the nonce, as
[P-surrogates](#p-surrogates) requires of every id a builder signs. Affects: [VERIFYKEYS-09](#verifykeys-09) item 3,
[VERIFYKEYS-49](#verifykeys-49) step 4.

<a id="decision-json-depth"></a>**2026-11-01. JSON nesting depth has a floor of 64 levels.** The depth limit of an SDK's
JSON reader is implementation-defined ([P-one-value](#p-one-value)), and every SDK must accept at least 64 levels. Depth
counts the arrays and objects open at one point of the text, the outermost value included, so a payload object whose
ignored member holds 63 nested arrays is 64 levels deep. A text over the SDK's limit is not valid JSON in its context.
Affects: [P-one-value](#p-one-value), [KEYS-32](#keys-32), [INBOUND-54](#inbound-54), [SETTLE-50](#settle-50),
[HTTP-09](#http-09).

<a id="decision-private-key-structure"></a>**2026-11-01. Private-key structures are pinned, and nothing may follow
them.** A PKCS#8 key is exactly a version 0 `PrivateKeyInfo` with the P-256 AlgorithmIdentifier, its `privateKey` and
optional attributes, which are not read; an `ECPrivateKey`, standalone or inside PKCS#8, is exactly version 1, the
scalar, optional `[0]` parameters naming P-256 and the optional `[1]` of the decision
[a private key whose halves disagree is refused](#decision-embedded-public-key), in that order. Lengths are DER, and
octets after the structure, or after the `ECPrivateKey` inside the `privateKey` octet string, are refused, as they are
for a public key. Each SDK checks this itself rather than through its platform's parser. Affects: [KEYS-05](#keys-05),
[KEYS-13](#keys-13), [KEYS-63](#keys-63).

<a id="decision-gid-id-rules"></a>**2026-11-03. Ids hold no `:` and have bounded lengths.** `partner`, `user` and `bet`
contain no U+003A `:`, and `partner` is at most 32, `user` at most 64 and `bet` at most 96 Unicode scalar values long.
Only U+003A is refused, nothing is normalised before the checks, and an empty id stays `missing_claim`. Every builder
that signs a GID refuses an id that breaks either rule with `invalid_claim` naming it; parsing an inbound token checks
neither. BoostX refuses such a gamepass when the game opens. Affects: [GID-09](#gid-09), [GID-10](#gid-10),
[GAMEPASS-07](#gamepass-07), [GAMEPASS-09](#gamepass-09), [GID-37](#gid-37), [KEYS-19](#keys-19),
[SETTLE-11](#settle-11), [SETTLE-12](#settle-12), [SETTLE-31](#settle-31), [SETTLE-74](#settle-74),
[P-builder-ids](#p-builder-ids), [P-check-order](#p-check-order).

<a id="decision-jackpot-result-fixed"></a>**2026-11-06. A jackpot round keeps its result.** BoostX fixes a jackpot
round's `xBase` and boost before it first sends the round, and every attempt, a retry or a re-send after a reopen, sends
that result: the same `round`, the same boost, and the `xBase` of the entry during which BoostX fixed it. A later
gamepass's `x` does not recalculate it, and BoostX computes its X as `playerX` does. Affects: section 1.6,
[GAMEPASS-21](#gamepass-21), [GAMEPASS-44](#gamepass-44), [INBOUND-49](#inbound-49), [INBOUND-50](#inbound-50).

## 14. Platform notes (informative)

These notes collect traps that common standard libraries and packages set for the rules above. They state no
requirement: each names the rule that does, and the vector cases that catch the trap, so that running those cases
first shows whether a platform's defaults fall into it. A note describes a library's default behaviour as its own
documentation states it; where a note says "check", the behaviour varies by version or is not settled here, and the
cited cases decide. The JS and Go remarks inside the rules are worked examples of the same traps.

### 14.1 Exact member names ([P-names](#p-names))

A decoder that maps JSON onto typed fields may match names loosely, so that `ROUND` or `Booster` supplies `round` or
`booster`.

- **Go.** `encoding/json` matches struct field names case-insensitively when it decodes into a struct; decode into
  `map[string]any`, or check the names yourself (`keys-payload-root-name-case`, `inbound-booster-round-case-variant`).
- **C#/.NET.** `JsonSerializer` matches names exactly by default, but `JsonSerializerDefaults.Web`, the ASP.NET Core
  default, sets `PropertyNameCaseInsensitive` and lets a JSON string stand for a number; read tokens and settlement
  answers with `JsonDocument` or with options of your own (`inbound-booster-root-case-variant`,
  `settle-client-accepted-case-variant-ignored`, `inbound-booster-round-string`).
- **Java.** Jackson matches names exactly unless `MapperFeature.ACCEPT_CASE_INSENSITIVE_PROPERTIES` is on; keep it
  off (`keys-payload-iat-name-case`, `gidgp-verify-gid-member-names-case-folded`).

### 14.2 Repeated member names ([P-duplicates](#p-duplicates))

The last occurrence wins, whole: a later object replaces an earlier one, and a later `null` counts.

- **Go.** `encoding/json` decodes a repeated member into the same struct field, so two objects merge:
  `{"a":{"x":1},"a":{"y":2}}` gives both `x` and `y`. Decode each occurrence into a fresh value, or into
  `map[string]any`, where the last wins (`keys-payload-duplicate-not-merged`,
  `settle-client-unexpected-later-result-not-merged`).
- **Java.** Jackson's tree model keeps the last occurrence unless `JsonParser.Feature.STRICT_DUPLICATE_DETECTION` or
  `DeserializationFeature.FAIL_ON_READING_DUP_TREE_KEY` is on, which refuses the text instead; keep both off
  (`keys-header-duplicate-alg-last-wins`, `http-body-duplicate-token-last-wins`).
- **C#/.NET.** `JsonElement.TryGetProperty` matches the last occurrence of a repeated name; check what any other
  entry point you use (`JsonNode`, the serializer) does with one (`keys-payload-duplicate-later-null`,
  `gidgp-verify-gid-duplicate-member-last-wins`).

### 14.3 Lone-surrogate escapes ([KEYS-37](#keys-37), [P-surrogates](#p-surrogates))

A `\uD800`-`\uDFFF` escape that is not half of a pair makes the token malformed. The check runs on the JSON text,
because decoders disagree on what they return for one.

- **Go.** `encoding/json` replaces the escape with U+FFFD, so the decoded value no longer shows it
  (`keys-surrogate-lone-low`, `keys-surrogate-gid-bet-never-verified`).
- **Python and JavaScript.** `json.loads('"\\ud800"')` and `JSON.parse` return a string holding the lone surrogate,
  without complaint; scan the text first (`keys-header-lone-surrogate`, `keys-surrogate-reversed-pair`).
- **Java.** Java strings can hold a lone surrogate, so a JSON library may return one rather than fail; check yours,
  and scan the text either way (`keys-surrogate-high-then-plain-escape`).
- **PHP.** `json_decode` refuses such an escape with `JSON_ERROR_UTF16`. Report that failure as a malformed token,
  in the step where the spec reads that text, after the signature for a payload
  (`keys-order-signature-before-payload-surrogate`, `keys-surrogate-uppercase-hex`).
- **C#/.NET.** Check what `Utf8JsonReader` and `JsonDocument` do with a lone-surrogate escape in your version, and scan
  the text either way (`keys-surrogate-lone-low`); an escaped pair stays valid (`keys-header-surrogate-pair-accepted`).

### 14.4 Strict UTF-8, no replacement, no byte order mark ([P-utf8](#p-utf8))

The bytes are checked before they are parsed: nothing replaces a bad sequence with U+FFFD, and a leading `EF BB BF`
is refused, never stripped.

- **Python.** `bytes.decode('utf-8')` is strict: it refuses overlong forms and encoded surrogates. `json.loads` given
  `bytes` is not: it guesses UTF-8, UTF-16 or UTF-32, decodes with `surrogatepass`, so `ED A0 80` gets through, and
  strips a UTF-8 byte order mark. Decode the bytes yourself and pass a `str` (`keys-payload-encoded-surrogate`,
  `keys-payload-bom`, `settle-client-unexpected-encoded-surrogate`).
- **Java.** `new String(bytes, StandardCharsets.UTF_8)` replaces malformed input with U+FFFD. Decode with
  `StandardCharsets.UTF_8.newDecoder()`, which reports malformed input by default, and run the overlong cases to
  confirm it refuses those forms (`keys-payload-invalid-utf8`, `keys-payload-overlong-3-byte`).
- **C#/.NET.** `Encoding.UTF8.GetString` replaces invalid bytes with U+FFFD; `new UTF8Encoding(false, true)` throws on
  them instead. Check whether your JSON entry point skips a leading byte order mark (`keys-header-overlong-utf8`,
  `http-body-overlong-utf8`, `keys-header-bom`).
- **PHP.** Strings are bytes. `json_decode` refuses invalid UTF-8 unless it is given `JSON_INVALID_UTF8_IGNORE` or
  `JSON_INVALID_UTF8_SUBSTITUTE`, which an SDK never passes; run the overlong and byte order mark cases to confirm the
  rest (`inbound-booster-payload-invalid-utf8`, `keys-vk-payload-bom`).
- **JavaScript.** `TextDecoder` with `fatal: true` refuses bad bytes, but strips a leading byte order mark unless
  `ignoreBOM: true` is set too (`settle-client-unexpected-byte-order-mark`).
- **Go.** `encoding/json` replaces invalid UTF-8 inside a string with U+FFFD; check the bytes with `utf8.Valid` first
  (`gidgp-verify-invalid-utf8-in-user`).

### 14.5 NaN and Infinity literals ([INBOUND-09](#inbound-09), [P-one-value](#p-one-value))

JSON has no `NaN`, `Infinity` or `-Infinity`; a text that holds one is not valid JSON, so the token is malformed.

- **Python.** `json.loads` accepts all three as numbers by default. Pass a `parse_constant` that raises
  (`inbound-booster-payload-bare-nan`). A number text beyond the binary64 range, such as `1e400`, becomes `inf`,
  which is the value the rules then judge (`inbound-booster-boost-overflow`).
- **Java.** Jackson refuses them unless `JsonReadFeature.ALLOW_NON_NUMERIC_NUMBERS` is on. Gson's `JsonParser`
  parses leniently, and lenient parsing accepts them; check your version (`inbound-booster-payload-bare-nan`).

### 14.6 Objects and arrays ([P-one-value](#p-one-value), [P-body](#p-body))

Where the spec needs an object, any other value is a structural fault, an empty array included.

- **PHP.** `json_decode($text, true)` turns both `{}` and `[]` into an empty array, and a list into an array keyed 0, 1,
  …, so an object can no longer be told from an array. Decode objects as objects (`json_decode($text, false)`, then
  `is_object`) (`keys-extract-payload-not-object`, `inbound-checkbet-root-array`, `keys-checkbet-header-array`).
  `json_decode` also returns `null` both for the text `null` and for a failure unless `JSON_THROW_ON_ERROR` is passed,
  and the two are answered differently (`http-body-null`, `http-body-not-json`). Decoding objects as objects also
  refuses a member name that starts with U+0000 (`JSON_ERROR_INVALID_PROPERTY_NAME`), although such a name is valid JSON
  and may sit in an ignored member of a valid token; check how your decoding handles one.

### 14.7 Canonical base64url ([P-base64url](#p-base64url))

The portable check is the one the rule gives: alphabet and length, decode, re-encode, compare.

- **Python.** `base64.urlsafe_b64decode` requires padding, ignores non-zero unused bits and silently drops characters
  outside the alphabet (`keys-b64-header-trailing-bits`, `keys-b64-payload-space`, `gidgp-verify-signature-padded`).
- **JavaScript.** Node's `Buffer.from(text, 'base64url')` accepts padding, non-zero unused bits and stray characters
  (`keys-b64-signature-trailing-bits`, `inbound-booster-signature-padded`).
- **Java, C#/.NET and PHP.** Whatever decoder the platform offers (`java.util.Base64.getUrlDecoder()`,
  `Convert.FromBase64String` after mapping the alphabet, `base64_decode` in strict mode), re-encode and compare rather
  than rely on its strictness (`keys-gid-sig-trailing-bits`, `gidgp-verify-signature-std-alphabet`).

### 14.8 The GID's canonical bytes ([GID-02](#gid-02), [GID-03](#gid-03))

The signature covers exactly what JavaScript's `JSON.stringify` writes for the three ids, and few encoders write those
bytes by default.

- **Python.** `json.dumps({"partner": p, "user": u, "bet": b}, ensure_ascii=False, separators=(",", ":"))` writes
  them (`gidgp-gid-build-other-c0-lowercase-hex`, `gidgp-gid-build-line-separators-literal`).
- **Go.** `encoding/json` escapes `<`, `>` and `&` unless told not to, and U+2028 and U+2029 always
  (`gidgp-gid-build-html-quote-backslash`, `gidgp-gid-build-line-separators-literal`).
- **C#/.NET.** System.Text.Json's default encoder escapes every non-ASCII character and the HTML-sensitive ones. With
  any encoder, check the case of the hex digits it writes in a `\u` escape, which GID-03 needs in lower case, and how it
  writes a character outside the Basic Multilingual Plane (`gidgp-gid-build-non-ascii-literal`,
  `gidgp-gid-build-html-quote-backslash`, `gidgp-gid-build-other-c0-lowercase-hex`, `gidgp-gid-build-astral-literal`).
- **Java.** Gson escapes `<`, `>`, `&`, `=` and `'` unless `disableHtmlEscaping()` is set; check whether your version
  still escapes U+2028 and U+2029 with it set, and any library's escaping of control characters, against the cases
  (`gidgp-gid-build-short-escapes`, `gidgp-gid-build-other-c0-lowercase-hex`,
  `gidgp-gid-build-line-separators-literal`).
- **PHP.** `json_encode` escapes `/` and every non-ASCII character by default, and U+2028 and U+2029 even with
  `JSON_UNESCAPED_UNICODE` unless `JSON_UNESCAPED_LINE_TERMINATORS` is set too (`gidgp-gid-build-slash-del-c1-literal`,
  `gidgp-gid-build-line-separators-literal`).
- **Every language.** The text is small and GID-03 is one table, so writing it by hand, as the Go SDK does, is often
  simpler than taming an encoder. A verifier rebuilds it from the decoded ids and never reuses the received text
  (`gidgp-gid-build-astral-literal`, `inbound-booster-gid-canonical-bytes`).

### 14.9 Signatures are the raw r || s ([KEYS-29](#keys-29), [KEYS-30](#keys-30), [GID-14](#gid-14))

A JWS signature and `gid.signature` are the 64-byte `r || s`. Many cryptography APIs sign and verify the DER (ASN.1)
form by default; every accepted builder case checks what an SDK emits.

- **Python.** `cryptography`'s `sign(data, ec.ECDSA(hashes.SHA256()))` returns DER, and `verify` expects it. Convert
  with `decode_dss_signature` and `encode_dss_signature` from `cryptography.hazmat.primitives.asymmetric.utils`, after
  checking that the received signature is 64 bytes (`gidgp-verify-signature-der`, `keys-sig-67-bytes`,
  `gidgp-gid-build-plain`).
- **Java.** `Signature.getInstance("SHA256withECDSA")` signs and verifies DER. Use `SHA256withECDSAinP1363Format`
  where your provider offers it, or convert (`gidgp-verify-signature-der`, `keys-sig-63-bytes`).
- **C#/.NET.** `ECDsa.SignData` and `VerifyData` use the fixed `r || s` form by default
  (`DSASignatureFormat.IeeeP1363FixedFieldConcatenation`); `Rfc3279DerSequence` is the DER one
  (`gidgp-gid-build-plain`).
- **PHP.** `openssl_sign` and `openssl_verify` use DER for EC keys; convert both ways (`gidgp-verify-signature-der`,
  `gidgp-gid-build-plain`).
- **Go.** `ecdsa.SignASN1` and `ecdsa.VerifyASN1` use DER; `ecdsa.Sign` returns, and `ecdsa.Verify` takes, `r` and `s`
  as integers, each written as 32 big-endian bytes (`keys-sig-zero`).
- **JavaScript.** Web Crypto signs and verifies `r || s`; Node's `crypto.sign` writes DER unless it is given
  `dsaEncoding: 'ieee-p1363'` (`keys-sig-flipped`).
- **Every language.** No low-S rule applies: a verifier that refuses `s > n/2` fails `keys-sig-high-s-accepted` and
  `keys-gid-sig-high-s-accepted`.

### 14.10 PEM and DER ([KEYS-04](#keys-04) to [KEYS-13](#keys-13))

Key loading is pinned closely (decision [private-key structures](#decision-private-key-structure)), and platform
loaders accept more than the spec does.

- **Every language.** The SDK parses the PEM framing and the DER structures itself, and asks the platform only to
  build a key from the checked scalar or point. A platform loader may accept what the spec refuses: encrypted keys,
  header lines, other curves, trailing octets (`keys-private-proc-type-header-refused`,
  `keys-private-pkcs8-trailing-octets-refused`, `keys-private-sec1-public-key-mismatch-refused`), or an SPKI whose
  BIT STRING declares unused bits. Node.js's Web Crypto `spki` import (OpenSSL) clears those bits, accepting the key
  when they were already zero (`keys-public-unused-bits-declared-refused`); Go's `x509` shifts the value right by the
  declared count, so a point stored shifted left by that count loads as the unshifted key
  (`keys-public-unused-bits-shifted-point-refused`). Check that octet, or the whole fixed 26-octet prefix of the SPKI,
  before the platform parses anything ([KEYS-12](#keys-12)).
- **Python.** `cryptography`'s `load_pem_private_key` loads keys of other types and on other curves; check the type and
  the curve before using the key (`keys-private-p384-pkcs8-refused`, `keys-private-ed25519-refused`).
- **Java.** `KeyFactory.getInstance("EC")` with a `PKCS8EncodedKeySpec` reads PKCS#8 only; a SEC1 key needs parsing
  of your own (`keys-private-sec1-accepted`).

### 14.11 Numbers are judged as binary64 values ([P-integers](#p-integers))

An integer claim is a JSON number whose binary64 value is integral and in range, whatever its spelling, and never a
string or a boolean.

- **Python.** `json.loads` returns an `int` of any size for an integer text and a `float` for the rest, so `3.0` is a
  `float` and `9007199254740993` an exact `int`. `json.loads(text, parse_int=float)` makes every number arrive as its
  binary64 value, `inf` or `-inf` beyond the range, which is the value the rule judges (`keys-iat-rounds-past-max-safe`,
  `inbound-booster-round-exponent-spelling`, `inbound-booster-round-overflow`). Without it, `json.loads` itself builds
  each integer with `int()`, which recent Python releases refuse for a text of more than 4300 digits (`ValueError`; 3.11
  and later, and the 3.7.14, 3.8.14, 3.9.14 and 3.10.7 security releases), and `float()` of an exact `int` beyond the
  binary64 range raises `OverflowError` afterwards; `parse_int=float` avoids both. `bool` is a subclass of `int`, so
  test `type(x) is bool` before any number check (`inbound-booster-round-boolean`, `keys-iat-boolean`).
- **PHP.** `json_decode` gives an `int` for an integer text that fits in 64 bits and a `float` otherwise, so judge
  `is_int($x) || is_float($x)` by value, never `is_int` alone, and never pass `JSON_BIGINT_AS_STRING`
  (`inbound-booster-round-max-safe`, `verifykeys-request-nonce-integral-exponent`).
- **Java.** Jackson picks the node type from the spelling (`IntNode`, `LongNode`, `BigIntegerNode`, `DoubleNode`);
  judge any numeric node by `doubleValue()` (`keys-iat-exponent-accepted`, `inbound-booster-iat-overflow`).
- **C#/.NET.** `JsonElement.TryGetInt64` fails for `3.0` and `3e0`; read the number as a double and judge the value.
  `TryGetDouble` may report a failure, rather than an infinity, for a text beyond the binary64 range such as `1e400`;
  check yours, and where it does, parse `GetRawText()` with `double.Parse` and the invariant culture, which returns plus
  or minus infinity on .NET Core 3.0 and later (`inbound-booster-round-exponent-spelling`,
  `inbound-booster-boost-overflow`).

### 14.12 Whole-string regular expressions ([P-currency](#p-currency), [P-base64url](#p-base64url))

`^[A-Z]{3,4}$` and the `gid.signature` pattern match the whole string; in several regex flavours `$` also matches
before a final line feed.

- **Python.** `re.match(r'^[A-Z]{3,4}$', 'USD\n')` matches; use `re.fullmatch`, or end with `\Z`
  (`settle-create-currency-trailing-newline`, `gidgp-gamepass-currency-trailing-newline`).
- **PHP.** `preg_match('/^[A-Z]{3,4}$/', "USD\n")` matches; add the `D` modifier, or end with `\z`
  (`settle-create-currency-trailing-newline`, `inbound-booster-gid-signature-trailing-newline`).
- **Java.** With `find()`, `$` matches before a final line terminator; `matches()` takes the whole input
  (`gidgp-gamepass-currency-trailing-newline`).
- **C#/.NET.** `$` matches before a final `\n`; end the pattern with `\z` (`settle-create-currency-trailing-newline`).
- **Go and JavaScript.** Without the multi-line flag, `$` matches only at the end of the text
  (`gidgp-verify-signature-crlf-appended`).

### 14.13 floorX ([GAMEPASS-38](#gamepass-38), [GAMEPASS-43](#gamepass-43))

Step 2 rounds the exact binary64 value of `s` to 15 significant digits and parses the text back. A formatter that
rounds a shorter decimal form, or a fused multiply-add inside `playerX`, moves the result by one step.

- **Python.** `float(format(s, '.15g'))` is step 2. `math.floor` raises `OverflowError` on an infinity and
  `ValueError` on NaN, so test `math.isfinite` first and return the non-finite value (`gidgp-x-floor-round15`,
  `gidgp-x-player-overflow-infinity`).
- **Java.** `new BigDecimal(s)` holds the exact value; `round(new MathContext(15))` and then `doubleValue()` is step 2
  (`gidgp-x-floor-round15-second`, `gidgp-x-floor-below-exactness-bound`).
- **C#/.NET.** `double.Parse(s.ToString("G15", CultureInfo.InvariantCulture), CultureInfo.InvariantCulture)` on .NET
  Core 3.0 and later, which format from the exact value (check on .NET Framework); without the invariant culture a
  decimal comma breaks the round trip (`gidgp-x-floor-round15`).
- **PHP.** `(float) sprintf('%.14e', $s)` gives 15 significant digits, and the `e` conversion, unlike `f`, ignores the
  locale; check it against the cases and the golden files. Never format with a string cast or `strval`, which follow the
  `precision` setting (`gidgp-x-floor-round15-second`).
- **Go.** The language specification lets a compiler fuse `x*y + z` into one fused multiply-add; an explicit
  conversion, `float64((b - 1) * boost) + 1`, prevents it (`gidgp-x-player-no-fused-multiply-add`).

### 14.14 JSON nesting depth ([P-one-value](#p-one-value), decision [JSON nesting depth](#decision-json-depth))

Every SDK accepts at least 64 levels; a deeper text may be refused as not valid JSON.

- **C#/.NET.** System.Text.Json's default `MaxDepth` is 64, exactly the floor; keep it at least that, and run the
  64-level cases to see that the boundary falls on the right side (`inbound-booster-ignored-member-nested-64-levels`,
  `settle-client-accepted-member-nested-64-levels`).
- **Python.** A deep enough text makes `json.loads` raise `RecursionError`, which is not a `ValueError`; catch it and
  treat the text as not valid JSON. How deep that is depends on the version and the stack, so check yours: recent
  CPython releases parse texts far deeper than older ones before they raise, and 64 levels is well inside every
  release (`http-body-ignored-member-nested-64-levels`).
- **PHP.** `json_decode`'s default depth is 512; a smaller depth passed to it has to leave room for 64 levels
  (`inbound-booster-ignored-member-nested-64-levels`).

### 14.15 Error cause chains ([P-taxonomy](#p-taxonomy), section 4.1)

The vectors compare the categories over the whole chain, and a handler finds the round-rejected error anywhere in it.

- **Python.** Chain with `raise … from err`, which sets `__cause__`. `str()` of an exception does not include its
  cause, so the `field` phrase goes into the outermost message (`http-set-boost-store-rejects-wrapped`,
  `inbound-booster-signed-by-other-key`). Never raise an error whose `__cause__` you set yourself, in its constructor
  for example, with `raise err from None`: `from None` sets `__cause__` to `None` and erases the cause categories, so
  every case expecting one fails (`inbound-booster-round-null`, `keys-iat-boolean`,
  `gidgp-verify-signature-std-alphabet`). Raise such an error with a plain `raise err`, which keeps the `__cause__`
  you set. Inside an `except` block Python then also records the exception being handled as `__context__`, which no
  check reads, and tracebacks already leave it out: assigning `__cause__` sets `__suppress_context__` to `True` as well
  (PEP 415), which is the half of `from None` that is wanted.
- **Java.** Pass the cause to the constructor or to `initCause`, and walk `getCause()`
  (`http-set-boost-store-rejects-wrapped`). A checked exception from a partner's store (an `SQLException`, say) cannot
  leave a method that does not declare it. Either the store method and the call that consults it declare it
  (`throws Exception`), so it reaches the caller unchanged, or the SDK wraps it once, with the original as the cause,
  in an unchecked exception that carries no category (a `CompletionException`, for example) and lets unchecked ones
  through unwrapped. Both meet [SETTLE-58](#settle-58) and [KEYS-54](#keys-54), since `getCause()` is Java's chain;
  a wrapper defeats a partner's `catch (SQLException e)`, so the SDK documents it
  (`settle-client-store-plain-error-passes-through`, `settle-client-unknown-partner`).
- **C#/.NET.** Walk `InnerException`. A task's `Wait()` or `Result` wraps the error in an `AggregateException`; `await`
  does not (`http-set-boost-store-rejects-wrapped`, `http-set-boost-store-error`).
- **PHP.** Pass the cause as the constructor's third argument, and walk `getPrevious()`
  (`http-set-boost-store-rejects-wrapped`).

### 14.16 The settlement client's HTTP stack ([SETTLE-39](#settle-39), [SETTLE-49](#settle-49), [SETTLE-55](#settle-55), [SETTLE-56](#settle-56))

The client follows no redirect, reads at most 65 536 bytes of the body, and turns every status into an outcome, never
into an exception of the HTTP library's own.

- **Python.** `urllib.request` follows redirects and raises `HTTPError` for a non-2xx answer, whose body still has to be
  read for the error text; `requests` follows redirects unless given `allow_redirects=False`; `httpx` does not follow
  them by default. The `timeout` of `requests` and `httpx` bounds each network operation, not the whole attempt
  (`settle-client-redirect-301-not-followed`, `settle-client-error-text-not-stored`,
  `settle-client-timeout-reading-body`). The standard library has no asynchronous HTTP client, so an asyncio SDK's
  default transport uses a library such as `httpx` (`AsyncClient`) or `aiohttp` (which follows redirects unless given
  `allow_redirects=False`), as a dependency of the default transport alone; which one is the SDK's choice
  ([SETTLE-68](#settle-68)); an asynchronous client is the simpler way to meet [SETTLE-61](#settle-61) and
  [SETTLE-62](#settle-62). A transport of the standard library alone runs `http.client`, which follows no redirect, in
  a thread (`asyncio.to_thread`). Unlike a partner's blocking store, that thread is the SDK's own code, bound by both
  rules: a coroutine that stops waiting for it is not enough, since a thread still connecting when the call is
  cancelled would send the settlement afterwards, and one blocked reading would hold the connection. Such a transport
  meets the rules only when it does both of these: the thread checks a cancellation flag, set from the event loop on a
  cancellation or an expired limit, right before it writes the request, and sends nothing once the flag is set; and on
  a cancellation or an expiry the loop closes the socket, which ends the thread's blocking read
  (`settle-client-cancelled-reading-body`, `settle-client-cancelled-waiting-for-answer`,
  `settle-client-timeout-waiting-for-answer`). As the step-3 parser of [SETTLE-39](#settle-39),
  `urllib.parse.urlsplit` silently removes ASCII tab, CR and LF anywhere in the URL, and checks the port only when
  `.port` is read, so `https://boostx\n.test` and `https://host:99999` pass it unless the SDK reads `.port`; either
  outcome is that rule's implementation-defined residue, as long as steps 1 and 2 run first
  (`settle-client-base-url-empty-host`, `settle-client-base-url-empty-host-with-port`).
- **Java.** `java.net.http.HttpClient` follows no redirect by default (`Redirect.NEVER`) and raises nothing for a
  status; check whether the request's `timeout` covers reading the body, which [SETTLE-61](#settle-61) needs
  (`settle-client-redirect-308-error-text`, `settle-client-timeout-reading-body`). On OpenJDK 27 it does, with
  `BodyHandlers.ofInputStream()`, but a read that the timeout ends fails with an `IOException` ("closed") whose
  `getCause()` is the `HttpTimeoutException`, so an SDK that relies on it looks down the chain to report a time-out
  (section 14.17). As the step-3 parser of [SETTLE-39](#settle-39), `java.net.URI` reads `https://my_host.test` as a
  registry-based authority whose `getHost()` is `null`, accepts `https://host:99999` with port 99999, and refuses a
  control character or a `\` in the authority. An SDK that refuses the first at construction, or adds a port check
  that refuses the second, stays inside that rule's residue once steps 1 and 2 have run, though a host name with `_`
  refused at construction may surprise a partner (`settle-client-base-url-empty-host`,
  `settle-client-base-url-empty-host-with-port`).
- **C#/.NET.** `HttpClientHandler` follows redirects by default: set `AllowAutoRedirect` to `false`.
  `HttpClient.Timeout` defaults to 100 seconds, not the spec's 30; with `HttpCompletionOption.ResponseHeadersRead`,
  which a 65 536-byte cap needs, check that the time limit still covers reading the body
  (`settle-client-redirect-301-not-followed`, `settle-client-timeout-zero-means-default`).
- **PHP.** curl follows no redirect unless `CURLOPT_FOLLOWLOCATION` is set, but the `http://` stream wrapper
  (`file_get_contents`) and Guzzle follow them by default (Guzzle: `'allow_redirects' => false`), and Guzzle raises an
  exception for a 4xx or 5xx unless given `'http_errors' => false` (`settle-client-redirect-308-error-text`,
  `settle-client-error-text-unauthorized`).

### 14.17 Cancellation and the time limit ([SETTLE-61](#settle-61), [SETTLE-62](#settle-62), [SETTLE-76](#settle-76))

A cancellation stops the call at once in any step, the key-store lookup and the body read included, and one time
limit covers the whole attempt.

- **Python.** With asyncio, cancelling the task that runs the call is the standard primitive: the call fails with
  `asyncio.CancelledError`, a `BaseException`, which `except Exception` does not catch, so it passes through unless the
  SDK catches it on purpose. `asyncio.timeout()` around the whole attempt gives the time limit, failing with
  `TimeoutError` (Python 3.11 and later). An asyncio SDK may also accept plain functions as store methods (section 3.4,
  Sync or async), as JS awaits whatever a store returns; but a plain function that blocks holds the event loop, so
  neither the time limit nor a cancellation can stop it before it returns, the position of a Go store that ignores its
  context ([SETTLE-61](#settle-61)). A partner reading such an SDK's documentation is helped by learning there that only
  an async store is bounded; `asyncio.to_thread` frees the loop, though the thread still runs to its end
  (`settle-client-timeout-in-key-lookup`, `settle-client-cancelled-in-key-lookup`). With asyncio, a cancellation and the
  expiry of `asyncio.timeout()` arrive only where the task suspends, so synchronous code (signing, a plain-function
  store) runs to its end first. A cancellation the caller requested on its own task before awaiting the call (the call
  awaited directly, not run as a task of its own) arrives at the call's first suspension, so the "before the key store
  is consulted" of [SETTLE-62](#settle-62) needs a suspension before the lookup, such as `await asyncio.sleep(0)`. An
  expiry arrives only once the loop has run the timer's callback, and a single `sleep(0)` does not wait for that: the
  task resumes first. So the "no request is sent once the limit has expired" of [SETTLE-61](#settle-61) needs an
  explicit test right before the request is handed to the transport, such as comparing the loop's clock with the
  deadline (`loop.time() >= timeout.when()`) and raising `TimeoutError`. No vector observes either, since a runner
  cancels, and lets the limit expire, while the SDK awaits (`settle-client-cancelled-before-call` cancels a task that
  has not started). A synchronous Python SDK is in PHP's position below (`settle-client-cancelled-waiting-for-answer`,
  `settle-client-timeout-spans-whole-attempt`). In the handlers, `asyncio.CancelledError` is the task's cancellation,
  not a failure reported through the normal error channel of [HTTP-28](#http-28), even when a store raises it for its
  own reasons: a router answers what a store raises as an `Exception` and lets a `BaseException` propagate unanswered,
  as it does when the request's own task is cancelled ([HTTP-31](#http-31)), and the connection then ends without an
  answer from the SDK, which BoostX retries on `/set-boost` and `/check-bet` as HTTP-28 explains
  (`http-set-boost-store-error` is an ordinary store failure, which is answered).
- **Java.** The platform has no standard cancellation token; `Thread.interrupt()` and `Future.cancel(true)` are the
  usual candidates. Check whether your HTTP client aborts the exchange on either, and otherwise define the token of
  SETTLE-76 (`settle-client-cancelled-in-key-lookup`, `settle-client-cancelled-before-call`). The platform has more than
  one timeout error, and any of them reports an expired limit ([SETTLE-76](#settle-76)).
  `java.util.concurrent.TimeoutException`, which `Future.get(timeout, unit)` throws, is checked and not an
  `IOException`; `CompletableFuture.orTimeout` does not throw it but completes the future with it, so `get()` throws an
  `ExecutionException` and `join()` a `CompletionException`, each with the `TimeoutException` as its cause, and an SDK
  built on it unwraps that cause before reporting the time-out. `java.net.http.HttpTimeoutException`, which `HttpClient`
  raises when a request's `timeout` expires, and `java.net.SocketTimeoutException`, from `HttpURLConnection` and
  sockets, are `IOException`s, so a partner's `catch (IOException e)` and a runner's `network` check by
  `instanceof IOException` match them as well. An SDK that reports a time-out with one of those tells partners to catch
  it before `IOException`, and its runner tests for `timeout` before `network`. `HttpRequest.timeout` alone bounds the
  exchange only, not the key-store lookup and the signing that come before it, which [SETTLE-61](#settle-61)'s limit
  also covers (`settle-client-timeout-in-key-lookup`, `settle-client-timeout-reading-body`).
- **C#/.NET.** The call takes a `CancellationToken`. A cancellation and an expired limit both raise
  `OperationCanceledException`, so the SDK documents how a caller tells them apart ([SETTLE-76](#settle-76)), for
  example by its own token's `IsCancellationRequested`; `CancellationTokenSource.CreateLinkedTokenSource` and
  `CancelAfter` combine the caller's token with the limit (`settle-client-timeout-waiting-for-answer`,
  `settle-client-cancelled-waiting-for-answer`).
- **PHP and other single-threaded synchronous platforms.** Nothing outside the call runs while it blocks, so a
  cancellation can only arrive through code the call itself runs: the SDK's own token, polled, a signal handler
  (`pcntl_async_signals`), or a deadline. SETTLE-61 and SETTLE-62 apply unchanged. One design that meets them, in
  PHP (`settle-client-cancelled-in-key-lookup`, `settle-client-timeout-in-key-lookup`,
  `settle-client-cancelled-waiting-for-answer`, `settle-client-timeout-reading-body`):
  1. a token type of the SDK's own, documented as SETTLE-76 asks;
  2. a check of the token and the attempt's deadline before the key-store lookup and at every step of
     [SETTLE-59](#settle-59) after it;
  3. a key-store contract that takes the token and the remaining time, as Go's takes a context, so that a store that
     waits can stop; as with Go, whose store is bounded only when it honours its context (SETTLE-61), a store that
     blocks without looking at them is not bounded;
  4. the request driven by `curl_multi_exec` and `curl_multi_select` in a loop with a short select timeout, which
     checks the token and the deadline on every turn and aborts the transfer as soon as either fires, with the
     remaining time also given to curl as `CURLOPT_TIMEOUT_MS`;
  5. an injectable transport ([SETTLE-68](#settle-68)) that takes the token and the remaining time too, which PSR-18's
     `sendRequest` does not.
  In such an SDK's runner, the fake key store and the fake transport poll the token and the deadline while they wait,
  so the cancellation cases and the time-limit cases above stop at once.

### 14.18 Points without curve arithmetic ([KEYS-13](#keys-13), [KEYS-63](#keys-63), [KEYS-69](#keys-69))

KEYS-13 compares the `[1]` field of a private key with the point its scalar derives, and KEYS-12 and KEYS-63 need a
public point on the curve. KEYS-69 forbids point arithmetic of the SDK's own, and neither check needs any: the crypto
library derives and checks the points.

- **Every language.** Check the form of the `[1]` field by its octets first: 65 octets, the first `0x04`, and X and Y
  each below the field prime p of P-256, compared as 32-octet big-endian numbers. Then compare it, octet for octet, with
  the uncompressed point the library derives from the scalar, where the library offers one. Where it offers none, sign a
  message of fresh random bytes, drawn anew for every key loaded, with the private key and verify the signature with the
  `[1]` point imported as a public key. A fresh message is what makes this a test: for any one signature another public
  key also verifies it, so with a fixed message and a deterministic signer (RFC 6979) the author of a key file could
  predict the signature and put that other key in `[1]`; a message nobody can predict leaves the scalar's own point as
  the only one that verifies, apart from a negligible chance. A public point is checked by importing it through the
  library, which refuses a point off the curve; where yours does not, test the curve equation `y² = x³ − 3x + b (mod p)`
  with the platform's big integers and the published P-256 constants, which checks the point and does no point
  arithmetic (`keys-private-sec1-public-key-mismatch-refused`, `keys-private-sec1-public-key-off-curve-refused`,
  `keys-public-coordinates-out-of-range-refused`, `keys-public-point-off-curve-refused`).
- **Python.** `cryptography`'s `ec.derive_private_key(d, ec.SECP256R1())` builds the key from the scalar, and
  `public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)` (both from
  `cryptography.hazmat.primitives.serialization`) gives the 65 octets to compare;
  `ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), octets)` refuses a point off the curve
  (`keys-private-pkcs8-public-key-mismatch-refused`, `keys-public-point-off-curve-refused`).
- **Go.** `ecdh.P256().NewPrivateKey(d)`, with the scalar as 32 octets, and its `PublicKey().Bytes()` give the
  uncompressed point; `ecdh.P256().NewPublicKey(octets)` refuses a point off the curve and the point at infinity
  (`keys-private-sec1-public-key-off-curve-refused`, `keys-public-point-off-curve-refused`,
  `keys-public-point-at-infinity-refused`).
- **JavaScript.** In Node.js, `crypto.createECDH('prime256v1')`, then `setPrivateKey(d)` and `getPublicKey()`, give the
  uncompressed point. With Web Crypto, a private key imported as extractable can be exported as a JWK whose `x` and `y`
  are the point; check that your runtime imports a key without the `[1]` field
  (`keys-private-pkcs8-without-public-key-accepted`, `keys-private-pkcs8-public-key-mismatch-refused`).
- **Java.** The JDK has no public call that derives a point from a scalar. Build both keys with
  `KeyFactory.getInstance("EC")` (`ECPrivateKeySpec`, `ECPublicKeySpec`), sign a message of fresh random bytes with
  `Signature.getInstance("SHA256withECDSA")` and verify it under the `[1]` point, as the first note says (never a fixed
  message); or take the point from a vetted library that derives it, such as Bouncy Castle. The JDK's SunEC provider
  does not refuse an off-curve point: on OpenJDK 27, `KeyFactory.generatePublic` builds an `ECPublicKey` from an
  `ECPublicKeySpec` holding one, and `Signature.verify` with it returns `false` without throwing. Trusting it would
  report an off-curve BoostX key as a signature failure, which [KEYS-63](#keys-63) forbids, so test the coordinate range
  and the curve equation, as the first note says, for every public key object the SDK is given as well as for every key
  it loads. No vector hands a parser such a key object: a runner gets key objects only from the SDK's loaders, which
  refuse such a point, or as the P-384 `@unusable`, and Web Crypto and `cryptography` cannot build one at all (KEYS-63
  leaves malformed key objects to each SDK's own tests), so test it in yours
  (`keys-private-sec1-public-key-mismatch-refused`, `keys-public-point-off-curve-refused`).
- **C#/.NET.** Check whether your version's `ECDsa.ImportParameters` accepts `ECParameters` that carry `D` without `Q`,
  and then reports `Q` through `ExportParameters(false)`; otherwise sign and verify as above
  (`keys-private-sec1-public-key-mismatch-refused`).
- **PHP.** OpenSSL derives the point when it loads an `EC PRIVATE KEY` that has no `[1]` field. Build such a block from
  the scalar and the `[0]` parameters, load it with `openssl_pkey_get_private`, and read `x` and `y` from
  `openssl_pkey_get_details()['ec']`, each left-padded to 32 octets; check this on your build
  (`keys-private-sec1-without-public-key-accepted`, `keys-private-sec1-public-key-mismatch-refused`).
