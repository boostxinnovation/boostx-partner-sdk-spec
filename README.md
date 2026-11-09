# BoostX partner SDK specification

This repository defines what a BoostX partner SDK does, with conformance vectors that test it: key loading and key
stores, the tokens a partner signs and verifies, the signed GID, the three endpoints BoostX calls on a partner
(`/set-boost`, `/check-bet`, `/verify-keys`), the settlement client and the X helpers.

It is for partners who integrate BoostX in a language that has no reference SDK, for the AI coding agents they use to
generate one, and for anyone who maintains a partner SDK.

**Spec version: v1.2.0.** Releases are listed in [CHANGELOG.md](CHANGELOG.md), and each is tagged `vX.Y.Z` in this
repository, https://github.com/boostxinnovation/boostx-partner-sdk-spec.

| Path | Content |
|------|---------|
| [SPEC.md](SPEC.md) | The specification: every rule under its own id |
| [AGENTS.md](AGENTS.md) | The guide an AI coding agent follows to generate a conformant SDK |
| [vectors/](vectors/) | The conformance vectors, with their format in [vectors/FORMAT.md](vectors/FORMAT.md) and three golden files in `vectors/golden/` |
| [tools/](tools/) | Checks that keep the spec and the vectors consistent |
| [SECURITY.md](SECURITY.md) | How to report a vulnerability |

## Reference SDKs

| Language | Repository | Package | Version |
|----------|------------|---------|---------|
| JavaScript and TypeScript | [boostxinnovation/boostx-partner-sdk-js](https://github.com/boostxinnovation/boostx-partner-sdk-js) | npm `@boostxinnovation/partner-sdk` | v1.1.0 |
| Go | [boostxinnovation/boostx-partner-sdk-go](https://github.com/boostxinnovation/boostx-partner-sdk-go) | module `github.com/boostxinnovation/boostx-partner-sdk-go` | v1.1.0 |

Both conform to boostx-partner-sdk-spec v1.1.0.

From v1.2.0 the reference SDKs carry this spec's version number: release vX.Y.Z of each implements spec vX.Y.Z, and
the spec and both SDKs are released together.

## Generating an SDK in another language

Point your AI coding agent at [AGENTS.md](AGENTS.md). An SDK that passes every vector, skipping only what
[vectors/FORMAT.md](vectors/FORMAT.md) section 7 allows, passes the three golden files in `vectors/golden/`, and meets
the rules AGENTS.md lists as covered by no vector, conforms to boostx-partner-sdk-spec at the version it was built
from; its README says so, with the commit. The vectors sample the input space rather than exhaust it, so conformance is
the claim to make, never identical behaviour to another SDK.

BoostX has no test environment for partners: test a new SDK with demo games, and with Test integration on the
dashboard.

To check the repository itself:

```sh
python3 tools/check_vectors.py
python3 tools/check_marks.py --catalogue --docs-pointers --platform-notes --agents
python3 -m unittest discover tools
```

## Partner docs

The partner docs, which BoostX opens to its partners, describe the integration for them: onboarding, keys and the
game. They give context; the behaviour of an SDK is defined here.

## Contact

Questions about the specification: sdk@boostxinnovation.com. Issues are disabled in this repository. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE).
