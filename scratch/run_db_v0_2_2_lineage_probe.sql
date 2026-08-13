
-- Bounded cross-table lineage probe for v0.2.2. Appended before base ROLLBACK.
CREATE TEMP TABLE v022_lineage_probe (
  probe_id TEXT PRIMARY KEY,
  defect_confirmed BOOLEAN NOT NULL,
  detail TEXT NOT NULL
);

-- L01: attempt can reference a routing decision from another run.
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('L01-A','RSH','DB1',1,'B','H1','PASS',TRUE,TRUE,0.01,'ACTUAL',FALSE);
INSERT INTO v022_lineage_probe VALUES (
  'L01_ATTEMPT_CAN_REFERENCE_OTHER_RUN_DECISION',
  EXISTS (SELECT 1 FROM run_attempts ra JOIN routing_decisions rd ON rd.routing_decision_id=ra.routing_decision_id WHERE ra.attempt_id='L01-A' AND ra.run_id<>rd.run_id),
  'run_attempts.routing_decision_id FK does not bind routing decision to same run'
);

-- L02: attempt model+harness can disagree with its routing decision selection.
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('L02-A','RSH','DSH',2,'B','H1','PASS',TRUE,TRUE,0.01,'ACTUAL',FALSE);
INSERT INTO v022_lineage_probe VALUES (
  'L02_ATTEMPT_SUBJECT_CAN_DISAGREE_WITH_DECISION',
  EXISTS (SELECT 1 FROM run_attempts ra JOIN routing_decisions rd ON rd.routing_decision_id=ra.routing_decision_id WHERE ra.attempt_id='L02-A' AND (ra.model_id<>rd.selected_model_id OR ra.harness_id<>rd.selected_harness_id)),
  'attempt execution identity is not bound to selected routing identity'
);

-- L03: review run_id can disagree with review attempt run_id.
INSERT INTO review_results(review_result_id,run_id,attempt_id,reviewer_type,verdict,evidence_class)
VALUES ('L03-R','RSH','BB1','INDEPENDENT','PASS','ACTUAL');
INSERT INTO v022_lineage_probe VALUES (
  'L03_REVIEW_RUN_ATTEMPT_MISMATCH',
  EXISTS (SELECT 1 FROM review_results rr JOIN run_attempts ra ON ra.attempt_id=rr.attempt_id WHERE rr.review_result_id='L03-R' AND rr.run_id<>ra.run_id),
  'review_results has independent run and attempt FKs without same-run constraint'
);

-- L04: evidence run_id can disagree with evidence attempt run_id.
INSERT INTO evidence(evidence_id,run_id,attempt_id,evidence_type,evidence_class,uri,sha256)
VALUES ('L04-E','RSH','BB1','receipt','ACTUAL','urn:test','abc');
INSERT INTO v022_lineage_probe VALUES (
  'L04_EVIDENCE_RUN_ATTEMPT_MISMATCH',
  EXISTS (SELECT 1 FROM evidence e JOIN run_attempts ra ON ra.attempt_id=e.attempt_id WHERE e.evidence_id='L04-E' AND e.run_id<>ra.run_id),
  'evidence can cross-link an attempt from a different run'
);

-- L05: artifact run_id can disagree with artifact attempt run_id.
INSERT INTO artifacts(artifact_id,run_id,attempt_id,artifact_type,uri,sha256,source_system)
VALUES ('L05-X','RSH','BB1','output','urn:artifact','def','TEST');
INSERT INTO v022_lineage_probe VALUES (
  'L05_ARTIFACT_RUN_ATTEMPT_MISMATCH',
  EXISTS (SELECT 1 FROM artifacts a JOIN run_attempts ra ON ra.attempt_id=a.attempt_id WHERE a.artifact_id='L05-X' AND a.run_id<>ra.run_id),
  'artifact can cross-link an attempt from a different run'
);

-- L06: routing previous_decision_id can point to another run's decision.
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,previous_decision_id)
VALUES ('L06-D','RSH',6,'A','H2','LOW','SHADOW','DB1');
INSERT INTO v022_lineage_probe VALUES (
  'L06_PREVIOUS_DECISION_CROSS_RUN',
  EXISTS (SELECT 1 FROM routing_decisions rd JOIN routing_decisions p ON p.routing_decision_id=rd.previous_decision_id WHERE rd.routing_decision_id='L06-D' AND rd.run_id<>p.run_id),
  'previous decision chain is not constrained to the same run'
);

SELECT probe_id, defect_confirmed, detail FROM v022_lineage_probe ORDER BY probe_id;
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM v022_lineage_probe WHERE defect_confirmed IS TRUE;
  IF n <> 6 THEN RAISE EXCEPTION 'Expected 6 confirmed v0.2.2 lineage defects, got %', n; END IF;
END $$;
SELECT 'V0_2_2_LINEAGE_PROBE_CONFIRMED_6_OF_6' AS result;
