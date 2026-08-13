
-- Appended before the base v0.2.2 ROLLBACK. Each forbidden case must fail closed.
CREATE TEMP TABLE v022_negative_controls (
  probe_id TEXT PRIMARY KEY,
  blocked BOOLEAN NOT NULL,
  detail TEXT NOT NULL
);

-- N01 non-QUALIFICATION run cannot contribute a qualification observation.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('N01-BAD','C1','T-Q1','RSH','ASH','A','H2','ACCEPT');
    RAISE EXCEPTION 'NEGFAIL N01';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N01' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N01_NON_QUALIFICATION_RUN_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N02 SIMULATED QUALIFICATION cannot set qualification_eligible=true.
DO $$ BEGIN
  BEGIN
    INSERT INTO runs(run_id,task_id,run_purpose,evidence_class,workflow_status,workflow_accepted,qualification_eligible)
    VALUES ('N02-SIM-Q','T-Q1','QUALIFICATION','SIMULATED','PASS',TRUE,TRUE);
    RAISE EXCEPTION 'NEGFAIL N02';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N02' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N02_SIMULATED_QUALIFICATION_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N03 task outside cohort task set cannot enter cohort.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('N03-BAD','C1','T-X','RX','AX','A','H2','ACCEPT');
    RAISE EXCEPTION 'NEGFAIL N03';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N03' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N03_OUT_OF_COHORT_TASK_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N04 duplicated attributed-cost field must not exist.
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM information_schema.columns
  WHERE table_schema='public' AND table_name='qualification_observations' AND column_name='attributed_cost_usd';
  IF n <> 0 THEN RAISE EXCEPTION 'NEGFAIL N04'; END IF;
  INSERT INTO v022_negative_controls VALUES ('N04_DUPLICATED_COST_FIELD_REMOVED',TRUE,'qualification_observations.attributed_cost_usd absent');
END $$;

-- N05 ACTUAL route cannot cite routing-ineligible qualification.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
    VALUES ('N05-BAD','RSH',4,'A','H2','LOW','ACTUAL','QR-PILOT');
    RAISE EXCEPTION 'NEGFAIL N05';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N05' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N05_INELIGIBLE_QUALIFICATION_ROUTE_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N06 unfrozen cohort cannot yield routing-eligible result.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_results(
      qualification_result_id,cohort_id,subject_model_id,subject_harness_id,sample_size,
      accepted_rate,first_pass_rate,retry_rate,human_intervention_rate,
      critical_failures,major_failures,qualification_status,routing_eligible
    ) VALUES ('N06-BAD','C-U','B','H1',20,0.9,0.8,0.2,0,0,0,'QUALIFIED',TRUE);
    RAISE EXCEPTION 'NEGFAIL N06';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N06' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N06_UNFROZEN_PROMOTION_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N07 any non-QUALIFICATION purpose cannot flip qualification_eligible=true.
DO $$ BEGIN
  BEGIN
    UPDATE runs SET qualification_eligible=TRUE WHERE run_id='RSH';
    RAISE EXCEPTION 'NEGFAIL N07';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N07' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N07_PURPOSE_CLASS_ELIGIBILITY_BOUND',TRUE,SQLERRM);
  END;
END $$;

-- N08 selected route subject must match cited qualification subject.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,qualification_result_id)
    VALUES ('N08-BAD','RSH',5,'B','H2','LOW','SHADOW','QR-PILOT');
    RAISE EXCEPTION 'NEGFAIL N08';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N08' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N08_ROUTE_SUBJECT_BINDING_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N09 qualification observation cannot use a mismatched subject attempt.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('N09-BAD','C1','T-Q1','RQB','BB1','A','H2','ACCEPT');
    RAISE EXCEPTION 'NEGFAIL N09';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N09' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N09_ATTEMPT_SUBJECT_MISMATCH_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N10 qualification run cannot contain cross-subject escalation and still produce observation.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('N10-BAD','C1','T-Q1','RQCROSS','BC1','B','H2','ACCEPT');
    RAISE EXCEPTION 'NEGFAIL N10';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N10' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N10_CROSS_SUBJECT_ESCALATION_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N11 accepted workflow cannot be recorded as FAIL observation.
DO $$ BEGIN
  BEGIN
    INSERT INTO qualification_observations(observation_id,cohort_id,task_id,run_id,attempt_id,subject_model_id,subject_harness_id,outcome)
    VALUES ('N11-BAD','C1','T-Q1','RQB','BB1','B','H1','FAIL');
    RAISE EXCEPTION 'NEGFAIL N11';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N11' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N11_WORKFLOW_OUTCOME_COHERENCE_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

-- N12 SIMULATED routing-policy result cannot self-promote.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_policy_results(routing_policy_result_id,policy_name,policy_version,evidence_class,sample_size,routing_eligible)
    VALUES ('N12-BAD','shadow','v1','SIMULATED',100,TRUE);
    RAISE EXCEPTION 'NEGFAIL N12';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM='NEGFAIL N12' THEN RAISE; END IF;
    INSERT INTO v022_negative_controls VALUES ('N12_SIMULATED_ROUTING_PROMOTION_BLOCKED',TRUE,SQLERRM);
  END;
END $$;

SELECT probe_id, blocked, detail FROM v022_negative_controls ORDER BY probe_id;
DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM v022_negative_controls WHERE blocked IS TRUE;
  IF n <> 12 THEN RAISE EXCEPTION 'Expected 12/12 v0.2.2 negative controls, got %', n; END IF;
END $$;
SELECT 'V0_2_2_NEGATIVE_CONTROLS_PASS_12_OF_12' AS result;
