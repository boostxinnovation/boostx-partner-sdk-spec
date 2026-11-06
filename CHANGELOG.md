# Changelog

## v1.2.0

On 2026-11-06 BoostX began fixing a jackpot round's `xBase` and boost before it first sends the round. Every attempt
sends that result: a retry or a re-send after a reopen carries the same `round` `N + 1`, the same boost and
`jackpot: true, final: true`, and neither a later gamepass's `x` nor a new exchange rate recalculates it. A jackpot
round therefore keeps the `x` of the entry during which BoostX fixed its result, normally the entry that first sent it,
and BoostX computes its X as `playerX` does, so `playerX` on that `xBase` gives the X the player saw. The token carries
no `xBase`: when the first attempt never reached the partner and a later entry changed `x`, the token alone cannot tell
which entry's `x` applies. An older jackpot round, one BoostX prepared before the change and had not recorded by then,
is the exception: its first attempt since the change can carry another `xBase` and boost, and every further attempt
keeps them. Why: v1.1.0 said that a jackpot round sent again could carry another boost and took the `x` of the entry
that sent it again. No SDK behaviour changes and no vector changes: every rule affected is informative or documentation
guidance, so an SDK that conforms to v1.1.0 conforms to v1.2.0. See the decision [2026-11-06. A jackpot round keeps its
result](SPEC.md#decision-jackpot-result-fixed).

Rules: [GAMEPASS-44](SPEC.md#gamepass-44), the documentation guidance on which `xBase` a partner passes;
[GAMEPASS-21](SPEC.md#gamepass-21), [INBOUND-49](SPEC.md#inbound-49) and [INBOUND-50](SPEC.md#inbound-50), whose item
(c) now states the exception for older jackpot rounds, all informative; the jackpot bullet of section 1.6; and the new
decision in section 13.

The spec now names the partner docs' sections by their current titles: Keys and Test integration (sections 5 and 10),
Integration details (section 8), and the Settlement page's POST /api/integration/settlement and Retries
([SETTLE-64](SPEC.md#settle-64)).

## v1.1.0

Every builder that signs a GID (`gid.build`, `gamepass.create`, `settlement.create`, and `client.submit` through the
settlement builder) now refuses a `partner`, `user` or `bet` that contains U+003A `:` or is longer than its limit, 32
(`partner`), 64 (`user`) or 96 (`bet`) Unicode scalar values, with `invalid_claim` naming that id. Only U+003A is
refused, nothing is normalised before the checks, and an empty id stays `missing_claim`. The id checks still run after
every other parameter check, per id: `partner`, then `user`, then `bet`, each well-formed, then free of `:`, then within
its length, before the next. Parsing an inbound token checks neither rule, since a game opened before these rules keeps
its gid for life. Why: BoostX identifies a game by the three ids and refuses a gamepass whose ids break either rule.
v1.0.x required an SDK to check neither, so an SDK that conforms to v1.0.x does not conform to v1.1.0. See the decision
[2026-11-03. Ids hold no `:` and have bounded lengths](SPEC.md#decision-gid-id-rules).

Rules: reversed for builders, [GID-09](SPEC.md#gid-09), [GID-10](SPEC.md#gid-10), [SETTLE-12](SPEC.md#settle-12) and
[SETTLE-74](SPEC.md#settle-74); the id step of every check order, [GAMEPASS-07](SPEC.md#gamepass-07) step 3,
[KEYS-19](SPEC.md#keys-19) list A step 3 and list B step 8 and [SETTLE-31](SPEC.md#settle-31) step 12, with
[SETTLE-11](SPEC.md#settle-11), [GAMEPASS-09](SPEC.md#gamepass-09), [P-builder-ids](SPEC.md#p-builder-ids),
[P-check-order](SPEC.md#p-check-order) and the `gid.build` entry of section 3.1; [GID-37](SPEC.md#gid-37), whose
characters each count as one against the limits; section 8.9; the new decision in section 13; and
[AGENTS.md](AGENTS.md), whose list of documentation duties now asks an SDK's documentation to state the `:` rule and the
length limits.

Vectors (case counts in section 12.3: `gidgp.json` 245 → 276, `inbound.json` 390 → 393, `settle.json` 268 → 275):

- Renamed, now refusals: `gidgp-gid-build-colon-not-checked` → `gidgp-gid-build-colon-refused` (`invalid_claim`,
  `user`); `gidgp-gid-build-long-id` → `gidgp-gid-build-long-bet-refused` and `settle-create-ids-long` →
  `settle-create-ids-long-refused` (`invalid_claim`, `bet`).
- Split, whitespace still accepted and `:` now refused: `gidgp-gamepass-colon-and-whitespace-ids` →
  `gidgp-gamepass-whitespace-ids` and `gidgp-gamepass-colon-user-refused`; `settle-create-ids-colon-and-whitespace` →
  `settle-create-ids-whitespace` and `settle-create-ids-colon-refused`.
- Changed: `inbound-booster-gid-exotic-ids` has no `:` in its ids any more, since its `sigs` entry is signed with the
  SDK's own `gid.build`; `inbound-booster-gid-colon-ids-verified` covers an inbound `:` instead.
- Added to `gidgp.json`: `gidgp-gid-build-colon-partner-alone`, `gidgp-gid-build-colon-partner-start`,
  `gidgp-gid-build-colon-partner-end`, `gidgp-gid-build-colon-user-alone`, `gidgp-gid-build-colon-user-start`,
  `gidgp-gid-build-colon-user-end`, `gidgp-gid-build-colon-bet-alone`, `gidgp-gid-build-colon-bet-start`,
  `gidgp-gid-build-colon-bet-end`, `gidgp-gid-build-fullwidth-colon-accepted`, `gidgp-gid-build-ids-at-limit`,
  `gidgp-gid-build-ids-at-limit-astral`, `gidgp-gid-build-user-at-limit-mixed`, `gidgp-gid-build-partner-over-limit`,
  `gidgp-gid-build-user-over-limit`, `gidgp-gid-build-bet-over-limit`, `gidgp-gid-build-partner-over-limit-astral`,
  `gidgp-gid-build-user-over-limit-astral`, `gidgp-gid-build-bet-over-limit-astral`,
  `gidgp-gid-build-user-over-limit-combining`, `gidgp-gid-build-order-partner-colon-before-user-ill-formed`,
  `gidgp-gid-build-order-partner-length-before-user-ill-formed`,
  `gidgp-gid-build-order-partner-colon-before-user-length`, `gidgp-gid-build-order-user-length-before-bet-colon`,
  `gidgp-gamepass-colon-partner-refused`, `gidgp-gamepass-colon-bet-refused`, `gidgp-gamepass-ids-at-limit`,
  `gidgp-gamepass-bet-over-limit`, `gidgp-gamepass-order-colon-after-currency`,
  `gidgp-gamepass-order-length-after-amount`.
- Added to `settle.json`: `settle-create-colon-partner-refused`, `settle-create-colon-bet-refused`,
  `settle-create-ids-at-limit`, `settle-create-user-over-limit-astral`, `settle-create-order-colon-after-status`,
  `settle-client-colon-refused`.
- Added to `inbound.json`: `inbound-booster-gid-colon-ids-verified`, `inbound-booster-gid-long-ids-verified`,
  `inbound-checkbet-gid-colon-and-long-ids-verified`.

## v1.0.1

The glossary no longer names the string BoostX joins from the GID's `partner`, `user` and `bet`, and the rules that
mentioned it describe it instead, so that it is not mistaken for the partner's own bet id, the `bet` part alone. No rule
and no vector changed: an SDK that conforms to v1.0.0 conforms to v1.0.1.

## v1.0.0

First public release of the specification and its conformance vectors.
