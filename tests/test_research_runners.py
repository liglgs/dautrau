"""A/B1/B2 consume identical visible input and preserve failed cases."""

import json
import re

from research.fixtures import load_cases
from research.runners import run_case
from src.ai.transport import ModelResult


class RecordingAdapter:
    def __init__(self):
        self.inputs = []

    def __call__(self, system, user):
        self.inputs.append((system, user))
        data = json.loads(user)
        if "source" in data:
            return ModelResult({"assertions": []}, "fixture", "fixture", "fixture", 2, 1, 3)
        if "issue" in data:
            return ModelResult({"action": "create_verification_task", "question": "Còn dùng?", "missing_fields": ["status"]}, "fixture", "fixture", "fixture", 2, 1, 3)
        return ModelResult({"assertions": [], "issues": [], "actions": []}, "fixture", "fixture", "fixture", 2, 1, 3)


def test_same_visible_input_and_no_hidden_label_for_all_strategies():
    case = load_cases("test")[10]  # response arrives later
    results = {}
    for strategy in ("A", "B1", "B2"):
        adapter = RecordingAdapter()
        results[strategy] = run_case(case, strategy, adapter)
        text = "\n".join(user for _, user in adapter.inputs)
        assert "expected_issues" not in text
        assert "accepted_outcomes" not in text
        assert case.delayed_sources[0]["text"] not in adapter.inputs[0][1]
        assert results[strategy].case_id == case.case_id
        assert [stage["visible_at"] for stage in results[strategy].stages] == [case.initial_visible_at, case.delayed_sources[0]["available_at"]]
    assert all(result.status == "completed" for result in results.values())


def test_model_failure_remains_in_result():
    case = load_cases("test")[0]

    def failing(_system, _user):
        raise RuntimeError("model down")

    result = run_case(case, "B1", failing)
    assert result.status == "incomplete"
    assert result.error == "RuntimeError"
    assert result.case_id == case.case_id
    assert result.stages == []


def test_b1_wrong_enum_is_incomplete_instead_of_silently_normalized():
    case = load_cases("test")[0]

    def invalid(_system, _user):
        return ModelResult({"assertions": [], "issues": [{"type": "frequency_mismatch", "product": "Thuốc B",
                             "field": "frequency", "work_status": "closed"}], "actions": []},
                           "fixture", "fixture", "fixture", 1, 1, 2)

    result = run_case(case, "B1", invalid)
    assert result.status == "incomplete"
    assert result.error == "ValueError"


def test_b2_has_fixed_no_decision_call_while_a_can_decide():
    case = load_cases("test")[15]  # ambiguity
    a_adapter = RecordingAdapter()
    b2_adapter = RecordingAdapter()
    run_case(case, "A", a_adapter)
    run_case(case, "B2", b2_adapter)
    assert all('"issue"' not in user for _, user in b2_adapter.inputs)
    assert len(a_adapter.inputs) >= len(b2_adapter.inputs)


def test_adaptive_action_and_fixed_action_are_observable():
    case = load_cases("test")[15]  # ambiguous history creates an information gap

    class ExtractingAdapter(RecordingAdapter):
        def __call__(self, system, user):
            self.inputs.append((system, user))
            data = json.loads(user)
            if "source" in data:
                source = data["source"]
                name = re.search(r"Thuốc [A-Z]", source["text"]).group()
                return ModelResult({"assertions": [{
                    "name": name, "dose": None, "frequency": None,
                    "assertion_type": "ordered" if source["kind"] == "admission_order" else "uncertain",
                    "quote": source["text"],
                }]}, "fixture", "fixture", "fixture", 2, 1, 3)
            return ModelResult({"action": "create_verification_task", "question": "Tên thuốc?", "missing_fields": ["product"]}, "fixture", "fixture", "fixture", 2, 1, 3)

    a = run_case(case, "A", ExtractingAdapter())
    b2 = run_case(case, "B2", ExtractingAdapter())
    assert a.status == b2.status == "completed"
    assert a.stages[0]["issues"][0]["type"] == "information_gap"
    assert a.stages[0]["actions"][0]["action"] == "create_verification_task"
    assert [action["action"] for action in b2.stages[0]["actions"]] == ["search_case_notes", "create_verification_task"]
