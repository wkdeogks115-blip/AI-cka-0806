\set ON_ERROR_STOP on
BEGIN;

-- RUN DB v0.2.2: bounded semantic-hardening candidate.
-- Focus: qualification contamination, attribution, cost derivation, and routing promotion boundaries.

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
  CHECK (NOT qualification_eligible OR (run_purpose='QUALIFICATION' AND evidence_class='ACTUAL'))
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
  UNIQUE(run_id, attempt_no)
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
  task_id TEXT NOT NULL REFERENCES tasks(task_id),
  run_id TEXT NOT NULL REFERENCES runs(run_id),
  attempt_id TEXT NOT NULL REFERENCES run_attempts(attempt_id),
  subject_model_id TEXT NOT NULL REFERENCES models(model_id),
  subject_harness_id TEXT NOT NULL REFERENCES harnesses(harness_id),
  outcome TEXT NOT NULL CHECK (outcome IN ('ACCEPT','FAIL','HOLD','NOT_VERIFIED')),
  first_pass BOOLEAN,
  human_intervention BOOLEAN,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
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
  CHECK (NOT routing_eligible OR qualification_status='QUALIFIED'),
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
  CHECK (NOT (evidence_class='SIMULATED' AND routing_eligible=TRUE))
);

-- Cross-table semantic guard for qualification observations.
CREATE OR REPLACE FUNCTION enforce_qualification_observation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  c_task_set TEXT;
  c_frozen BOOLEAN;
  t_task_set TEXT;
  r_task TEXT;
  r_purpose TEXT;
  r_evidence TEXT;
  r_eligible BOOLEAN;
  r_accepted BOOLEAN;
  a_run TEXT;
  a_model TEXT;
  a_harness TEXT;
  first_accept BOOLEAN;
  any_human BOOLEAN;
BEGIN
  SELECT task_set_id, frozen INTO c_task_set, c_frozen
  FROM qualification_cohorts WHERE cohort_id=NEW.cohort_id;
  IF NOT FOUND OR c_frozen IS NOT TRUE THEN
    RAISE EXCEPTION 'qualification cohort must exist and be frozen';
  END IF;

  SELECT task_set_id INTO t_task_set FROM tasks WHERE task_id=NEW.task_id;
  IF t_task_set IS DISTINCT FROM c_task_set THEN
    RAISE EXCEPTION 'qualification task is outside cohort task_set';
  END IF;

  SELECT task_id, run_purpose, evidence_class, qualification_eligible, workflow_accepted
  INTO r_task, r_purpose, r_evidence, r_eligible, r_accepted
  FROM runs WHERE run_id=NEW.run_id;
  IF NOT FOUND OR r_task IS DISTINCT FROM NEW.task_id OR r_purpose <> 'QUALIFICATION'
     OR r_evidence <> 'ACTUAL' OR r_eligible IS NOT TRUE THEN
    RAISE EXCEPTION 'observation requires ACTUAL qualification-eligible QUALIFICATION run for same task';
  END IF;

  SELECT run_id, model_id, harness_id INTO a_run, a_model, a_harness
  FROM run_attempts WHERE attempt_id=NEW.attempt_id;
  IF NOT FOUND OR a_run IS DISTINCT FROM NEW.run_id
     OR a_model IS DISTINCT FROM NEW.subject_model_id
     OR a_harness IS DISTINCT FROM NEW.subject_harness_id THEN
    RAISE EXCEPTION 'observation subject/attempt identity mismatch';
  END IF;

  IF EXISTS (
    SELECT 1 FROM run_attempts
    WHERE run_id=NEW.run_id
      AND (model_id IS DISTINCT FROM NEW.subject_model_id OR harness_id IS DISTINCT FROM NEW.subject_harness_id)
  ) THEN
    RAISE EXCEPTION 'qualification run must isolate one model+harness subject; cross-subject escalation forbidden';
  END IF;

  IF r_accepted IS TRUE AND NEW.outcome <> 'ACCEPT' THEN
    RAISE EXCEPTION 'accepted qualification workflow must yield ACCEPT observation';
  ELSIF r_accepted IS FALSE AND NEW.outcome='ACCEPT' THEN
    RAISE EXCEPTION 'failed qualification workflow cannot yield ACCEPT observation';
  END IF;

  SELECT COALESCE(attempt_accepted,FALSE) INTO first_accept
  FROM run_attempts WHERE run_id=NEW.run_id ORDER BY attempt_no LIMIT 1;
  NEW.first_pass := COALESCE(first_accept,FALSE);

  SELECT COALESCE(BOOL_OR(COALESCE(human_intervention,FALSE)),FALSE) INTO any_human
  FROM run_attempts WHERE run_id=NEW.run_id;
  NEW.human_intervention := any_human;

  RETURN NEW;
END $$;
CREATE TRIGGER trg_qualification_observation_guard
BEFORE INSERT OR UPDATE ON qualification_observations
FOR EACH ROW EXECUTE FUNCTION enforce_qualification_observation();

-- Promotion eligibility must come from a frozen cohort.
CREATE OR REPLACE FUNCTION enforce_qualification_result_promotion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE c_frozen BOOLEAN;
BEGIN
  IF NEW.routing_eligible IS TRUE THEN
    SELECT frozen INTO c_frozen FROM qualification_cohorts WHERE cohort_id=NEW.cohort_id;
    IF c_frozen IS NOT TRUE THEN
      RAISE EXCEPTION 'routing-eligible qualification result requires frozen cohort';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_qualification_result_promotion
BEFORE INSERT OR UPDATE ON qualification_results
FOR EACH ROW EXECUTE FUNCTION enforce_qualification_result_promotion();

-- Any cited qualification result must match the selected subject; ACTUAL route requires routing eligibility.
CREATE OR REPLACE FUNCTION enforce_routing_qualification_reference() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE q_model TEXT; q_harness TEXT; q_eligible BOOLEAN;
BEGIN
  IF NEW.qualification_result_id IS NOT NULL THEN
    SELECT subject_model_id, subject_harness_id, routing_eligible
    INTO q_model, q_harness, q_eligible
    FROM qualification_results WHERE qualification_result_id=NEW.qualification_result_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'qualification result does not exist';
    END IF;
    IF q_model IS DISTINCT FROM NEW.selected_model_id OR q_harness IS DISTINCT FROM NEW.selected_harness_id THEN
      RAISE EXCEPTION 'routing decision subject does not match qualification result subject';
    END IF;
    IF NEW.mode='ACTUAL' AND q_eligible IS NOT TRUE THEN
      RAISE EXCEPTION 'ACTUAL routing cannot cite routing-ineligible qualification result';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_routing_qualification_reference
BEFORE INSERT OR UPDATE ON routing_decisions
FOR EACH ROW EXECUTE FUNCTION enforce_routing_qualification_reference();

-- Fixtures.
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

-- T01 canonical E2E is valid only as non-qualification evidence.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,qualification_exclusion_reason)
VALUES ('RUN-000001','T-E2E','ACTUAL_CANONICAL_E2E','ACTUAL','PASS',TRUE,FALSE,'CANONICAL_E2E_NOT_CONTROLLED_QUALIFICATION_COHORT');
DO $$ BEGIN
  BEGIN
    UPDATE runs SET qualification_eligible=TRUE WHERE run_id='RUN-000001';
    RAISE EXCEPTION 'T01 failed';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- T02 non-qualification purpose cannot set qualification_eligible.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,qualification_eligible)
VALUES ('RSH','T-Q1','SHADOW','ACTUAL','PASS',FALSE);
DO $$ BEGIN
  BEGIN
    UPDATE runs SET qualification_eligible=TRUE WHERE run_id='RSH';
    RAISE EXCEPTION 'T02 failed';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- T03 simulated qualification cannot become eligible.
DO $$ BEGIN
  BEGIN
    INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,qualification_eligible)
    VALUES ('RSIMQ','T-Q1','QUALIFICATION','SIMULATED','PASS',TRUE);
    RAISE EXCEPTION 'T03 failed';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- Valid frozen actual cohort with isolated subject runs.
INSERT INTO qualification_cohorts(cohort_id,name,version,task_set_id,evidence_class,cohort_mode,metric_contract_version,frozen)
VALUES ('C1','pilot','v1','TS-Q','ACTUAL','CONTROLLED_PAIR_COMPARISON','v0.2.2',TRUE);

INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible)
VALUES ('RQA','T-Q1','QUALIFICATION','ACTUAL','FAIL',FALSE,TRUE);
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DA1','RQA',1,'A','H1','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('AA1','RQA','DA1',1,'A','H1','FAIL',FALSE,TRUE,0.02,'ACTUAL',FALSE);
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('AA2','RQA','DA1',2,'A','H1','FAIL',FALSE,FALSE,0.02,'ACTUAL',TRUE);
INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
VALUES ('OA','C1','T-Q1','RQA','AA2','A','H1','FAIL');

INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible)
VALUES ('RQB','T-Q1','QUALIFICATION','ACTUAL','PASS',TRUE,TRUE);
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DB1','RQB',1,'B','H1','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('BB1','RQB','DB1',1,'B','H1','PASS',TRUE,TRUE,0.07,'ACTUAL',FALSE);
INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
VALUES ('OB','C1','T-Q1','RQB','BB1','B','H1','ACCEPT');

-- T04 derived first_pass/human flags.
DO $$ DECLARE fp BOOLEAN; hi BOOLEAN; BEGIN
  SELECT first_pass,human_intervention INTO fp,hi FROM qualification_observations WHERE observation_id='OA';
  IF fp IS TRUE OR hi IS NOT TRUE THEN RAISE EXCEPTION 'T04 A derived semantics failed'; END IF;
  SELECT first_pass,human_intervention INTO fp,hi FROM qualification_observations WHERE observation_id='OB';
  IF fp IS NOT TRUE OR hi IS TRUE THEN RAISE EXCEPTION 'T04 B derived semantics failed'; END IF;
END $$;

-- T05 non-qualification run cannot enter cohort even with qualification_eligible=false.
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DSH','RSH',1,'A','H2','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('ASH','RSH','DSH',1,'A','H2','PASS',TRUE,TRUE,0.03,'ACTUAL',FALSE);
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('BAD-SHADOW','C1','T-Q1','RSH','ASH','A','H2','ACCEPT');
    RAISE EXCEPTION 'T05 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T05 failed' THEN RAISE; END IF;
  END;
END $$;

-- T06 out-of-cohort task blocked.
INSERT INTO task_sets(task_set_id,name,version,purpose,frozen,source_hash) VALUES ('TS-X','X','v1','QUALIFICATION',TRUE,'x');
INSERT INTO tasks(task_id,task_set_id,task_type,risk_level) VALUES ('T-X','TS-X','x','LOW');
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible)
VALUES ('RX','T-X','QUALIFICATION','ACTUAL','PASS',TRUE,TRUE);
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DX','RX',1,'A','H2','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('AX','RX','DX',1,'A','H2','PASS',TRUE,TRUE,0.04,'ACTUAL',FALSE);
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('BAD-X','C1','T-X','RX','AX','A','H2','ACCEPT');
    RAISE EXCEPTION 'T06 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T06 failed' THEN RAISE; END IF;
  END;
END $$;

-- T07 subject/attempt mismatch blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('BAD-MISMATCH','C1','T-Q1','RQB','BB1','A','H2','ACCEPT');
    RAISE EXCEPTION 'T07 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T07 failed' THEN RAISE; END IF;
  END;
END $$;

-- T08 cross-subject escalation in qualification run blocked.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible)
VALUES ('RQCROSS','T-Q1','QUALIFICATION','ACTUAL','PASS',TRUE,TRUE);
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DC1','RQCROSS',1,'A','H2','LOW','ACTUAL');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DC2','RQCROSS',2,'B','H2','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('AC1','RQCROSS','DC1',1,'A','H2','FAIL',FALSE,TRUE,0.02,'ACTUAL',FALSE);
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('BC1','RQCROSS','DC2',2,'B','H2','PASS',TRUE,TRUE,0.07,'ACTUAL',FALSE);
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('BAD-CROSS','C1','T-Q1','RQCROSS','BC1','B','H2','ACCEPT');
    RAISE EXCEPTION 'T08 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T08 failed' THEN RAISE; END IF;
  END;
END $$;

-- T09 cost is derived from run_attempts, not duplicated in observations.
DO $$ DECLARE n INT; ca NUMERIC; cb NUMERIC; BEGIN
  SELECT COUNT(*) INTO n FROM information_schema.columns
  WHERE table_schema='public' AND table_name='qualification_observations' AND column_name='attributed_cost_usd';
  IF n <> 0 THEN RAISE EXCEPTION 'T09 duplicated cost column still exists'; END IF;
  SELECT SUM(cost_usd) INTO ca FROM run_attempts WHERE run_id='RQA' AND model_id='A' AND harness_id='H1';
  SELECT SUM(cost_usd) INTO cb FROM run_attempts WHERE run_id='RQB' AND model_id='B' AND harness_id='H1';
  IF ca <> 0.04 OR cb <> 0.07 THEN RAISE EXCEPTION 'T09 derived costs wrong A %, B %',ca,cb; END IF;
END $$;

-- T10 ACTUAL route cannot cite an ineligible qualification result.
INSERT INTO qualification_results(
  qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
  accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
  critical_failures,major_failures,qualification_status,routing_eligible
) VALUES ('QR-PILOT','C1','A','H2',1,0.5,0.5,0.5,0,0,0,'PILOT',FALSE);
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
    VALUES ('BAD-INELIG','RSH',2,'A','H2','LOW','ACTUAL','QR-PILOT');
    RAISE EXCEPTION 'T10 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T10 failed' THEN RAISE; END IF;
  END;
END $$;

-- T11 cited qualification subject must match selected route subject even in SHADOW mode.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
    VALUES ('BAD-SUBJECT-QREF','RSH',3,'B','H2','LOW','SHADOW','QR-PILOT');
    RAISE EXCEPTION 'T11 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T11 failed' THEN RAISE; END IF;
  END;
END $$;

-- T12 unfrozen cohort cannot produce routing-eligible result.
INSERT INTO qualification_cohorts(cohort_id,name,version,task_set_id,evidence_class,cohort_mode,metric_contract_version,frozen)
VALUES ('C-U','unfrozen','v1','TS-Q','ACTUAL','ISOLATED_SUBJECT','v0.2.2',FALSE);
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_results(
      qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
      accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
      critical_failures,major_failures,qualification_status,routing_eligible
    ) VALUES ('BAD-U','C-U','A','H1',10,0.9,0.8,0.2,0,0,0,'QUALIFIED',TRUE);
    RAISE EXCEPTION 'T12 failed';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM='T12 failed' THEN RAISE; END IF;
  END;
END $$;

-- T13 invalid rates blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_results(
      qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
      accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
      critical_failures,major_failures,qualification_status,routing_eligible
    ) VALUES ('BAD-RATE','C1','A','H1',1,1.2,-0.1,2,0,0,0,'PILOT',FALSE);
    RAISE EXCEPTION 'T13 failed';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- T14 simulated policy cannot self-promote.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_policy_results(routing_policy_result_id,policy_name,policy_version,evidence_class,sample_size,routing_eligible)
    VALUES ('BAD-SIM','p','v1','SIMULATED',20,TRUE);
    RAISE EXCEPTION 'T14 failed';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
END $$;

-- T15 dynamic qualification metric query derives costs including failed attempts.
CREATE TEMP VIEW qualification_worker_metrics_v022 AS
WITH obs AS (
  SELECT qo.*, t.task_type
  FROM qualification_observations qo
  JOIN qualification_cohorts qc ON qc.cohort_id=qo.cohort_id
  JOIN tasks t ON t.task_id=qo.task_id
  WHERE qc.evidence_class='ACTUAL' AND qc.frozen IS TRUE
), costs AS (
  SELECT o.observation_id,
         CASE WHEN COUNT(*) FILTER (WHERE ra.cost_usd IS NULL) > 0 THEN NULL ELSE SUM(ra.cost_usd) END AS subject_total_cost
  FROM obs o
  JOIN run_attempts ra ON ra.run_id=o.run_id
    AND ra.model_id=o.subject_model_id AND ra.harness_id=o.subject_harness_id
  GROUP BY o.observation_id
)
SELECT o.subject_model_id,o.subject_harness_id,COUNT(*) AS sample_size,
       COUNT(*) FILTER (WHERE o.outcome='ACCEPT')::numeric/NULLIF(COUNT(*),0) AS accepted_rate,
       COUNT(*) FILTER (WHERE o.first_pass IS TRUE)::numeric/NULLIF(COUNT(*),0) AS first_pass_rate,
       CASE WHEN COUNT(*) FILTER (WHERE c.subject_total_cost IS NULL)>0 THEN NULL
            ELSE SUM(c.subject_total_cost)/NULLIF(COUNT(*) FILTER (WHERE o.outcome='ACCEPT'),0) END AS cost_per_accepted_usd
FROM obs o JOIN costs c USING(observation_id)
GROUP BY o.subject_model_id,o.subject_harness_id;
DO $$ DECLARE ar NUMERIC; br NUMERIC; bc NUMERIC; BEGIN
  SELECT accepted_rate INTO ar FROM qualification_worker_metrics_v022 WHERE subject_model_id='A' AND subject_harness_id='H1';
  SELECT accepted_rate,cost_per_accepted_usd INTO br,bc FROM qualification_worker_metrics_v022 WHERE subject_model_id='B' AND subject_harness_id='H1';
  IF ar <> 0 OR br <> 1 OR bc <> 0.07 THEN RAISE EXCEPTION 'T15 metric mismatch A %, B %, Bcost %',ar,br,bc; END IF;
END $$;

SELECT 'V0_2_2_SEMANTIC_HARDENING_PASS_15_OF_15' AS result,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN (
         'providers','models','harnesses','task_sets','tasks','runs','routing_decisions','run_attempts','test_results','review_results','evidence','artifacts','qualification_cohorts','qualification_observations','qualification_results','routing_policy_results'
       )) AS table_count,
       (SELECT SUM(cost_usd) FROM run_attempts WHERE run_id='RQA') AS failed_subject_cost,
       (SELECT SUM(cost_usd) FROM run_attempts WHERE run_id='RQB') AS accepted_subject_cost;

ROLLBACK;
