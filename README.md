# Promiscope Soroban Contracts

This repository is the Rust/Soroban contract workspace associated with Promiscope, a community project accountability platform. The contract suite is being migrated to that purpose. Its current data models and workflows still support the previous product and do not yet represent projects, evidence submissions, or community reviews. Treat deployed and stored state as legacy until a migration plan is published.

## Workspace layout

- `contracts/registration/`, `contracts/verification/`, `contracts/progress/`, and `contracts/scout_access/` — contract crates and their Rust tests.
- `contracts/shared-types/` — shared contract types.
- `contracts/chaos-tests/` — cross-contract and adversarial test scenarios.
- `bindings/` — TypeScript bindings and usage examples.
- `migrations/` — schema and state migration notes.
- `scripts/` — build, deployment, validation, and maintenance utilities.

## Build and test

Use the Rust version pinned in `rust-toolchain.toml`. From the repository root:

```sh
cargo build --workspace
cargo test --workspace
cargo fmt --all -- --check
npm install
npm test
```

The Cargo commands build, test, and check formatting for the Rust workspace. `npm test` runs the Jest checks for repository tooling. Some integration tests require a local Stellar test environment; follow the relevant script or test documentation before running them.

## Contract changes

Document storage-key, event, authorization, and cross-contract interface changes. Storage key changes can make existing ledger data unreadable without an explicit migration. Update bindings and migration documentation alongside contract interfaces. Do not describe the existing scouting workflows as Promiscope accountability features.

## Contributions and security

Use focused Conventional Commit messages, for example `fix(progress): preserve update history`. Pull requests should describe the contract behavior and compatibility impact, link an issue, and report the checks run. Never commit secret keys, funded wallet credentials, or production configuration. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
