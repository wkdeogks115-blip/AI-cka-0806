
-- Appended before ROLLBACK of v0.2.1. These probes intentionally demonstrate gaps.
CREATE TEMP TABLE v021_probe_results (
  probe_id TEXT PRIMARY KEY,
  defect_confirmed BOOLEAN NOT NULL,
  detail TEXT NOT NULL
);

-- D101: a non-QUALIFICATION ACTUAL run can still be inserted into an ACTUAL qualification cohort.
-- Use A/H2 to avoid colliding with the legitimate C1/T-Q1/A/H1 observation.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('SHADOW-Q-CONTAM','T-Q1','SHADOW','ACTUAL','PASS',TRUE,FALSE,'shadow-q');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('SHADOW-Q-D','SHADOW-Q-CONTAM',1,'A','H2','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('SHADOW-Q-A','SHADOW-Q-CONTAM','SHADOW-Q-D',1,'A','H2','PASS',TRUE,TRUE,0.03,'ACTUAL',FALSE);
INSERT INTO qualification_observations
VALUES ('O-SHADOW-CONTAM','C1','T-Q1','SHADOW-Q-CONTAM','SHADOW-Q-A','A','H2','ACCEPT',TRUE,FALSE,0.03);
INSERT INTO v021_probe_results VALUES (
  'D101_NON_QUALIFICATION_RUN_CAN_ENTER_COHORT',
  EXISTS (SELECT 1 FROM qualification_observations WHERE observation_id='O-SHADOW-CONTAM'),
  'v0.2.1 observation does not enforce run_purpose=QUALIFICATION'
);

-- D102: a SIMULATED QUALIFICATION run can enter an ACTUAL cohort.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('SIM-Q-CONTAM','T-Q1','QUALIFICATION','SIMULATED','PASS',TRUE,TRUE,'sim-q');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('SIM-Q-D','SIM-Q-CONTAM',1,'B','H2','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('SIM-Q-A','SIM-Q-CONTAM','SIM-Q-D',1,'B','H2','PASS',TRUE,TRUE,0.01,'SIMULATED',FALSE);
INSERT INTO qualification_observations
VALUES ('O-SIM-CONTAM','C1','T-Q1','SIM-Q-CONTAM','SIM-Q-A','B','H2','ACCEPT',TRUE,FALSE,0.01);
INSERT INTO v021_probe_results VALUES (
  'D102_SIMULATED_RUN_CAN_ENTER_ACTUAL_COHORT',
  EXISTS (SELECT 1 FROM qualification_observations WHERE observation_id='O-SIM-CONTAM'),
  'v0.2.1 observation does not enforce referenced run evidence_class=ACTUAL'
);

-- D103: a task outside the cohort frozen task_set can enter the cohort.
INSERT INTO task_sets(task_set_id,name,version,purpose,frozen,source_hash)
VALUES ('TS-OTHER','OTHER','v1','QUALIFICATION',TRUE,'other-hash');
INSERT INTO tasks(task_id,task_set_id,task_type,risk_level,source_hash,acceptance_contract_hash)
VALUES ('T-OTHER','TS-OTHER','other','LOW','other-src','other-acc');
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash)
VALUES ('R-OTHER','T-OTHER','QUALIFICATION','ACTUAL','PASS',TRUE,TRUE,'other-lock');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('D-OTHER','R-OTHER',1,'A','H2','LOW','ACTUAL');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('A-OTHER','R-OTHER','D-OTHER',1,'A','H2','PASS',TRUE,TRUE,0.04,'ACTUAL',FALSE);
INSERT INTO qualification_observations
VALUES ('O-OTHER-TASK','C1','T-OTHER','R-OTHER','A-OTHER','A','H2','ACCEPT',TRUE,FALSE,0.04);
INSERT INTO v021_probe_results VALUES (
  'D103_OUT_OF_COHORT_TASK_CAN_ENTER',
  EXISTS (SELECT 1 FROM qualification_observations WHERE observation_id='O-OTHER-TASK'),
  'v0.2.1 observation task_id is not tied to cohort.task_set_id'
);

-- D104: attributed_cost_usd is duplicated and can disagree with the actual referenced attempt cost.
UPDATE qualification_observations SET attributed_cost_usd=999.00 WHERE observation_id='O-B';
INSERT INTO v021_probe_results VALUES (
  'D104_ATTRIBUTED_COST_CAN_DIVERGE_FROM_ATTEMPTS',
  EXISTS (
    SELECT 1 FROM qualification_observations qo
    JOIN run_attempts ra ON ra.attempt_id=qo.attempt_id
    WHERE qo.observation_id='O-B' AND qo.attributed_cost_usd <> ra.cost_usd
  ),
  'v0.2.1 stores duplicated attributed cost without derivation/guard'
);

-- D105: ACTUAL routing decision can cite a non-routing-eligible qualification result.
INSERT INTO qualification_results(
  qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
  accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
  critical_failures,major_failures,qualification_status,routing_eligible
) VALUES ('QR-PILOT','C1','A','H1',1,0.5,0.5,0.5,0.0,0,0,'PILOT',FALSE);
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
VALUES ('D-ACTUAL-PILOT','SHADOW-Q-CONTAM',2,'A','H2','LOW','ACTUAL','QR-PILOT');
INSERT INTO v021_probe_results VALUES (
  'D105_ACTUAL_ROUTE_CAN_REFERENCE_INELIGIBLE_QUALIFICATION',
  EXISTS (SELECT 1 FROM routing_decisions WHERE routing_decision_id='D-ACTUAL-PILOT'),
  'v0.2.1 FK proves existence but not routing_eligible=true and does not bind selected subject to cited qualification subject'
);

-- D106: a QUALIFIED routing-eligible result can be created from an unfrozen cohort.
INSERT INTO qualification_cohorts(cohort_id,name,version,task_set_id,evidence_class,cohort_mode,metric_contract_version,frozen)
VALUES ('C-UNFROZEN','unfrozen','v1','TS-Q','ACTUAL','ISOLATED_SUBJECT','v0.1.0',FALSE);
INSERT INTO qualification_results(
  qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
  accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
  critical_failures,major_failures,qualification_status,routing_eligible
) VALUES ('QR-UNFROZEN','C-UNFROZEN','B','H1',10,0.9,0.8,0.2,0.0,0,0,'QUALIFIED',TRUE);
INSERT INTO v021_probe_results VALUES (
  'D106_UNFROZEN_COHORT_CAN_BECOME_ROUTING_ELIGIBLE',
  EXISTS (SELECT 1 FROM qualification_results WHERE qualification_result_id='QR-UNFROZEN' AND routing_eligible IS TRUE),
  'v0.2.1 cannot enforce cohort.frozen at qualification result promotion'
);

-- D107: runs can claim qualification_eligible outside ACTUAL QUALIFICATION purpose.
UPDATE runs SET qualification_eligible=TRUE WHERE run_id='SHADOW-Q-CONTAM';
INSERT INTO v021_probe_results VALUES (
  'D107_QUALIFICATION_ELIGIBLE_FLAG_NOT_PURPOSE_CLASS_BOUND',
  EXISTS (SELECT 1 FROM runs WHERE run_id='SHADOW-Q-CONTAM' AND qualification_eligible IS TRUE),
  'v0.2.1 only forbids qualification_eligible on ACTUAL_CANONICAL_E2E, not other non-qualification purposes'
);

SELECT probe_id, defect_confirmed, detail FROM v021_probe_results ORDER BY probe_id;
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM v021_probe_results WHERE defect_confirmed IS TRUE;
  IF n <> 7 THEN RAISE EXCEPTION 'Expected 7 confirmed v0.2.1 semantic contamination defects, got %', n; END IF;
END $$;
SELECT 'V0_2_1_SEMANTIC_CONTAMINATION_PROBE_CONFIRMED_7_OF_7' AS result;
