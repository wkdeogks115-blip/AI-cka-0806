from __future__ import annotations
from typing import Any, Dict

ARTIFACT_TYPES = ["ANSWER","POLICY","SKILL","TEMPLATE","SCHEMA","EVAL","ADAPTER","CODE","PRODUCT","RESEARCH"]
SIGNAL_MAP = {
    "one_off_answer":"ANSWER",
    "policy_change":"POLICY",
    "repeatable_procedure":"SKILL",
    "reusable_template":"TEMPLATE",
    "formal_schema":"SCHEMA",
    "evaluation_harness":"EVAL",
    "external_system_bridge":"ADAPTER",
    "executable_code":"CODE",
    "end_user_product":"PRODUCT",
    "research_only":"RESEARCH",
}

def artifact_type_gate(req: Dict[str, Any]) -> Dict[str, Any]:
    explicit=req.get("explicit_artifact_type")
    if explicit is not None:
        if explicit not in ARTIFACT_TYPES:
            return {"status":"INVALID_INPUT","artifact_type":None,"errors":["invalid_explicit_artifact_type"]}
        return {"status":"OK","artifact_type":explicit,"source":"EXPLICIT","candidates":[explicit]}
    signals=req.get("signals")
    if not isinstance(signals, dict):
        return {"status":"INVALID_INPUT","artifact_type":None,"errors":["signals_required"]}
    candidates=[]
    for k,t in SIGNAL_MAP.items():
        if signals.get(k) is True and t not in candidates:
            candidates.append(t)
    if len(candidates)==1:
        return {"status":"OK","artifact_type":candidates[0],"source":"STRUCTURED_SIGNALS","candidates":candidates}
    return {"status":"AMBIGUOUS","artifact_type":None,"source":"NO_DECISIVE_SIGNAL" if not candidates else "MULTIPLE_DECISIVE_SIGNALS","candidates":candidates}

def assetization_gate(data: Dict[str, Any]) -> Dict[str, Any]:
    t=data.get("artifact_type")
    if t not in ARTIFACT_TYPES:
        return {"status":"INVALID_INPUT","action":None,"errors":["invalid_artifact_type"]}
    existing=data.get("existing_solution","NONE")
    reuse=data.get("expected_reuse","ONE_OFF")
    impact=data.get("quality_impact","LOW")
    volatility=data.get("volatility","LOW")
    maintenance=data.get("maintenance_cost","LOW")
    evidence=data.get("evidence_strength","UNVERIFIED")
    procedural=bool(data.get("proceduralizable",False))
    productizable=bool(data.get("productizable",False))
    if existing=="SUFFICIENT": return {"status":"OK","action":"REFERENCE","reason":"existing_solution_sufficient"}
    if existing=="PARTIAL" and reuse in {"REPEATED","CROSS_PROJECT"} and maintenance!="HIGH": return {"status":"OK","action":"WRAP","reason":"existing_solution_partial_reusable"}
    if volatility=="HIGH" and maintenance=="HIGH" and evidence in {"UNVERIFIED","SIMULATED"}: return {"status":"OK","action":"DEFER","reason":"volatile_high_maintenance_weak_evidence"}
    if reuse=="ONE_OFF" and impact in {"LOW","MEDIUM"}: return {"status":"OK","action":"ONE_OFF","reason":"low_reuse"}
    if t=="ANSWER": return {"status":"OK","action":"ONE_OFF","reason":"answer_not_asset_by_default"}
    if t=="RESEARCH": return {"status":"OK","action":"REFERENCE" if reuse!="ONE_OFF" else "ONE_OFF","reason":"research_reference_policy"}
    if t=="POLICY": return {"status":"OK","action":"CREATE_POLICY","reason":"typed_reusable_asset"}
    if t=="SKILL": return {"status":"OK","action":"CREATE_SKILL" if procedural else "DEFER","reason":"typed_reusable_asset" if procedural else "skill_requires_proceduralizable_behavior"}
    if t=="TEMPLATE": return {"status":"OK","action":"CREATE_TEMPLATE","reason":"typed_reusable_asset"}
    if t=="SCHEMA": return {"status":"OK","action":"CREATE_SCHEMA","reason":"typed_reusable_asset"}
    if t=="EVAL": return {"status":"OK","action":"CREATE_EVAL","reason":"typed_reusable_asset"}
    if t=="ADAPTER": return {"status":"OK","action":"CREATE_ADAPTER","reason":"typed_reusable_asset"}
    if t=="PRODUCT": return {"status":"OK","action":"CREATE_PRODUCT","reason":"typed_reusable_asset"}
    if t=="CODE": return {"status":"OK","action":"CREATE_PRODUCT" if productizable else "DEFER","reason":"reusable_code_packaged_as_product_asset" if productizable else "no_create_code_action_in_v1_contract_choose_packaging_first"}
    return {"status":"OK","action":"DEFER","reason":"conservative_default"}

def release_check(target: str) -> Dict[str, Any]:
    if target!="LOCAL":
        return {"status":"DENIED_PREVIEW_ONLY","allowed":False,"candidate_only":True,"errors":["standalone_preview_never_performs_external_delivery_or_final_approval"]}
    return {"status":"ALLOWED_PREVIEW","allowed":True,"candidate_only":True,"errors":[]}

def build_preview(req: Dict[str, Any]) -> Dict[str, Any]:
    t=artifact_type_gate(req)
    if t["status"]!="OK":
        return {"preview_status":"NEEDS_CLARIFICATION","artifact_type":t,"active_release":False,"actual_external_agent":"NOT_RUN","final_approval":"UNVERIFIED"}
    artifact_type=t["artifact_type"]
    asset=assetization_gate({"artifact_type":artifact_type, **req.get("assetization",{})})
    constraints=list(req.get("constraints",[]))+["PREVIEW_ONLY","NO_EXTERNAL_WRITE","NO_ACTIVE_PROMOTION","NO_SELF_FINAL_APPROVAL"]
    contract={
        "WHO":req.get("who","USER+FACTORY_B_PREVIEW"),"WHAT":req.get("idea","UNSPECIFIED"),"WHY":req.get("why","UNVERIFIED"),"WHEN":req.get("when","ON_REQUEST"),"WHERE":req.get("where","STANDALONE_PREVIEW"),
        "HOW":f"artifact_type={artifact_type}; assetization={asset.get('action')}","INPUTS":req.get("inputs",[]),"OUTPUTS":req.get("outputs",["PREVIEW_CANDIDATE_PLAN"]),"DEPENDENCIES":["FACTORY_B_MINIMAL_CONTRACT_REFERENCE_v0.2.1"],
        "CONSTRAINTS":constraints,"APPROVAL_BOUNDARY":{"final_approver":"EXTERNAL","factory_can_final_approve":False},"FAILURE_MODES":["AMBIGUOUS_TYPE","UNSUPPORTED_DELIVERY","STALE_SNAPSHOT"],"RECOVERY":["REFRESH_LIVE_CURRENT_IF_AVAILABLE","CLARIFY_STRUCTURED_SIGNALS"],
        "SUCCESS_CRITERIA":req.get("success_criteria",["TYPE_AND_ASSETIZATION_DECIDED"]),"TEST_STATUS":"PREVIEW_NOT_EXECUTION_EVIDENCE","KNOWN_LIMITATIONS":["NO_ACTUAL_CODEX","NO_ACTUAL_DELIVERY","NO_SEMANTIC_PERFORMANCE_CLAIM"],"VERSION":"PREVIEW-0.2.0","PROVENANCE":{"rules":"snapshot_of_minimal_factory_contract_v0.2.1"}
    }
    handoff={
        "TASK_ID":req.get("task_id","PREVIEW-TASK-001"),"GOAL":req.get("idea","UNSPECIFIED"),"CURRENT_CONTEXT":"Self-contained Factory B offline preview request. No prior chat required.","REQUIREMENTS":req.get("requirements",[]),"NON_GOALS":["ACTUAL_EXTERNAL_AGENT_EXECUTION","FINAL_APPROVAL","PRODUCTION_RELEASE"],"CONSTRAINTS":constraints,"RELEVANT_FILES":[{"reference":"CURRENT_SNAPSHOT.json","stable_id":"PREVIEW_LOCAL_SNAPSHOT"}],"ACCEPTANCE_CRITERIA":req.get("success_criteria",["TYPE_AND_ASSETIZATION_DECIDED"]),"REQUIRED_TESTS":req.get("required_tests",["PREVIEW_SELF_CHECK"]),"DO_NOT":["CLAIM_ACTIVE","WRITE_EXTERNAL_SYSTEM","CLAIM_TESTS_NOT_RUN"],"EVIDENCE_REQUIRED":["PREVIEW_OUTPUT_JSON"],"RELEASE_TARGET":"LOCAL"
    }
    return {"preview_status":"READY_PREVIEW","artifact_type":t,"assetization":asset,"artifact_contract":contract,"implementation_handoff":handoff,"release_check":release_check("LOCAL"),"active_release":False,"activation_evidence":False,"actual_external_agent":"NOT_RUN","actual_handoff_independence":"UNVERIFIED","independent_review":"UNVERIFIED","final_approval":"UNVERIFIED"}
