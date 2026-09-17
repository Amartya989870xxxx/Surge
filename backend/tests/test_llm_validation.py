"""LLM outputs are proposals. These tests use a fake model that deliberately invents IDs."""

import pytest

from app.agent.assessor import validate_assessments
from app.llm.client import LLMError, LLMResult
from tests.conftest import TERMINAL_OR_WAITING, _client_for, start, wait_for_status


class FakeLLM:
    model = "fake/fake-model"
    available = True

    def __init__(self):
        self.calls: list[str] = []

    async def complete_json(self, *, purpose, system, prompt, schema, max_tokens=2048, trace_id=None):
        self.calls.append(purpose)
        return LLMResult(self._data(purpose, schema), "fake", "fake-model", 1)

    @staticmethod
    def _data(purpose, schema):
        if purpose == "plan_next_step":
            ids = schema["properties"]["probe_id"]["enum"]
            return {"probe_id": ids[-1], "reason": "Fake planner picked the last valid candidate.", "expected_information": ["x"]}
        if purpose == "assess_evidence":
            keys = schema["properties"]["assessments"]["items"]["properties"]["evidence_id"]["enum"]
            return {
                "assessments": [
                    {"evidence_id": keys[0], "hypothesis": "checkout_regression", "relation": "supports", "strength": "moderate", "rationale": "fake"},
                    {"evidence_id": "invented_key", "hypothesis": "checkout_regression", "relation": "supports", "strength": "strong", "rationale": "hallucinated"},
                    {"evidence_id": keys[0], "hypothesis": "made_up_hypothesis", "relation": "supports", "strength": "strong", "rationale": "hallucinated"},
                ]
            }
        if purpose == "synthesize":
            return {
                "summary": "Fake narrative summary.",
                "key_findings": [{"text": "A finding citing evidence that does not exist", "claim_type": "FACT", "evidence_ids": ["ev_doesnotexist"]}],
            }
        raise AssertionError(f"unexpected purpose {purpose}")


class BrokenLLM(FakeLLM):
    async def complete_json(self, **kwargs):
        raise LLMError("simulated provider outage")


def test_validation_drops_invented_ids_kinds_and_self_contradictions():
    data = {
        "assessments": [
            {"evidence_id": "a", "hypothesis": "checkout_regression", "relation": "supports", "strength": "weak", "rationale": "ok"},
            {"evidence_id": "zzz", "hypothesis": "checkout_regression", "relation": "supports", "strength": "strong", "rationale": "invented id"},
            {"evidence_id": "a", "hypothesis": "not_a_kind", "relation": "supports", "strength": "strong", "rationale": "invented kind"},
            {"evidence_id": "b", "hypothesis": "tracking_failure", "relation": "supports", "strength": "weak", "rationale": "x"},
            {"evidence_id": "b", "hypothesis": "tracking_failure", "relation": "contradicts", "strength": "weak", "rationale": "y"},
        ]
    }
    result = validate_assessments(data, {"a", "b"})
    assert [(r.evidence_key, r.hypothesis_kind) for r in result] == [("a", "checkout_regression")]
    with pytest.raises(LLMError):
        validate_assessments({"nope": []}, {"a"})


async def test_llm_citations_are_checked_against_the_evidence_store(settings):
    fake = FakeLLM()
    async for client in _client_for(settings, llm=fake):
        inv_id = await start(client, reasoning="llm")
        detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
        assert detail["reasoning_mode"] == "llm"
        assert {"plan_next_step", "synthesize"} <= set(fake.calls)
        assert detail["synthesis"]["summary_source"] == "llm"

        claims = (await client.get(f"/api/investigations/{inv_id}/claims")).json()
        llm_claims = [c for c in claims if c["source"] == "llm"]
        assert llm_claims and llm_claims[0]["grounded"] is False
        assert llm_claims[0]["invalid_references"] == ["ev_doesnotexist"]
        assert all(c["grounded"] for c in claims if c["source"] == "backend")

        events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
        assert any(
            e["event_type"] == "PLAN" and e["data"].get("decided_by") == "llm" and e["data"].get("model") == "fake/fake-model"
            for e in events
        )
        evidence = (await client.get(f"/api/investigations/{inv_id}/evidence")).json()
        kinds = {r["hypothesis_kind"] for e in evidence for r in e["relations"]}
        assert "made_up_hypothesis" not in kinds


async def test_llm_outage_falls_back_visibly_and_still_concludes(settings):
    async for client in _client_for(settings, llm=BrokenLLM()):
        inv_id = await start(client, reasoning="llm")
        detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
        assert detail["status"] == "AWAITING_APPROVAL"
        assert detail["strongest_hypothesis"]["kind"] == "checkout_regression"
        events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
        fallbacks = {e["data"].get("component") for e in events if e["event_type"] == "LLM_FALLBACK"}
        assert {"planner", "synthesizer"} <= fallbacks
        assert detail["synthesis"]["summary_source"] == "template"
