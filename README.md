<p align="center">
  <img src="https://img.shields.io/badge/SHAKTI-Governance_Substrate-blueviolet?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0xMiAyTDIgN2wxMCA1IDEwLTV6Ii8+PHBhdGggZD0iTTIgMTdsMTAgNSAxMC01Ii8+PHBhdGggZD0iTTIgMTJsMTAgNSAxMC01Ii8+PC9zdmc+" alt="SHAKTI Badge"/>
  <br/>
  <img src="https://img.shields.io/badge/tests-23%2F23_passing-brightgreen?style=flat-square" alt="Tests"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/store-SQLite_append--only-orange?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/api-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="License"/>
</p>

<h1 align="center">⚡ SHAKTI — Governance Execution Substrate</h1>

<p align="center">
  <strong>Telemetry Continuity · Constitutional Bounds · Operational Truth</strong>
  <br/>
  <em>A provably correct, self-policing governance runtime for critical infrastructure telemetry.</em>
</p>

---

## 🧬 What Is SHAKTI?

**SHAKTI** is a **governance execution substrate** — not a monitoring dashboard, not a metrics pipeline. It is a *self-policing runtime* that enforces **constitutional authority bounds** on every system component, produces **cryptographically verifiable continuity proofs** for telemetry data, and assembles **evidence-backed operational truth** about device state.

Every identifier is **deterministic** (SHA-256 from inputs). Every store is **append-only** (no updates, no deletes). Every observation is **read-only**. Every unauthorized operation is **blocked before it is logged**.

```
┌─────────────────────────────────────────────┐
│            API SPINE SURFACE                │
│  /health  /snapshot  /probe  /truth  /flow  │
│              /constitution                   │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────────────┐
    │              │                      │
┌───▼──────┐  ┌───▼──────────┐  ┌────────▼──────────┐
│TELEMETRY │  │OBSERVABILITY │  │ OPERATIONAL TRUTH  │
│          │  │              │  │                    │
│ probe    │  │ snapshot     │  │ truth assembler    │
│ flow     │  │ engine       │  │ (evidence-backed   │
│ tracker  │  │ replay-safe  │  │  claims + proof)   │
│ heartbeat│  │ observer     │  │                    │
└──────────┘  └──────────────┘  └────────────────────┘
                   │
         ┌─────────▼──────────────┐
         │  CONSTITUTIONAL BOUNDS  │
         │                        │
         │ authority_bounds.py    │
         │ bound_checker.py       │
         │ violation_emitter.py   │
         └─────────┬──────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐  ┌─────▼──┐  ┌───────▼─────┐
│ingest  │  │signal  │  │ gov_store   │
│_store  │  │_log    │  │ spine_store │
└────────┘  └────────┘  └─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **pip**

### Install & Run

```bash
# Clone the repository
git clone https://github.com/AnshGupta007/shakti-substrate.git
cd shakti-substrate

# Install dependencies
pip install -r requirements.txt

# Run the full 23-test validation suite
python -m pytest tests/test_substrate.py -v

# Run the interactive demo
python demo/demo_substrate.py

# Run the adversarial simulation
python simulation/inject_bound_violation.py

# Start the API server
uvicorn api.spine_api:app --host 0.0.0.0 --port 8000
```

---

## 🏗️ Architecture

### Design Principles

| Principle | How It's Enforced |
|:----------|:------------------|
| 🔒 **Observability never mutates** | Snapshot engine & observer are strictly READ-ONLY |
| 🧱 **Governance is an execution substrate** | Constitutional bounds checked before every store access |
| 🔑 **Deterministic identity** | All IDs via `SHA-256(input tuple)` — no `random()`, no `datetime.now()` |
| 📝 **Append-only storage** | All 4 stores: INSERT only — no UPDATE, no DELETE |
| 🚫 **Non-negotiable blocking** | Violations are BLOCKED *before* the event is emitted |
| 🔗 **Chain-hash continuity** | Continuity proofs use chained SHA-256 of trace_ids |

### Constitutional Authority Map

Every component has a **hardcoded, declarative constitution** defining exactly what it can read, write, and emit. This cannot be changed at runtime.

```
Component            │ read                              │ write            │ emit
─────────────────────┼───────────────────────────────────┼──────────────────┼──────────────────
INGESTION_LAYER      │ —                                 │ ingestion_store  │ —
SIGNAL_ENGINE        │ ingestion_store, signal_log       │ signal_log       │ —
GOVERNANCE_ROUTER    │ ingestion_store, signal_log,      │ gov_store        │ All 8 GOV_* types
                     │ gov_store                         │                  │
BHIV_MODULE          │ —                                 │ —                │ —
TANTRA_MODULE        │ —                                 │ —                │ —
TELEMETRY_SPINE      │ ingestion_store, signal_log,      │ spine_store      │ GOV_BOUND_VIOLATION
                     │ gov_store                         │                  │
API_LAYER            │ ingestion_store, signal_log,      │ —                │ GOV_SURFACE_ACCESS
                     │ gov_store, spine_store             │                  │
```

---

## 📦 Modules

<table>
  <tr>
    <th>Category</th>
    <th>Module</th>
    <th>Purpose</th>
  </tr>
  <tr>
    <td rowspan="3">📡 <strong>Telemetry</strong></td>
    <td><code>continuity_probe.py</code></td>
    <td>Chain-hash proof of sequence integrity; gap detection</td>
  </tr>
  <tr>
    <td><code>flow_tracker.py</code></td>
    <td>Multi-stage journey reconstruction (ingestion → governance)</td>
  </tr>
  <tr>
    <td><code>heartbeat_emitter.py</code></td>
    <td>Device silence detection with synthetic heartbeat injection</td>
  </tr>
  <tr>
    <td rowspan="3">🛡️ <strong>Constitution</strong></td>
    <td><code>authority_bounds.py</code></td>
    <td>Declarative permission map for all 7 system components</td>
  </tr>
  <tr>
    <td><code>bound_checker.py</code></td>
    <td>Pure function: <code>(component, op, target) → permit/deny</code></td>
  </tr>
  <tr>
    <td><code>violation_emitter.py</code></td>
    <td>BLOCK-then-emit enforcement for constitutional failures</td>
  </tr>
  <tr>
    <td rowspan="2">🔍 <strong>Observability</strong></td>
    <td><code>snapshot_engine.py</code></td>
    <td>Immutable system state capture at sequence boundaries</td>
  </tr>
  <tr>
    <td><code>replay_safe_observer.py</code></td>
    <td>Pure function over snapshots — no store reads, fully replayable</td>
  </tr>
  <tr>
    <td>✅ <strong>Truth</strong></td>
    <td><code>truth_assembler.py</code></td>
    <td>Evidence-backed claims with confidence scores across 5 claim types</td>
  </tr>
  <tr>
    <td rowspan="2">⚙️ <strong>Pipeline</strong></td>
    <td><code>event_types.py</code></td>
    <td>8 governance event types including <code>GOV_BOUND_VIOLATION</code></td>
  </tr>
  <tr>
    <td><code>router.py</code></td>
    <td>BHIV → TANTRA → Store pipeline with deterministic IDs</td>
  </tr>
  <tr>
    <td rowspan="4">💾 <strong>Spine (Stores)</strong></td>
    <td><code>ingestion_store.py</code></td>
    <td>Append-only telemetry record store</td>
  </tr>
  <tr>
    <td><code>signal_log.py</code></td>
    <td>Append-only signal history</td>
  </tr>
  <tr>
    <td><code>gov_store.py</code></td>
    <td>Append-only governance event ledger</td>
  </tr>
  <tr>
    <td><code>spine_store.py</code></td>
    <td>Snapshots, truth reports, continuity probes, flow reports</td>
  </tr>
  <tr>
    <td>🌐 <strong>API</strong></td>
    <td><code>spine_api.py</code></td>
    <td>6 FastAPI endpoints with bound-checking and surface access emission</td>
  </tr>
</table>

---

## 🧪 Testing

The substrate is validated by a **23-test suite** covering all 5 capabilities:

```
tests/test_substrate.py::test_probe_detects_gap_in_sequence              ✅
tests/test_substrate.py::test_probe_returns_continuous_when_no_gaps       ✅
tests/test_substrate.py::test_continuity_proof_changes_on_record_swap    ✅
tests/test_substrate.py::test_heartbeat_emitted_on_silence               ✅
tests/test_substrate.py::test_probe_is_readonly                          ✅
tests/test_substrate.py::test_ingestion_layer_cannot_write_to_gov_store  ✅
tests/test_substrate.py::test_api_layer_cannot_write_to_any_store        ✅
tests/test_substrate.py::test_tantra_module_has_no_read_or_write_perms   ✅
tests/test_substrate.py::test_permitted_operation_returns_permitted_true  ✅
tests/test_substrate.py::test_violation_emits_gov_bound_violation_event  ✅
tests/test_substrate.py::test_violation_is_always_blocked_before_emission✅
tests/test_substrate.py::test_snapshot_is_immutable_after_creation        ✅
tests/test_substrate.py::test_observer_is_pure_same_snapshot_same_result ✅
tests/test_substrate.py::test_snapshot_taken_without_writes              ✅
tests/test_substrate.py::test_replay_produces_same_snapshot              ✅
tests/test_substrate.py::test_truth_claim_has_evidence                   ✅
tests/test_substrate.py::test_continuity_intact_claim_on_clean_data      ✅
tests/test_substrate.py::test_governance_escalated_claim_fires           ✅
tests/test_substrate.py::test_bound_compliant_claim_fails_on_violation   ✅
tests/test_substrate.py::test_truth_id_is_deterministic                  ✅
tests/test_substrate.py::test_flow_tracks_full_journey                   ✅
tests/test_substrate.py::test_flow_detects_blocked_stage                 ✅
tests/test_substrate.py::test_flow_report_is_readonly                    ✅
```

| Capability | Tests | Status |
|:-----------|:-----:|:------:|
| Telemetry Continuity | 5 | 🟢 5/5 |
| Constitutional Bounds | 6 | 🟢 6/6 |
| Snapshot Observability | 4 | 🟢 4/4 |
| Operational Truth | 5 | 🟢 5/5 |
| Flow Tracker | 3 | 🟢 3/3 |

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|:------:|:---------|:------------|
| `GET` | `/spine/health` | System health status & store connectivity |
| `POST` | `/spine/snapshot` | Capture immutable system snapshot at a sequence boundary |
| `POST` | `/spine/probe` | Run continuity probe with chain-hash verification |
| `GET` | `/spine/flow/{trace_id}` | Trace a telemetry record across all 6 pipeline stages |
| `POST` | `/spine/truth` | Assemble evidence-backed operational truth for a device |
| `GET` | `/spine/constitution/{component}` | Inspect a component's constitutional permissions |

Every endpoint emits a `GOV_SURFACE_ACCESS` event after responding. All timestamps are injected — `datetime.now()` is never called.

```bash
# Example: Take a snapshot
curl -X POST http://localhost:8000/spine/snapshot \
  -H "Content-Type: application/json" \
  -d '{"at_sequence": 5, "timestamp": "2026-05-28T00:05:00"}'

# Example: Assemble truth
curl -X POST http://localhost:8000/spine/truth \
  -H "Content-Type: application/json" \
  -d '{"device_id": "GRID-RELAY-01", "timestamp": "2026-05-28T00:06:00"}'
```

---

## 🔐 Constitutional Enforcement

SHAKTI's constitutional bounds are **hardcoded** — no runtime actor can widen its own permissions.

### How It Works

```
1. Component requests operation  ──→  bound_checker.check()
                                            │
                              ┌─────────────┴──────────────┐
                              │                            │
                         ✅ PERMITTED                  ❌ DENIED
                              │                            │
                       Operation proceeds         Operation BLOCKED
                                                          │
                                              GOV_BOUND_VIOLATION
                                              emitted to gov_store
                                              (decision = "BLOCK")
```

### Adversarial Simulation

```bash
python simulation/inject_bound_violation.py
```

```
Attempt 1: INGESTION_LAYER → write → gov_store     → ❌ BLOCKED
Attempt 2: TANTRA_MODULE   → read  → spine_store   → ❌ BLOCKED
Attempt 3: API_LAYER       → emit  → GOV_POLICY_CHECK → ❌ BLOCKED
Attempt 4: GOVERNANCE_ROUTER → read → ingestion_store → ✅ PERMITTED

Result: 3 blocked. 1 permitted. 3 GOV_BOUND_VIOLATION events emitted.
```

---

## 📊 Operational Truth

The truth assembler produces **evidence-backed claims** — it never asserts without proof.

### 5 Claim Types

| Claim Type | Confidence | Evidence Source |
|:-----------|:----------:|:---------------|
| `OPERATIONAL_STATE` | 1.0 | Last ingestion record for device |
| `SIGNAL_ACTIVE` | 0.9 (active) / 0.5 (absent) | Signal log query |
| `GOVERNANCE_ESCALATED` | 0.95 | Governance store escalation records |
| `CONTINUITY_INTACT` | 1.0 | Chain-hash continuity proof |
| `BOUND_COMPLIANT` | 1.0 / 0.0 | Constitutional bound check results |

> **Invariant:** No claim with `confidence > 0` has empty evidence.

---

## 📁 Project Structure

```
shakti-substrate/
├── api/
│   └── spine_api.py              # 6 FastAPI endpoints with bound-checking
├── bhiv/
│   └── alignment.py              # 5-rule behavioral verification
├── constitution/
│   ├── authority_bounds.py       # Declarative constitutional map
│   ├── bound_checker.py          # Pure bound check function
│   └── violation_emitter.py      # BLOCK-then-emit enforcement
├── demo/
│   └── demo_substrate.py         # Full substrate walkthrough
├── governance/
│   └── event_types.py            # 8 governance event types
├── observability/
│   ├── replay_safe_observer.py   # Pure function over snapshots
│   └── snapshot_engine.py        # Immutable state capture
├── simulation/
│   └── inject_bound_violation.py # Adversarial enforcement demo
├── spine/
│   ├── gov_store.py              # Append-only governance ledger
│   ├── ingestion_store.py        # Append-only telemetry store
│   ├── router.py                 # BHIV → TANTRA → Store pipeline
│   ├── signal_log.py             # Signal history store
│   └── spine_store.py            # Snapshots, truth, probes, flows
├── tantra/
│   └── alignment.py              # 6-rule policy gatekeeper
├── telemetry/
│   ├── continuity_probe.py       # Chain-hash continuity proof
│   ├── flow_tracker.py           # Multi-stage journey tracking
│   └── heartbeat_emitter.py      # Device silence detection
├── tests/
│   └── test_substrate.py         # 23-test validation suite
├── truth/
│   └── truth_assembler.py        # Evidence-backed truth claims
├── requirements.txt
├── REVIEW_PACKET.md              # Full audit & review document
└── README.md                     # You are here
```

---

## ⚙️ Configuration

| Environment Variable | Default | Purpose |
|:---------------------|:--------|:--------|
| `INGESTION_STORE_PATH` | `ingestion_store.db` | Ingestion store SQLite path |
| `SIGNAL_LOG_PATH` | `signal_log.db` | Signal log SQLite path |
| `GOV_STORE_PATH` | `gov_store.db` | Governance event store path |
| `SPINE_STORE_PATH` | `spine_store.db` | Spine store (snapshots, truth, etc.) path |

---

## 🔬 Hard Rules

These rules are **non-negotiable** and verified by the test suite:

| # | Rule | Verification |
|:-:|:-----|:-------------|
| 1 | No `random()` in any module | `grep` — zero matches |
| 2 | No `datetime.now()` in any module | `grep` — zero matches (only in comments) |
| 3 | No mutation of existing records | All stores: INSERT only |
| 4 | Observability does not mutate | Snapshot & observer are READ-ONLY |
| 5 | Constitutional bounds are declarative | Static dict, not runtime logic |
| 6 | Bound checker is pure | No I/O, no side effects |
| 7 | Violations BLOCK before emit | `violation_emitter` enforces ordering |
| 8 | `GOV_BOUND_VIOLATION` → `decision=BLOCK` | Hardcoded in `event_types.py` |
| 9 | Truth claims carry evidence | No claim at `confidence > 0` has `evidence=[]` |
| 10 | Continuity proof is chain-hash | SHA-256 chain of trace_ids |

---

## 📄 License

This project is licensed under the MIT License.

---

<p align="center">
  <strong>SHAKTI</strong> — Governance is not a feature. It is the substrate.
</p>
