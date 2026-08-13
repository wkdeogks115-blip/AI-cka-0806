\set ON_ERROR_STOP on
BEGIN;

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
  status TEXT NOT NULL DEFAULT 'CANDIDATE',
  UNIQUE(provider_id, canonical_name, model_version)
);
CREATE TABLE harnesses (
  harness_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  harness_version TEXT,
  status TEXT NOT NULL DEFAULT 'CANDIDATE',
  UNIQUE(canonical_name, harness_version)
);
CREATE TABLE task_sets (
  task_set_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (purpose IN ('E2E','QUALIFICATION','SHADOW','PRODUCTION','DEVELOPMENT')),
  frozen BOOLEAN NOT NULL DEFAULT FALSE,
  source_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(name, version)
);
CREATE TABLE tasks (
  task_id TEXT PRIMARY KEY,
  task_set_id TEXT REFERENCES task_sets(task_set_id),
  task_type TEXT NOT NULL,
  risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  source_ref TEXT,
  source_hash TEXT,
  acceptance_contract_ref TEXT,
  acceptance_contract_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(task_id),
  run_purpose TEXT NOT NULL CHECK (run_purpose IN ('ACTUAL_CANONICAL_E2E','QUALIFICATION','SHADOW','PRODUCTION','DEVELOPMENT')),
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED','REPORTED','INFERRED','NOT_VERIFIED')),
  workflow_status TEXT NOT NULL,
  workflow_accepted BOOLEAN,
  qualification_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  qualification_exclusion_reason TEXT,
  source_repo TEXT,
  source_ref TEXT,
  source_sha TEXT,
  source_lock_hash TEXT,
  execution_surface_identity TEXT,
  human_intervention_required BOOLEAN,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (NOT (run_purpose = 'ACTUAL_CANONICAL_E2E' AND qualification_eligible = TRUE)),
  UNIQUE(run_id, task_id)
);
CREATE TABLE routing_decisions (
  routing_decision_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  decision_no INTEGER NOT NULL CHECK (decision_no >= 1),
  selected_model_id TEXT NOT NULL REFERENCES models(model_id),
  selected_harness_id TEXT NOT NULL REFERENCES harnesses(harness_id),
  risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  mode TEXT NOT NULL CHECK (mode IN ('SHADOW','ACTUAL')),
  decision_reason TEXT,
  qualification_result_id TEXT,
  previous_decision_id TEXT REFERENCES routing_decisions(routing_decision_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(run_id, decision_no)
);
CREATE TABLE run_attempts (
  attempt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  routing_decision_id TEXT REFERENCES routing_decisions(routing_decision_id),
  attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
  model_id TEXT NOT NULL REFERENCES models(model_id),
  harness_id TEXT NOT NULL REFERENCES harnesses(harness_id),
  execution_status TEXT NOT NULL,
  attempt_accepted BOOLEAN,
  first_attempt_for_subject BOOLEAN NOT NULL DEFAULT FALSE,
  input_tokens BIGINT CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens BIGINT CHECK (output_tokens IS NULL OR output_tokens >= 0),
  latency_ms BIGINT CHECK (latency_ms IS NULL OR latency_ms >= 0),
  cost_usd NUMERIC(18,8) CHECK (cost_usd IS NULL OR cost_usd >= 0),
  cost_evidence_class TEXT CHECK (cost_evidence_class IN ('ACTUAL','SIMULATED','REPORTED','INFERRED','NOT_VERIFIED')),
  human_intervention BOOLEAN,
  exit_code INTEGER,
  failure_taxonomy TEXT,
  receipt_hash TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  UNIQUE(run_id, attempt_no),
  UNIQUE(attempt_id, run_id, model_id, harness_id)
);
CREATE TABLE test_results (
  test_result_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES run_attempts(attempt_id),
  suite_id TEXT NOT NULL,
  suite_version TEXT,
  passed_count INTEGER CHECK (passed_count IS NULL OR passed_count >= 0),
  failed_count INTEGER CHECK (failed_count IS NULL OR failed_count >= 0),
  skipped_count INTEGER CHECK (skipped_count IS NULL OR skipped_count >= 0),
  status TEXT NOT NULL,
  evidence_hash TEXT
);
CREATE TABLE review_results (
  review_result_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  attempt_id TEXT REFERENCES run_attempts(attempt_id),
  reviewer_type TEXT NOT NULL,
  reviewer_identity TEXT,
  verdict TEXT NOT NULL,
  critical_count INTEGER NOT NULL DEFAULT 0 CHECK (critical_count >= 0),
  major_count INTEGER NOT NULL DEFAULT 0 CHECK (major_count >= 0),
  independence_attested BOOLEAN,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED','REPORTED','INFERRED','NOT_VERIFIED')),
  evidence_hash TEXT
);
CREATE TABLE evidence (
  evidence_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id),
  attempt_id TEXT REFERENCES run_attempts(attempt_id),
  evidence_type TEXT NOT NULL,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED','REPORTED','INFERRED','NOT_VERIFIED')),
  uri TEXT,
  sha256 TEXT,
  source_identity TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (run_id IS NOT NULL OR attempt_id IS NOT NULL)
);
CREATE TABLE artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id),
  attempt_id TEXT REFERENCES run_attempts(attempt_id),
  artifact_type TEXT NOT NULL,
  uri TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_size BIGINT CHECK (byte_size IS NULL OR byte_size >= 0),
  source_system TEXT NOT NULL,
  CHECK (run_id IS NOT NULL OR attempt_id IS NOT NULL)
);
CREATE TABLE qualification_cohorts (
  cohort_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  task_set_id TEXT NOT NULL REFERENCES task_sets(task_set_id),
  evidence_class TEXT NOT NULL CHECK (evidence_class = 'ACTUAL'),
  cohort_mode TEXT NOT NULL CHECK (cohort_mode IN ('ISOLATED_SUBJECT','CONTROLLED_PAIR_COMPARISON')),
  metric_contract_version TEXT NOT NULL,
  frozen BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(name, version)
);
CREATE TABLE qualification_observations (
  observation_id TEXT PRIMARY KEY,
  cohort_id TEXT NOT NULL REFERENCES qualification_cohorts(cohort_id),
  task_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  subject_model_id TEXT NOT NULL REFERENCES models(model_id),
  subject_harness_id TEXT NOT NULL REFERENCES harnesses(harness_id),
  outcome TEXT NOT NULL CHECK (outcome IN ('ACCEPT','FAIL','HOLD','NOT_VERIFIED')),
  first_pass BOOLEAN,
  human_intervention BOOLEAN,
  attributed_cost_usd NUMERIC(18,8) CHECK (attributed_cost_usd IS NULL OR attributed_cost_usd >= 0),
  FOREIGN KEY (run_id, task_id) REFERENCES runs(run_id, task_id),
  FOREIGN KEY (attempt_id, run_id, subject_model_id, subject_harness_id)
    REFERENCES run_attempts(attempt_id, run_id, model_id, harness_id),
  UNIQUE(cohort_id, task_id, subject_model_id, subject_harness_id)
);
CREATE TABLE qualification_results (
  qualification_result_id TEXT PRIMARY KEY,
  cohort_id TEXT NOT NULL REFERENCES qualification_cohorts(cohort_id),
  subject_model_id TEXT NOT NULL REFERENCES models(model_id),
  subject_harness_id TEXT NOT NULL REFERENCES harnesses(harness_id),
  task_type_segment TEXT,
  risk_segment TEXT,
  sample_size INTEGER NOT NULL CHECK (sample_size >= 0),
  accepted_rate NUMERIC(8,5) CHECK (accepted_rate IS NULL OR accepted_rate BETWEEN 0 AND 1),
  first_pass_rate NUMERIC(8,5) CHECK (first_pass_rate IS NULL OR first_pass_rate BETWEEN 0 AND 1),
  cost_per_accepted_usd NUMERIC(18,8) CHECK (cost_per_accepted_usd IS NULL OR cost_per_accepted_usd >= 0),
  retry_rate NUMERIC(8,5) CHECK (retry_rate IS NULL OR retry_rate BETWEEN 0 AND 1),
  human_intervention_rate NUMERIC(8,5) CHECK (human_intervention_rate IS NULL OR human_intervention_rate BETWEEN 0 AND 1),
  p50_latency_ms BIGINT CHECK (p50_latency_ms IS NULL OR p50_latency_ms >= 0),
  p95_latency_ms BIGINT CHECK (p95_latency_ms IS NULL OR p95_latency_ms >= 0),
  critical_failures INTEGER NOT NULL DEFAULT 0 CHECK (critical_failures >= 0),
  major_failures INTEGER NOT NULL DEFAULT 0 CHECK (major_failures >= 0),
  qualification_status TEXT NOT NULL CHECK (qualification_status IN ('PILOT','PROVISIONAL','QUALIFIED','REJECTED','HOLD')),
  routing_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (NOT routing_eligible OR qualification_status = 'QUALIFIED'),
  UNIQUE NULLS NOT DISTINCT (cohort_id, subject_model_id, subject_harness_id, task_type_segment, risk_segment)
);
ALTER TABLE routing_decisions
  ADD CONSTRAINT fk_routing_qualification_result
  FOREIGN KEY (qualification_result_id) REFERENCES qualification_results(qualification_result_id);
CREATE TABLE routing_policy_results (
  routing_policy_result_id TEXT PRIMARY KEY,
  policy_name TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED')),
  sample_size INTEGER NOT NULL CHECK (sample_size >= 0),
  workflow_accept_rate NUMERIC(8,5) CHECK (workflow_accept_rate IS NULL OR workflow_accept_rate BETWEEN 0 AND 1),
  first_route_accept_rate NUMERIC(8,5) CHECK (first_route_accept_rate IS NULL OR first_route_accept_rate BETWEEN 0 AND 1),
  escalation_rate NUMERIC(8,5) CHECK (escalation_rate IS NULL OR escalation_rate BETWEEN 0 AND 1),
  cost_per_workflow_accept_usd NUMERIC(18,8) CHECK (cost_per_workflow_accept_usd IS NULL OR cost_per_workflow_accept_usd >= 0),
  human_intervention_rate NUMERIC(8,5) CHECK (human_intervention_rate IS NULL OR human_intervention_rate BETWEEN 0 AND 1),
  routing_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  CHECK (NOT (evidence_class = 'SIMULATED' AND routing_eligible = TRUE))
);

-- Fixture identities. Direct API/no orchestration should still be represented as an explicit harness identity.
INSERT INTO providers VALUES ('P1','Synthetic Provider','CANDIDATE');
INSERT INTO models VALUES ('A','Worker A','P1','v1','CANDIDATE');
INSERT INTO models VALUES ('B','Worker B','P1','v1','CANDIDATE');
INSERT INTO harnesses VALUES ('H1','Harness','v1','CANDIDATE');
INSERT INTO harnesses VALUES ('H2','Harness','v2','CANDIDATE');
INSERT INTO harnesses VALUES ('DIRECT','Direct API','v1','CANDIDATE');
INSERT INTO task_sets(task_set_id,name,version,purpose,frozen,source_hash) VALUES ('TS-E2E','E2E','v1','E2E',TRUE,'hash-e2e');
INSERT INTO task_sets(task_set_id,name,version,purpose,frozen,source_hash) VALUES ('TS-Q','QUAL','v1','QUALIFICATION',TRUE,'hash-q');
INSERT INTO tasks(task_id,task_set_id,task_type,risk_level,source_hash,acceptance_contract_hash) VALUES ('T-E2E','TS-E2E','integration','HIGH','src-e2e','acc-e2e');
INSERT INTO tasks(task_id,task_set_id,task_type,risk_level,source_hash,acceptance_contract_hash) VALUES ('T-Q1','TS-Q','parser','LOW','src-q1','acc-q1');

-- Base canonical and qualification fixtures.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,qualification_exclusion_reason,source_lock_hash)
VALUES ('RUN-000001','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',TRUE,FALSE,'CANONICAL_E2E_NOT_CONTROLLED_QUALIFICATION_COHORT','lock');
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('RQ1','T-Q1','QUALIFICATION','ACTUAL','PASS',TRUE,TRUE,'lock-q1');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('D1','RQ1',1,'A','H1','LOW','ACTUAL');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('D2','RQ1',2,'B','H1','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention,exit_code)
VALUES ('A1','RQ1','D1',1,'A','H1','FAIL',FALSE,TRUE,0.02,'ACTUAL',FALSE,1);
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention,exit_code)
VALUES ('B1','RQ1','D2',2,'B','H1','PASS',TRUE,TRUE,0.07,'ACTUAL',FALSE,0);
INSERT INTO qualification_cohorts(cohort_id,name,version,task_set_id,evidence_class,cohort_mode,metric_contract_version,frozen)
VALUES ('C1','pilot','v1','TS-Q','ACTUAL','CONTROLLED_PAIR_COMPARISON','v0.1.0',TRUE);
INSERT INTO qualification_observations VALUES ('O-A','C1','T-Q1','RQ1','A1','A','H1','FAIL',FALSE,FALSE,0.02);
INSERT INTO qualification_observations VALUES ('O-B','C1','T-Q1','RQ1','B1','B','H1','ACCEPT',TRUE,FALSE,0.07);

-- P01: SIMULATED cost class is representable for a simulated shadow attempt.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('RSIM','T-Q1','SHADOW','SIMULATED','PASS',TRUE,FALSE,'sim-lock');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DSIM','RSIM',1,'A','H1','LOW','SHADOW');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention,exit_code)
VALUES ('ASIM','RSIM','DSIM',1,'A','H1','PASS',TRUE,TRUE,0.01,'SIMULATED',FALSE,0);

-- P02: subject/attempt mismatch must fail via composite FK.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations
    VALUES ('BAD-MISMATCH','C1','T-Q1','RQ1','B1','A','H2','ACCEPT',TRUE,FALSE,0.07);
    RAISE EXCEPTION 'P02 failed: mismatched subject identity accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- P03: scored harness identity cannot be NULL.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations
    VALUES ('BAD-NULL-H','C1','T-Q1','RQ1','A1','A',NULL,'FAIL',FALSE,FALSE,0.02);
    RAISE EXCEPTION 'P03 failed: NULL harness accepted';
  EXCEPTION WHEN not_null_violation THEN NULL;
  END;
END $$;

-- P04: routing decisions cannot cite nonexistent qualification results.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
    VALUES ('BAD-QREF','RSIM',2,'A','H1','LOW','SHADOW','DOES-NOT-EXIST');
    RAISE EXCEPTION 'P04 failed: nonexistent qualification ref accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- P05: attempt-level human intervention exists and stores evidence.
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM information_schema.columns
  WHERE table_schema='public' AND table_name='run_attempts' AND column_name='human_intervention';
  IF n <> 1 THEN RAISE EXCEPTION 'P05 failed: human_intervention field missing'; END IF;
END $$;

-- P06: impossible rate values fail closed.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_results(
      qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
      accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
      critical_failures,major_failures,qualification_status,routing_eligible
    ) VALUES ('BAD-RATE','C1','A','H1',1,1.5,1.2,2.0,-0.1,0,0,'PILOT',FALSE);
    RAISE EXCEPTION 'P06 failed: impossible rates accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- P07: routing eligibility requires qualification_status=QUALIFIED.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_results(
      qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
      accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
      critical_failures,major_failures,qualification_status,routing_eligible
    ) VALUES ('BAD-ELIG','C1','A','H1',10,0.9,0.8,0.2,0.0,0,0,'PILOT',TRUE);
    RAISE EXCEPTION 'P07 failed: PILOT became routing eligible';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- P08: negative costs and latencies fail closed.
DO $$ BEGIN
  BEGIN
    INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention,latency_ms)
    VALUES ('BAD-NEG','RSIM','DSIM',2,'A','H1','FAIL',FALSE,FALSE,-1,'SIMULATED',FALSE,-1);
    RAISE EXCEPTION 'P08 failed: negative cost/latency accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- P09: canonical E2E still cannot self-promote to qualification.
DO $$ BEGIN
  BEGIN
    INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible)
    VALUES ('BAD-E2E','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',TRUE,TRUE);
    RAISE EXCEPTION 'P09 failed: canonical E2E became qualification eligible';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- P10: simulated policy still cannot become routing eligible.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_policy_results(routing_policy_result_id,policy_name,policy_version,evidence_class,sample_size,routing_eligible)
    VALUES ('BAD-SIM-ROUTE','p','v1','SIMULATED',10,TRUE);
    RAISE EXCEPTION 'P10 failed: simulated policy became routing eligible';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

SELECT 'V0_2_1_POSTGRES_HARDENING_PASS' AS result,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN (
         'providers','models','harnesses','task_sets','tasks','runs','routing_decisions','run_attempts','test_results','review_results','evidence','artifacts','qualification_cohorts','qualification_observations','qualification_results','routing_policy_results'
       )) AS table_count,
       (SELECT SUM(cost_usd) FROM run_attempts WHERE run_id='RQ1') AS workflow_cost,
       (SELECT cost_evidence_class FROM run_attempts WHERE attempt_id='ASIM') AS simulated_cost_class;

ROLLBACK;
