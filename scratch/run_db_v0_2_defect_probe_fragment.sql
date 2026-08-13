
-- Appended before ROLLBACK of the v0.2 PostgreSQL validation script.
CREATE TEMP TABLE defect_probe_results (
  probe_id TEXT PRIMARY KEY,
  defect_confirmed BOOLEAN NOT NULL,
  detail TEXT NOT NULL
);

-- D01: simulated runs need a SIMULATED cost evidence label, but v0.2 rejects it.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('RSIM','T-Q1','SHADOW','SIMULATED','PASS',TRUE,FALSE,'sim-lock');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('DSIM','RSIM',1,'A','H1','LOW','SHADOW');
DO $$ BEGIN
  BEGIN
    INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,exit_code)
    VALUES ('ASIM','RSIM','DSIM',1,'A','H1','PASS',TRUE,TRUE,0.01,'SIMULATED',0);
    INSERT INTO defect_probe_results VALUES ('D01_SIMULATED_COST_CLASS_MISSING',FALSE,'SIMULATED cost class unexpectedly accepted');
  EXCEPTION WHEN check_violation THEN
    INSERT INTO defect_probe_results VALUES ('D01_SIMULATED_COST_CLASS_MISSING',TRUE,'v0.2 cost_evidence_class rejects SIMULATED');
  END;
END $$;

-- D02: qualification observation can claim a subject that does not match the referenced attempt.
-- H2 avoids colliding with the legitimate A/H1 observation while still deliberately mismatching B1 (B/H1).
INSERT INTO qualification_observations
VALUES ('O-MISMATCH','C1','T-Q1','RQ1','B1','A','H2','ACCEPT',TRUE,FALSE,0.07);
INSERT INTO defect_probe_results VALUES (
  'D02_OBSERVATION_SUBJECT_ATTEMPT_MISMATCH',
  EXISTS (SELECT 1 FROM qualification_observations qo JOIN run_attempts ra ON ra.attempt_id=qo.attempt_id
          WHERE qo.observation_id='O-MISMATCH'
            AND (qo.subject_model_id <> ra.model_id OR qo.subject_harness_id IS DISTINCT FROM ra.harness_id)),
  'v0.2 has no DB-level composite FK tying observation subject identity to attempt identity'
);

-- D03: nullable subject_harness_id weakens the intended uniqueness contract in PostgreSQL.
INSERT INTO qualification_observations
VALUES ('O-NULL-H1','C1','T-Q1','RQ1','A1','A',NULL,'FAIL',FALSE,FALSE,0.02);
INSERT INTO qualification_observations
VALUES ('O-NULL-H2','C1','T-Q1','RQ1','A1','A',NULL,'FAIL',FALSE,FALSE,0.02);
INSERT INTO defect_probe_results VALUES (
  'D03_NULL_HARNESS_DUPLICATE_UNIQUENESS',
  (SELECT COUNT(*) FROM qualification_observations
   WHERE cohort_id='C1' AND task_id='T-Q1' AND subject_model_id='A' AND subject_harness_id IS NULL) = 2,
  'PostgreSQL UNIQUE treats NULL harness values as distinct under the v0.2 constraint'
);

-- D04: routing decision qualification_result_id is an unconstrained TEXT reference in v0.2.
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
VALUES ('D-NOQUAL','RSIM',2,'A','H1','LOW','SHADOW','NONEXISTENT-QUALIFICATION-RESULT');
INSERT INTO defect_probe_results VALUES (
  'D04_ROUTING_QUALIFICATION_REF_NO_FK',
  EXISTS (SELECT 1 FROM routing_decisions WHERE routing_decision_id='D-NOQUAL' AND qualification_result_id='NONEXISTENT-QUALIFICATION-RESULT'),
  'v0.2 routing decision can reference a nonexistent qualification result'
);

-- D05: run_attempts lacks attempt-level human intervention attribution.
INSERT INTO defect_probe_results VALUES (
  'D05_ATTEMPT_HUMAN_INTERVENTION_FIELD_MISSING',
  NOT EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_schema='public' AND table_name='run_attempts' AND column_name='human_intervention'),
  'v0.2 only has workflow-level human intervention plus observation-level copied value'
);

-- D06: qualification/routing rate columns currently accept impossible values > 1.
INSERT INTO qualification_results(
  qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
  accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
  critical_failures,major_failures,qualification_status,routing_eligible
) VALUES ('QR-BAD-RATE','C1','A','H1',1,1.5,1.2,2.0,-0.1,0,0,'PILOT',FALSE);
INSERT INTO defect_probe_results VALUES (
  'D06_RATE_RANGE_NOT_CONSTRAINED',
  EXISTS (SELECT 1 FROM qualification_results WHERE qualification_result_id='QR-BAD-RATE'),
  'v0.2 rate columns have no 0..1 CHECK constraints'
);

SELECT probe_id, defect_confirmed, detail
FROM defect_probe_results
ORDER BY probe_id;

DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM defect_probe_results WHERE defect_confirmed IS TRUE;
  IF n <> 6 THEN RAISE EXCEPTION 'Expected 6 confirmed v0.2 defects, got %', n; END IF;
END $$;

SELECT 'V0_2_ADVERSARIAL_PROBE_CONFIRMED_6_OF_6' AS result;
