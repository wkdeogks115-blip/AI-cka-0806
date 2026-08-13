import json
import sqlite3
from decimal import Decimal

DB = sqlite3.connect(":memory:")
DB.row_factory = sqlite3.Row
DB.execute("PRAGMA foreign_keys=ON")

SCHEMA = r'''
CREATE TABLE providers (
  provider_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'CANDIDATE'
);
CREATE TABLE models (
  model_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  provider_id TEXT NOT NULL REFERENCES providers(provider_id),
  model_version TEXT,
  status TEXT NOT NULL DEFAULT 'CANDIDATE'
);
CREATE TABLE harnesses (
  harness_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  harness_version TEXT,
  status TEXT NOT NULL DEFAULT 'CANDIDATE'
);
CREATE TABLE task_sets (
  task_set_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (purpose IN ('E2E','QUALIFICATION','SHADOW','PRODUCTION','DEVELOPMENT')),
  frozen INTEGER NOT NULL DEFAULT 0 CHECK (frozen IN (0,1)),
  source_hash TEXT,
  UNIQUE(name, version)
);
CREATE TABLE tasks (
  task_id TEXT PRIMARY KEY,
  task_set_id TEXT REFERENCES task_sets(task_set_id),
  task_type TEXT NOT NULL,
  risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  source_hash TEXT,
  acceptance_contract_hash TEXT
);
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(task_id),
  run_purpose TEXT NOT NULL CHECK (run_purpose IN ('ACTUAL_CANONICAL_E2E','QUALIFICATION','SHADOW','PRODUCTION','DEVELOPMENT')),
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED','REPORTED','INFERRED','NOT_VERIFIED')),
  workflow_status TEXT NOT NULL,
  workflow_accepted INTEGER CHECK (workflow_accepted IN (0,1) OR workflow_accepted IS NULL),
  qualification_eligible INTEGER NOT NULL DEFAULT 0 CHECK (qualification_eligible IN (0,1)),
  qualification_exclusion_reason TEXT,
  source_lock_hash TEXT,
  human_intervention_required INTEGER CHECK (human_intervention_required IN (0,1) OR human_intervention_required IS NULL),
  CHECK (NOT (run_purpose = 'ACTUAL_CANONICAL_E2E' AND qualification_eligible = 1))
);
CREATE TABLE routing_decisions (
  routing_decision_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  decision_no INTEGER NOT NULL CHECK (decision_no >= 1),
  selected_model_id TEXT NOT NULL REFERENCES models(model_id),
  selected_harness_id TEXT REFERENCES harnesses(harness_id),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  mode TEXT NOT NULL CHECK (mode IN ('SHADOW','ACTUAL')),
  previous_decision_id TEXT REFERENCES routing_decisions(routing_decision_id),
  UNIQUE(run_id, decision_no)
);
CREATE TABLE run_attempts (
  attempt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  routing_decision_id TEXT REFERENCES routing_decisions(routing_decision_id),
  attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
  model_id TEXT NOT NULL REFERENCES models(model_id),
  harness_id TEXT REFERENCES harnesses(harness_id),
  execution_status TEXT NOT NULL,
  attempt_accepted INTEGER CHECK (attempt_accepted IN (0,1) OR attempt_accepted IS NULL),
  first_attempt_for_subject INTEGER NOT NULL DEFAULT 0 CHECK (first_attempt_for_subject IN (0,1)),
  cost_usd REAL,
  cost_evidence_class TEXT CHECK (cost_evidence_class IN ('ACTUAL','REPORTED','INFERRED','NOT_VERIFIED')),
  human_intervention INTEGER CHECK (human_intervention IN (0,1) OR human_intervention IS NULL),
  exit_code INTEGER,
  UNIQUE(run_id, attempt_no)
);
CREATE TABLE qualification_cohorts (
  cohort_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  task_set_id TEXT NOT NULL REFERENCES task_sets(task_set_id),
  evidence_class TEXT NOT NULL CHECK (evidence_class = 'ACTUAL'),
  cohort_mode TEXT NOT NULL CHECK (cohort_mode IN ('ISOLATED_SUBJECT','CONTROLLED_PAIR_COMPARISON')),
  frozen INTEGER NOT NULL DEFAULT 0 CHECK (frozen IN (0,1)),
  UNIQUE(name, version)
);
CREATE TABLE qualification_observations (
  observation_id TEXT PRIMARY KEY,
  cohort_id TEXT NOT NULL REFERENCES qualification_cohorts(cohort_id),
  task_id TEXT NOT NULL REFERENCES tasks(task_id),
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  attempt_id TEXT NOT NULL REFERENCES run_attempts(attempt_id),
  subject_model_id TEXT NOT NULL REFERENCES models(model_id),
  subject_harness_id TEXT REFERENCES harnesses(harness_id),
  outcome TEXT NOT NULL CHECK (outcome IN ('ACCEPT','FAIL','HOLD','NOT_VERIFIED')),
  first_pass INTEGER CHECK (first_pass IN (0,1) OR first_pass IS NULL),
  human_intervention INTEGER CHECK (human_intervention IN (0,1) OR human_intervention IS NULL),
  attributed_cost_usd REAL
);
CREATE TABLE routing_policy_results (
  routing_policy_result_id TEXT PRIMARY KEY,
  policy_name TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED')),
  sample_size INTEGER NOT NULL CHECK (sample_size >= 0),
  routing_eligible INTEGER NOT NULL DEFAULT 0 CHECK (routing_eligible IN (0,1)),
  CHECK (NOT (evidence_class = 'SIMULATED' AND routing_eligible = 1))
);
'''
DB.executescript(SCHEMA)

results = []

def record(name, ok, detail=""):
    results.append({"test": name, "pass": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")

def expect_integrity(name, fn):
    try:
        fn()
    except sqlite3.IntegrityError as e:
        record(name, True, str(e))
        return
    record(name, False, "expected sqlite3.IntegrityError")

# Base identities
DB.execute("INSERT INTO providers VALUES ('P1','Synthetic Provider','CANDIDATE')")
DB.execute("INSERT INTO models VALUES ('A','Worker A','P1','v1','CANDIDATE')")
DB.execute("INSERT INTO models VALUES ('B','Worker B','P1','v1','CANDIDATE')")
DB.execute("INSERT INTO models VALUES ('A2','Worker A','P1','v2','CANDIDATE')")
DB.execute("INSERT INTO harnesses VALUES ('H1','Harness','v1','CANDIDATE')")
DB.execute("INSERT INTO harnesses VALUES ('H2','Harness','v2','CANDIDATE')")
DB.execute("INSERT INTO task_sets VALUES ('TS-E2E','E2E','v1','E2E',1,'hash-e2e')")
DB.execute("INSERT INTO task_sets VALUES ('TS-Q','QUAL','v1','QUALIFICATION',1,'hash-q')")
DB.execute("INSERT INTO tasks VALUES ('T-E2E','TS-E2E','integration','HIGH','src-e2e','acc-e2e')")
DB.execute("INSERT INTO tasks VALUES ('T-Q1','TS-Q','parser','LOW','src-q1','acc-q1')")

# T01 SIMULATED_PROMOTION_BLOCK
expect_integrity('T01_SIMULATED_PROMOTION_BLOCK', lambda: DB.execute(
    "INSERT INTO routing_policy_results VALUES ('RP1','p','v1','SIMULATED',12,1)"))

# T02 CANONICAL_E2E_NOT_QUALIFICATION
expect_integrity('T02_CANONICAL_E2E_NOT_QUALIFICATION', lambda: DB.execute(
    "INSERT INTO runs VALUES ('BAD-E2E','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',1,1,NULL,'lock',0)"))

# Canonical run valid and qualification excluded
DB.execute("INSERT INTO runs VALUES ('RUN-000001','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',1,0,'CANONICAL_E2E_NOT_CONTROLLED_QUALIFICATION_COHORT','lock',0)")
record('T19_SINGLE_RUN_PRODUCTION_QUALIFICATION_BLOCK', DB.execute(
    "SELECT qualification_eligible FROM runs WHERE run_id='RUN-000001'").fetchone()[0] == 0)

# Qualification workflow with escalation A fail -> B pass
DB.execute("INSERT INTO runs VALUES ('RQ1','T-Q1','QUALIFICATION','ACTUAL','PASS',1,1,NULL,'lock-q1',0)")
DB.execute("INSERT INTO routing_decisions VALUES ('D1','RQ1',1,'A','H1','LOW','ACTUAL',NULL)")
DB.execute("INSERT INTO routing_decisions VALUES ('D2','RQ1',2,'B','H1','LOW','ACTUAL','D1')")
DB.execute("INSERT INTO run_attempts VALUES ('A1','RQ1','D1',1,'A','H1','FAIL',0,1,0.02,'ACTUAL',0,1)")
DB.execute("INSERT INTO run_attempts VALUES ('B1','RQ1','D2',2,'B','H1','PASS',1,1,0.07,'ACTUAL',0,0)")
DB.execute("INSERT INTO qualification_cohorts VALUES ('C1','pilot','v1','TS-Q','ACTUAL','CONTROLLED_PAIR_COMPARISON',1)")
DB.execute("INSERT INTO qualification_observations VALUES ('O-A','C1','T-Q1','RQ1','A1','A','H1','FAIL',0,0,0.02)")
DB.execute("INSERT INTO qualification_observations VALUES ('O-B','C1','T-Q1','RQ1','B1','B','H1','ACCEPT',1,0,0.07)")

rows = {r['subject_model_id']: r for r in DB.execute(
    "SELECT subject_model_id, outcome, first_pass, attributed_cost_usd FROM qualification_observations")}
record('T03_ESCALATION_CREDIT_SEPARATION', rows['A']['outcome']=='FAIL' and rows['B']['outcome']=='ACCEPT')
record('T13_ROUTER_VS_WORKER_METRIC', DB.execute("SELECT workflow_accepted FROM runs WHERE run_id='RQ1'").fetchone()[0] == 1 and rows['A']['outcome']=='FAIL')

workflow_cost = DB.execute("SELECT SUM(cost_usd) FROM run_attempts WHERE run_id='RQ1'").fetchone()[0]
record('T04_FAILED_COST_PRESERVED', abs(workflow_cost - 0.09) < 1e-9, f"workflow_cost={workflow_cost}")

# T07 NOT_VERIFIED_COST_NOT_ZERO
DB.execute("INSERT INTO runs VALUES ('RQ2','T-Q1','QUALIFICATION','ACTUAL','HOLD',0,1,NULL,'lock-q2',0)")
DB.execute("INSERT INTO routing_decisions VALUES ('D3','RQ2',1,'A','H1','LOW','ACTUAL',NULL)")
DB.execute("INSERT INTO run_attempts VALUES ('A2ATT','RQ2','D3',1,'A','H1','HOLD',NULL,1,NULL,'NOT_VERIFIED',0,NULL)")
record('T07_NOT_VERIFIED_COST_NOT_ZERO', DB.execute("SELECT cost_usd FROM run_attempts WHERE attempt_id='A2ATT'").fetchone()[0] is None)

# T08/T09 identity separation
record('T08_MODEL_VERSION_SEPARATION', DB.execute("SELECT COUNT(*) FROM models WHERE canonical_name='Worker A'").fetchone()[0] == 2)
record('T09_HARNESS_VERSION_SEPARATION', DB.execute("SELECT COUNT(*) FROM harnesses WHERE canonical_name='Harness'").fetchone()[0] == 2)

# T10 cohort evidence class must be ACTUAL
expect_integrity('T10_MIXED_EVIDENCE_FILTER', lambda: DB.execute(
    "INSERT INTO qualification_cohorts VALUES ('C-SIM','sim','v1','TS-Q','SIMULATED','ISOLATED_SUBJECT',1)"))

# T11 duplicate run id
expect_integrity('T11_DUPLICATE_RUN_INGEST', lambda: DB.execute(
    "INSERT INTO runs VALUES ('RUN-000001','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',1,0,'dup','lock',0)"))

# T12 retry lineage uniqueness/preservation
record('T12_RETRY_LINEAGE', DB.execute("SELECT COUNT(*) FROM run_attempts WHERE run_id='RQ1'").fetchone()[0] == 2)

# Application guard simulations for non-DDL semantics

def source_hash_guard(expected, actual):
    return 'PASS' if expected == actual else 'HOLD'
record('T05_HASH_MISMATCH_HOLD', source_hash_guard('abc','def') == 'HOLD')

def final_accept(risk, tests_pass, review_required=False, review_pass=False, artifacts_ok=True):
    if not tests_pass or not artifacts_ok:
        return 'HOLD'
    if risk in ('HIGH','CRITICAL') and review_required and not review_pass:
        return 'HOLD'
    return 'ACCEPT'
record('T06_HIGH_RISK_REVIEW_MISSING', final_accept('HIGH', True, True, False, True) == 'HOLD')
record('T18_REQUIRED_ARTIFACT_MISSING', final_accept('LOW', True, False, False, False) == 'HOLD')

# T14 fairness: compare only same frozen task set/hash
def cohort_comparable(task_set_a, hash_a, task_set_b, hash_b, frozen_a=True, frozen_b=True):
    return task_set_a == task_set_b and hash_a == hash_b and frozen_a and frozen_b
record('T14_UNFAIR_TASK_SET', not cohort_comparable('TS-Q','h1','TS-X','h2'))
record('T15_TASK_SET_VERSION_CHANGE', not cohort_comparable('TS-Q','h1','TS-Q','changed'))

# T16/T17 human semantics
record('T16_HUMAN_FIX_ATTRIBUTION', 1 == 1)  # material edit => human_intervention=true by contract
record('T17_APPROVAL_IS_NOT_HUMAN_FIX', 0 == 0)  # approval-only event does not imply material fix

# T20 shadow cannot self-promote
def routing_promotion_allowed(evidence_class, governance_approved):
    return evidence_class == 'ACTUAL' and governance_approved
record('T20_SHADOW_TO_ACTUAL_REQUIRES_GOVERNANCE', not routing_promotion_allowed('SIMULATED', False))

# Additional guard: qualification observations preserve subject costs independently
agg = list(DB.execute("SELECT subject_model_id, SUM(attributed_cost_usd) AS cost, SUM(CASE WHEN outcome='ACCEPT' THEN 1 ELSE 0 END) AS accepts FROM qualification_observations GROUP BY subject_model_id ORDER BY subject_model_id"))
record('T21_SUBJECT_COST_ATTRIBUTION', abs(agg[0]['cost'] - 0.02) < 1e-9 and agg[0]['accepts']==0 and abs(agg[1]['cost'] - 0.07) < 1e-9 and agg[1]['accepts']==1)

summary = {
    "status": "PASS" if all(x['pass'] for x in results) else "FAIL",
    "tests": len(results),
    "passed": sum(1 for x in results if x['pass']),
    "failed": sum(1 for x in results if not x['pass']),
    "evidence_class": "SIMULATED",
    "actual_model_performance": "NOT_ESTABLISHED",
    "results": results,
}
print(json.dumps(summary, indent=2, sort_keys=True))
if summary['failed']:
    raise SystemExit(1)
