import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

schema = json.loads(Path('scratch/run000001.schema.json').read_text(encoding='utf-8'))
validator = Draft202012Validator(schema, format_checker=FormatChecker())

valid = {
    'run_id': 'RUN-000001',
    'run_purpose': 'ACTUAL_CANONICAL_E2E',
    'evidence_class': 'ACTUAL',
    'qualification_eligible': False,
    'qualification_exclusion_reason': 'CANONICAL_E2E_NOT_CONTROLLED_QUALIFICATION_COHORT',
    'task': {'task_id': 'E2E-1', 'task_type': 'integration', 'risk_level': 'HIGH'},
    'source': {'repository': 'owner/repo', 'ref': 'candidate', 'sha': 'abcdef012345', 'source_lock_hash': 'hash'},
    'execution': {
        'surface_identity': 'external-executor-1',
        'started_at': '2026-08-13T08:00:00Z',
        'finished_at': '2026-08-13T08:01:00Z',
        'workflow_status': 'PASS',
        'workflow_accepted': True,
        'human_intervention_required': False
    },
    'routing_decisions': [{'decision_no': 1, 'model_id': 'M1', 'harness_id': 'H1', 'reason': 'frozen route'}],
    'attempts': [{
        'attempt_no': 1, 'model_id': 'M1', 'harness_id': 'H1', 'execution_status': 'PASS',
        'attempt_accepted': True, 'input_tokens': None, 'output_tokens': None,
        'latency_ms': 60000, 'cost_usd': None, 'cost_evidence_class': 'NOT_VERIFIED',
        'human_intervention': False, 'exit_code': 0, 'receipt_hash': 'receipt'
    }],
    'tests': [], 'reviews': [], 'evidence': [], 'artifacts': [], 'limitations': [],
    'final_acceptance_status': 'ACCEPT'
}

def check_valid(name, obj):
    errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    if errors:
        raise AssertionError(f'{name} expected valid, got: {errors[0].message}')
    print(f'PASS {name}')

def check_invalid(name, mutator):
    obj = copy.deepcopy(valid)
    mutator(obj)
    errors = list(validator.iter_errors(obj))
    if not errors:
        raise AssertionError(f'{name} expected invalid')
    print(f'PASS {name}: {errors[0].message}')

check_valid('J01_VALID_CANONICAL_E2E', valid)
check_invalid('J02_QUALIFICATION_ELIGIBLE_TRUE_BLOCKED', lambda x: x.__setitem__('qualification_eligible', True))
check_invalid('J03_WRONG_EVIDENCE_CLASS_BLOCKED', lambda x: x.__setitem__('evidence_class', 'SIMULATED'))
check_invalid('J04_NEGATIVE_COST_BLOCKED', lambda x: x['attempts'][0].__setitem__('cost_usd', -0.01))
check_invalid('J05_NEGATIVE_LATENCY_BLOCKED', lambda x: x['attempts'][0].__setitem__('latency_ms', -1))
check_invalid('J06_MISSING_SOURCE_LOCK_BLOCKED', lambda x: x['source'].pop('source_lock_hash'))
check_invalid('J07_EMPTY_HARNESS_BLOCKED', lambda x: x['attempts'][0].__setitem__('harness_id', ''))
check_invalid('J08_UNKNOWN_TOPLEVEL_FIELD_BLOCKED', lambda x: x.__setitem__('made_up', True))
check_invalid('J09_BAD_TIMESTAMP_BLOCKED', lambda x: x['execution'].__setitem__('started_at', 'not-a-time'))
check_invalid('J10_BAD_FINAL_STATUS_BLOCKED', lambda x: x.__setitem__('final_acceptance_status', 'PASS'))

print('RUN000001_JSON_SCHEMA_10_OF_10_PASS')
