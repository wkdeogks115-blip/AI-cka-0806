
-- Appended before ROLLBACK of the v0.2.1 PostgreSQL candidate.

-- Add one ACTUAL SHADOW workflow to validate routing-policy economics queries.
INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible,source_lock_hash,human_intervention_required)
VALUES ('RSHADOW','T-Q1','SHADOW','ACTUAL','PASS',TRUE,FALSE,'shadow-lock',FALSE);
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode)
VALUES ('SD1','RSHADOW',1,'A','H1','LOW','SHADOW');
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,previous_decision_id)
VALUES ('SD2','RSHADOW',2,'B','H1','LOW','SHADOW','SD1');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention,latency_ms)
VALUES ('SA1','RSHADOW','SD1',1,'A','H1','FAIL',FALSE,TRUE,0.02,'ACTUAL',FALSE,100);
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention,latency_ms)
VALUES ('SB1','RSHADOW','SD2',2,'B','H1','PASS',TRUE,TRUE,0.07,'ACTUAL',FALSE,80);

-- Q1 Worker qualification summary semantics.
CREATE TEMP VIEW q1_worker_summary AS
SELECT
  qo.subject_model_id,
  qo.subject_harness_id,
  COUNT(*) AS sample_size,
  COUNT(*) FILTER (WHERE qo.outcome = 'ACCEPT')::numeric / NULLIF(COUNT(*),0) AS accepted_rate,
  COUNT(*) FILTER (WHERE qo.first_pass IS TRUE)::numeric / NULLIF(COUNT(*),0) AS first_pass_rate,
  COUNT(*) FILTER (WHERE qo.human_intervention IS TRUE)::numeric / NULLIF(COUNT(*),0) AS human_intervention_rate,
  CASE
    WHEN COUNT(*) FILTER (WHERE qo.attributed_cost_usd IS NULL) = 0
    THEN SUM(qo.attributed_cost_usd) / NULLIF(COUNT(*) FILTER (WHERE qo.outcome = 'ACCEPT'),0)
    ELSE NULL
  END AS cost_per_accepted_usd
FROM qualification_observations qo
JOIN qualification_cohorts qc ON qc.cohort_id = qo.cohort_id
WHERE qc.evidence_class = 'ACTUAL'
  AND qc.frozen IS TRUE
GROUP BY qo.subject_model_id, qo.subject_harness_id;

DO $$ DECLARE ar NUMERIC; br NUMERIC; bc NUMERIC; BEGIN
  SELECT accepted_rate INTO ar FROM q1_worker_summary WHERE subject_model_id='A' AND subject_harness_id='H1';
  SELECT accepted_rate,cost_per_accepted_usd INTO br,bc FROM q1_worker_summary WHERE subject_model_id='B' AND subject_harness_id='H1';
  IF ar <> 0 THEN RAISE EXCEPTION 'Q1 A accepted_rate expected 0, got %', ar; END IF;
  IF br <> 1 THEN RAISE EXCEPTION 'Q1 B accepted_rate expected 1, got %', br; END IF;
  IF bc <> 0.07 THEN RAISE EXCEPTION 'Q1 B cost/accepted expected .07, got %', bc; END IF;
END $$;

-- Q2 task-type segmented worker summary.
CREATE TEMP VIEW q2_segmented AS
SELECT
  t.task_type,
  qo.subject_model_id,
  qo.subject_harness_id,
  COUNT(*) AS sample_size,
  COUNT(*) FILTER (WHERE qo.outcome='ACCEPT')::numeric / NULLIF(COUNT(*),0) AS accepted_rate,
  COUNT(*) FILTER (WHERE qo.first_pass IS TRUE)::numeric / NULLIF(COUNT(*),0) AS first_pass_rate
FROM qualification_observations qo
JOIN tasks t ON t.task_id = qo.task_id
JOIN qualification_cohorts qc ON qc.cohort_id = qo.cohort_id
WHERE qc.evidence_class='ACTUAL' AND qc.frozen IS TRUE
GROUP BY t.task_type, qo.subject_model_id, qo.subject_harness_id;
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM q2_segmented WHERE task_type='parser';
  IF n <> 2 THEN RAISE EXCEPTION 'Q2 expected 2 parser subjects, got %', n; END IF;
END $$;

-- Q3 workflow routing policy economics.
CREATE TEMP VIEW q3_routing_economics AS
WITH workflow_cost AS (
  SELECT
    r.run_id,
    r.workflow_accepted,
    SUM(ra.cost_usd) AS total_cost,
    COUNT(*) AS attempt_count
  FROM runs r
  JOIN run_attempts ra ON ra.run_id = r.run_id
  WHERE r.evidence_class = 'ACTUAL'
    AND r.run_purpose IN ('SHADOW','PRODUCTION')
  GROUP BY r.run_id, r.workflow_accepted
)
SELECT
  COUNT(*) AS workflows,
  COUNT(*) FILTER (WHERE workflow_accepted IS TRUE)::numeric / NULLIF(COUNT(*),0) AS workflow_accept_rate,
  COUNT(*) FILTER (WHERE attempt_count > 1)::numeric / NULLIF(COUNT(*),0) AS escalation_or_retry_rate,
  CASE
    WHEN COUNT(*) FILTER (WHERE total_cost IS NULL) = 0
    THEN SUM(total_cost) / NULLIF(COUNT(*) FILTER (WHERE workflow_accepted IS TRUE),0)
    ELSE NULL
  END AS cost_per_workflow_accept
FROM workflow_cost;
DO $$ DECLARE w INT; a NUMERIC; e NUMERIC; c NUMERIC; BEGIN
  SELECT workflows,workflow_accept_rate,escalation_or_retry_rate,cost_per_workflow_accept INTO w,a,e,c FROM q3_routing_economics;
  IF w <> 1 OR a <> 1 OR e <> 1 OR c <> 0.09 THEN
    RAISE EXCEPTION 'Q3 mismatch workflows %, accept %, escalation %, cost %',w,a,e,c;
  END IF;
END $$;

-- Q4 escalation attribution audit must expose the failed first attempt and successful second attempt.
CREATE TEMP VIEW q4_escalation_audit AS
SELECT
  r.run_id,
  r.workflow_accepted,
  ra.attempt_no,
  ra.model_id,
  ra.harness_id,
  ra.execution_status,
  ra.attempt_accepted,
  ra.cost_usd
FROM runs r
JOIN run_attempts ra ON ra.run_id = r.run_id
WHERE r.workflow_accepted IS TRUE
  AND EXISTS (
    SELECT 1 FROM run_attempts x
    WHERE x.run_id = r.run_id
      AND x.attempt_no < ra.attempt_no
      AND COALESCE(x.attempt_accepted,FALSE) = FALSE
  )
ORDER BY r.run_id, ra.attempt_no;
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM q4_escalation_audit WHERE run_id='RSHADOW' AND model_id='B' AND attempt_accepted IS TRUE;
  IF n <> 1 THEN RAISE EXCEPTION 'Q4 expected successful escalated B row'; END IF;
END $$;

-- Q5 canonical E2E contamination audit must be empty.
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM runs
  WHERE run_purpose='ACTUAL_CANONICAL_E2E' AND qualification_eligible IS TRUE;
  IF n <> 0 THEN RAISE EXCEPTION 'Q5 canonical E2E qualification contamination rows %', n; END IF;
END $$;

-- Q6 production qualification cohorts must all be ACTUAL by schema.
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM qualification_cohorts WHERE evidence_class <> 'ACTUAL';
  IF n <> 0 THEN RAISE EXCEPTION 'Q6 non-ACTUAL qualification cohorts %', n; END IF;
END $$;

SELECT 'V0_2_1_METRIC_QUERY_REFERENCE_PASS_6_OF_6' AS result;
