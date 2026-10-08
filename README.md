# Signpost Contracts — Soroban Infrastructure for Community Accountability on Stellar

![CI](https://github.com/Signpost-Labs/signpost-contracts/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Stellar](https://img.shields.io/badge/Stellar-Soroban-7D00FF?logo=stellar&logoColor=white)

Signpost helps communities track project commitments, milestones, progress, evidence, and responses. This Rust/Soroban workspace runs on Stellar, but its current contracts still support the previous product and do not represent accountability records. The proposed design for anchoring project revision hashes on Soroban is tracked in [issue #1](https://github.com/Stellar-Signpost/signpost-contracts/issues/1); it is not implemented yet.

## Table of Contents

- [Architecture and tree](#architecture-and-tree)
- [How the project uses Stellar](#how-the-project-uses-stellar)
- [Environment and network configuration](#environment-and-network-configuration)
- [Prerequisites](#prerequisites)
- [Build and test](#build-and-test)
- [Security](#security)

## Architecture and tree

The Cargo workspace builds six crates: `shared-types` contains shared definitions; `registration`, `verification`, `progress`, and `scout_access` contain the current product contracts; `chaos-tests` exercises cross-contract and adversarial behavior. Contract entry points and tests live under each crate’s `src/` and `tests/` directories. `bindings/` contains TypeScript clients and examples, `migrations/` records state/schema changes, and `scripts/` plus `testnet/` hold deployment and operational tooling.

Contracts use Soroban SDK 25 and communicate through addresses and published interfaces. Events and storage keys are consumed by backend/indexer services, so interface or key changes may affect deployed data and downstream clients.

## How the project uses Stellar

The proposed accountability design would publish a hash and timestamp for a project revision on Soroban while keeping project content, personal information, and evidence files off-chain. An anchor could show that a particular revision existed at a given time; it would not verify the truth of its claims. This is design work only, not a live feature.

## Environment and network configuration

Copy `.env.example` to `.env` for deployment and integration tooling. Its comments document every variable. The main groups are deployment credentials (`DEPLOYER_SECRET`, `ADMIN_SECRET`), target network (`STELLAR_NETWORK`, `HORIZON_URL`, `SOROBAN_RPC_URL`), deployed contract addresses, and backend integration (`DATABASE_URL`, `JWT_SECRET`, SEP-10 settings). Keep secret keys out of source control; use testnet accounts for development. Rust compilation itself uses the toolchain pinned in `rust-toolchain.toml` and does not require deployment secrets.

## Prerequisites

| Tool | Notes |
| --- | --- |
| **Rust** | pinned in `rust-toolchain.toml` |
| **Node.js** | 18+ (repository tooling) |
| **Stellar CLI** | deployment scripts |

## Build and test

From the repository root, run:

```sh
cargo build --workspace
cargo test --workspace
cargo fmt --all -- --check
npm install && npm test
```

Cargo builds, tests, and checks Rust formatting. Jest covers repository tooling. Deployment scripts require the relevant `.env` values and are documented in [docs/](docs/) and [scripts/](scripts/). When changing storage keys, events, authorization, or interfaces, update bindings and migration notes with the implementation.

See [SECURITY.md](SECURITY.md) and [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) before contributing.

## Security

- **Never commit secrets** — keep keys, seed phrases, and `.env` files out of source control.
- **Testnet values have no real-world value**; treat testnet deployments as experimental.
- **Keys never leave the wallet** — signing is delegated to the user's Stellar wallet; the app does not store secret keys.
- Report vulnerabilities per `SECURITY.md` where present rather than opening a public issue.

## License

MIT — see [`LICENSE`](LICENSE).
