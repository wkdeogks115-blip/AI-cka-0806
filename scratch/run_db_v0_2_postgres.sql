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
  CHECK (NOT (run_purpose = 'ACTUAL_CANONICAL_E2E' AND qualification_eligible = TRUE))
);
CREATE TABLE routing_decisions (
  routing_decision_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  decision_no INTEGER NOT NULL CHECK (decision_no >= 1),
  selected_model_id TEXT NOT NULL REFERENCES models(model_id),
  selected_harness_id TEXT REFERENCES harnesses(harness_id),
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
  harness_id TEXT REFERENCES harnesses(harness_id),
  execution_status TEXT NOT NULL,
  attempt_accepted BOOLEAN,
  first_attempt_for_subject BOOLEAN NOT NULL DEFAULT FALSE,
  input_tokens BIGINT,
  output_tokens BIGINT,
  latency_ms BIGINT,
  cost_usd NUMERIC(18,8),
  cost_evidence_class TEXT CHECK (cost_evidence_class IN ('ACTUAL','REPORTED','INFERRED','NOT_VERIFIED')),
  exit_code INTEGER,
  failure_taxonomy TEXT,
  receipt_hash TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  UNIQUE(run_id, attempt_no)
);
CREATE TABLE test_results (
  test_result_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES run_attempts(attempt_id),
  suite_id TEXT NOT NULL,
  suite_version TEXT,
  passed_count INTEGER,
  failed_count INTEGER,
  skipped_count INTEGER,
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
  critical_count INTEGER NOT NULL DEFAULT 0,
  major_count INTEGER NOT NULL DEFAULT 0,
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
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(run_id),
  attempt_id TEXT REFERENCES run_attempts(attempt_id),
  artifact_type TEXT NOT NULL,
  uri TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  byte_size BIGINT,
  source_system TEXT NOT NULL
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
  task_id TEXT NOT NULL REFERENCES tasks(task_id),
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  attempt_id TEXT NOT NULL REFERENCES run_attempts(attempt_id),
  subject_model_id TEXT NOT NULL REFERENCES models(model_id),
  subject_harness_id TEXT REFERENCES harnesses(harness_id),
  outcome TEXT NOT NULL CHECK (outcome IN ('ACCEPT','FAIL','HOLD','NOT_VERIFIED')),
  first_pass BOOLEAN,
  human_intervention BOOLEAN,
  attributed_cost_usd NUMERIC(18,8),
  UNIQUE(cohort_id, task_id, subject_model_id, subject_harness_id)
);
CREATE TABLE qualification_results (
  qualification_result_id TEXT PRIMARY KEY,
  cohort_id TEXT NOT NULL REFERENCES qualification_cohorts(cohort_id),
  subject_model_id TEXT NOT NULL REFERENCES models(model_id),
  subject_harness_id TEXT REFERENCES harnesses(harness_id),
  task_type_segment TEXT,
  risk_segment TEXT,
  sample_size INTEGER NOT NULL CHECK (sample_size >= 0),
  accepted_rate NUMERIC(8,5),
  first_pass_rate NUMERIC(8,5),
  cost_per_accepted_usd NUMERIC(18,8),
  retry_rate NUMERIC(8,5),
  human_intervention_rate NUMERIC(8,5),
  p50_latency_ms BIGINT,
  p95_latency_ms BIGINT,
  critical_failures INTEGER NOT NULL DEFAULT 0,
  major_failures INTEGER NOT NULL DEFAULT 0,
  qualification_status TEXT NOT NULL CHECK (qualification_status IN ('PILOT','PROVISIONAL','QUALIFIED','REJECTED','HOLD')),
  routing_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE routing_policy_results (
  routing_policy_result_id TEXT PRIMARY KEY,
  policy_name TEXT NOT NULL,
  policy_version TEXT NOT NULL,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('ACTUAL','SIMULATED')),
  sample_size INTEGER NOT NULL CHECK (sample_size >= 0),
  workflow_accept_rate NUMERIC(8,5),
  first_route_accept_rate NUMERIC(8,5),
  escalation_rate NUMERIC(8,5),
  cost_per_workflow_accept_usd NUMERIC(18,8),
  human_intervention_rate NUMERIC(8,5),
  routing_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  CHECK (NOT (evidence_class = 'SIMULATED' AND routing_eligible = TRUE))
);

INSERT INTO providers VALUES ('P1','Synthetic Provider','CANDIDATE');
INSERT INTO models VALUES ('A','Worker A','P1','v1','CANDIDATE');
INSERT INTO models VALUES ('B','Worker B','P1','v1','CANDIDATE');
INSERT INTO models VALUES ('A2','Worker A','P1','v2','CANDIDATE');
INSERT INTO harnesses VALUES ('H1','Harness','v1','CANDIDATE');
INSERT INTO harnesses VALUES ('H2','Harness','v2','CANDIDATE');
INSERT INTO task_sets(task_set_id,name,version,purpose,frozen,source_hash) VALUES ('TS-E2E','E2E','v1','E2E',TRUE,'hash-e2e');
INSERT INTO task_sets(task_set_id,name,version,purpose,frozen,source_hash) VALUES ('TS-Q','QUAL','v1','QUALIFICATION',TRUE,'hash-q');
INSERT INTO tasks(task_id,task_set_id,task_type,risk_level,source_hash,acceptance_contract_hash) VALUES ('T-E2E','TS-E2E','integration','HIGH','src-e2e','acc-e2e');
INSERT INTO tasks(task_id,task_set_id,task_type,risk_level,source_hash,acceptance_contract_hash) VALUES ('T-Q1','TS-Q','parser','LOW','src-q1','acc-q1');

DO $$ BEGIN
  BEGIN
    INSERT INTO routing_policy_results(routing_policy_result_id,policy_name,policy_version,evidence_class,sample_size,routing_eligible)
    VALUES ('RP1','p','v1','SIMULATED',12,TRUE);
    RAISE EXCEPTION 'T01 failed: simulated routing promotion was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

DO $$ BEGIN
  BEGIN
    INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
    VALUES ('BAD-E2E','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',TRUE,TRUE,'lock');
    RAISE EXCEPTION 'T02 failed: canonical E2E became qualification eligible';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,qualification_exclusion_reason,source_lock_hash)
VALUES ('RUN-000001','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',TRUE,FALSE,'CANONICAL_E2E_NOT_CONTROLLED_QUALIFICATION_COHORT','lock');

INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('RQ1','T-Q1','QUALIFICATION','ACTUAL','PASS',TRUE,TRUE,'lock-q1');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('D1','RQ1',1,'A','H1','LOW','ACTUAL');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,previous_decision_id)
VALUES ('D2','RQ1',2,'B','H1','LOW','ACTUAL','D1');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,exit_code)
VALUES ('A1','RQ1','D1',1,'A','H1','FAIL',FALSE,TRUE,0.02,'ACTUAL',1);
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,exit_code)
VALUES ('B1','RQ1','D2',2,'B','H1','PASS',TRUE,TRUE,0.07,'ACTUAL',0);
INSERT INTO qualification_cohorts(cohort_id,name,version,task_set_id,evidence_class,cohort_mode,metric_contract_version,frozen)
VALUES ('C1','pilot','v1','TS-Q','ACTUAL','CONTROLLED_PAIR_COMPARISON','v0.1.0',TRUE);
INSERT INTO qualification_observations VALUES ('O-A','C1','T-Q1','RQ1','A1','A','H1','FAIL',FALSE,FALSE,0.02);
INSERT INTO qualification_observations VALUES ('O-B','C1','T-Q1','RQ1','B1','B','H1','ACCEPT',TRUE,FALSE,0.07);

DO $$ DECLARE c NUMERIC; a TEXT; b TEXT; q BOOLEAN; BEGIN
  SELECT SUM(cost_usd) INTO c FROM run_attempts WHERE run_id='RQ1';
  IF c <> 0.09 THEN RAISE EXCEPTION 'T04 failed cost %, expected 0.09', c; END IF;
  SELECT outcome INTO a FROM qualification_observations WHERE observation_id='O-A';
  SELECT outcome INTO b FROM qualification_observations WHERE observation_id='O-B';
  IF a <> 'FAIL' OR b <> 'ACCEPT' THEN RAISE EXCEPTION 'T03 attribution failed A %, B %', a, b; END IF;
  SELECT qualification_eligible INTO q FROM runs WHERE run_id='RUN-000001';
  IF q THEN RAISE EXCEPTION 'T19 canonical single run qualification block failed'; END IF;
END $$;

DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_cohorts(cohort_id,name,version,task_set_id,evidence_class,cohort_mode,metric_contract_version,frozen)
    VALUES ('C-SIM','sim','v1','TS-Q','SIMULATED','ISOLATED_SUBJECT','v0.1.0',TRUE);
    RAISE EXCEPTION 'T10 failed: simulated qualification cohort accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

DO $$ BEGIN
  BEGIN
    INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,qualification_eligible)
    VALUES ('RUN-000001','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',FALSE);
    RAISE EXCEPTION 'T11 failed: duplicate run id accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
END $$;

DO $$ DECLARE mc INT; hc INT; ac NUMERIC; bc NUMERIC; BEGIN
  SELECT COUNT(*) INTO mc FROM models WHERE canonical_name='Worker A';
  SELECT COUNT(*) INTO hc FROM harnesses WHERE canonical_name='Harness';
  IF mc <> 2 THEN RAISE EXCEPTION 'T08 failed model versions count %', mc; END IF;
  IF hc <> 2 THEN RAISE EXCEPTION 'T09 failed harness versions count %', hc; END IF;
  SELECT attributed_cost_usd INTO ac FROM qualification_observations WHERE observation_id='O-A';
  SELECT attributed_cost_usd INTO bc FROM qualification_observations WHERE observation_id='O-B';
  IF ac <> 0.02 OR bc <> 0.07 THEN RAISE EXCEPTION 'T21 subject cost attribution failed'; END IF;
END $$;

SELECT 'POSTGRES_SCHEMA_AND_CRITICAL_GUARDS_PASS' AS result,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN (
         'providers','models','harnesses','task_sets','tasks','runs','routing_decisions','run_attempts','test_results','review_results','evidence','artifacts','qualification_cohorts','qualification_observations','qualification_results','routing_policy_results'
       )) AS expected_table_count,
       (SELECT COUNT(*) FROM run_attempts WHERE run_id='RQ1') AS escalation_attempts,
       (SELECT SUM(cost_usd) FROM run_attempts WHERE run_id='RQ1') AS workflow_cost;

ROLLBACK;
