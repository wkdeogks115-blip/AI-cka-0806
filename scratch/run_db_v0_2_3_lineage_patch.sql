
-- RUN DB v0.2.3 lineage-integrity patch applied on top of v0.2.2 before ROLLBACK.

-- Bind routing decision identity to its run and selected model+harness.
ALTER TABLE routing_decisions
  ADD CONSTRAINT uq_routing_decision_run UNIQUE (routing_decision_id, run_id);
ALTER TABLE routing_decisions
  ADD CONSTRAINT uq_routing_decision_subject UNIQUE (routing_decision_id, run_id, selected_model_id, selected_harness_id);
ALTER TABLE routing_decisions
  ADD CONSTRAINT fk_previous_decision_same_run
  FOREIGN KEY (previous_decision_id, run_id)
  REFERENCES routing_decisions(routing_decision_id, run_id);

-- Every scored execution attempt must be backed by the exact routing decision for the same run and subject.
ALTER TABLE run_attempts ALTER COLUMN routing_decision_id SET NOT NULL;
ALTER TABLE run_attempts
  ADD CONSTRAINT uq_attempt_run UNIQUE (attempt_id, run_id);
ALTER TABLE run_attempts
  ADD CONSTRAINT fk_attempt_exact_routing_subject
  FOREIGN KEY (routing_decision_id, run_id, model_id, harness_id)
  REFERENCES routing_decisions(routing_decision_id, run_id, selected_model_id, selected_harness_id);

-- Optional attempt-scoped review: when attempt_id exists it must belong to review run_id.
ALTER TABLE review_results
  ADD CONSTRAINT fk_review_attempt_same_run
  FOREIGN KEY (attempt_id, run_id)
  REFERENCES run_attempts(attempt_id, run_id);

-- Evidence/artifacts may be run-scoped, but attempt-scoped rows must also include and match run_id.
ALTER TABLE evidence
  ADD CONSTRAINT ck_evidence_attempt_requires_run CHECK (attempt_id IS NULL OR run_id IS NOT NULL);
ALTER TABLE evidence
  ADD CONSTRAINT fk_evidence_attempt_same_run
  FOREIGN KEY (attempt_id, run_id)
  REFERENCES run_attempts(attempt_id, run_id);
ALTER TABLE artifacts
  ADD CONSTRAINT ck_artifact_attempt_requires_run CHECK (attempt_id IS NULL OR run_id IS NOT NULL);
ALTER TABLE artifacts
  ADD CONSTRAINT fk_artifact_attempt_same_run
  FOREIGN KEY (attempt_id, run_id)
  REFERENCES run_attempts(attempt_id, run_id);

-- L01 other-run routing decision must be blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
    VALUES ('V23-L01','RSH','DB1',3,'B','H1','PASS',TRUE,TRUE,0.01,'ACTUAL',FALSE);
    RAISE EXCEPTION 'V23 L01 failed';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- L02 selected routing subject mismatch must be blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
    VALUES ('V23-L02','RSH','DSH',4,'B','H1','PASS',TRUE,TRUE,0.01,'ACTUAL',FALSE);
    RAISE EXCEPTION 'V23 L02 failed';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- L03 review run/attempt mismatch must be blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO review_results(review_result_id,run_id,attempt_id,reviewer_type,verdict,evidence_class)
    VALUES ('V23-L03','RSH','BB1','INDEPENDENT','PASS','ACTUAL');
    RAISE EXCEPTION 'V23 L03 failed';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- L04 evidence run/attempt mismatch must be blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO evidence(evidence_id,run_id,attempt_id,evidence_type,evidence_class,uri,sha256)
    VALUES ('V23-L04','RSH','BB1','receipt','ACTUAL','urn:test','abc');
    RAISE EXCEPTION 'V23 L04 failed';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- L05 artifact run/attempt mismatch must be blocked.
DO $$ BEGIN
  BEGIN
    INSERT INTO artifacts(artifact_id,run_id,attempt_id,artifact_type,uri,sha256,source_system)
    VALUES ('V23-L05','RSH','BB1','output','urn:artifact','def','TEST');
    RAISE EXCEPTION 'V23 L05 failed';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- L06 previous decision chain must stay within same run.
DO $$ BEGIN
  BEGIN
    INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,previous_decision_id)
    VALUES ('V23-L06','RSH',6,'A','H2','LOW','SHADOW','DB1');
    RAISE EXCEPTION 'V23 L06 failed';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END $$;

-- L07 valid same-run lineage remains accepted.
INSERT INTO routing_decisions(routing_decision_id,run_id,decision_no,selected_model_id,selected_harness_id,risk_level,mode,previous_decision_id)
VALUES ('V23-D2','RSH',7,'A','H2','LOW','SHADOW','DSH');
INSERT INTO run_attempts(attempt_id,run_id,routing_decision_id,attempt_no,model_id,harness_id,execution_status,attempt_accepted,first_attempt_for_subject,cost_usd,cost_evidence_class,human_intervention)
VALUES ('V23-A2','RSH','V23-D2',7,'A','H2','PASS',TRUE,FALSE,0.01,'ACTUAL',FALSE);
INSERT INTO review_results(review_result_id,run_id,attempt_id,reviewer_type,verdict,evidence_class)
VALUES ('V23-R','RSH','V23-A2','INDEPENDENT','PASS','ACTUAL');
INSERT INTO evidence(evidence_id,run_id,attempt_id,evidence_type,evidence_class,uri,sha256)
VALUES ('V23-E','RSH','V23-A2','receipt','ACTUAL','urn:v23','123');
INSERT INTO artifacts(artifact_id,run_id,attempt_id,artifact_type,uri,sha256,source_system)
VALUES ('V23-X','RSH','V23-A2','output','urn:v23-artifact','456','TEST');

DO $$ DECLARE n INT; BEGIN
  SELECT COUNT(*) INTO n FROM run_attempts ra
  JOIN routing_decisions rd ON rd.routing_decision_id=ra.routing_decision_id
  WHERE ra.attempt_id='V23-A2'
    AND ra.run_id=rd.run_id
    AND ra.model_id=rd.selected_model_id
    AND ra.harness_id=rd.selected_harness_id;
  IF n <> 1 THEN RAISE EXCEPTION 'V23 L07 valid lineage not preserved'; END IF;
END $$;

SELECT 'V0_2_3_LINEAGE_HARDENING_PASS_7_OF_7' AS result;
