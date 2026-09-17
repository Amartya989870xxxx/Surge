import json

from app.agent.hypotheses import CATALOG
from app.db.models import EvaluationSuite
from app.enums import ReasoningMode
from app.scenarios import ScenarioLibrary

REQUIRED_CATEGORIES = {"diagnosis", "ambiguity", "availability", "action_reliability", "safety"}


def test_scenario_suite_covers_required_categories(settings):
    library = ScenarioLibrary(settings.scenarios_dir, settings.worlds_dir)
    scenarios = library.list()
    assert len(scenarios) >= 12
    assert REQUIRED_CATEGORIES <= {s.category for s in scenarios}


def test_ground_truth_never_reaches_provider_data(settings):
    library = ScenarioLibrary(settings.scenarios_dir, settings.worlds_dir)
    for scenario in library.list():
        world = library.build_world(scenario)
        visible = json.dumps([world.sheets, world.github, world.slack], default=str).lower()
        for kind in CATALOG:
            assert kind not in visible, (scenario.scenario_id, kind)
        assert "ground_truth" not in scenario.public_view()


async def test_full_suite_runs_and_scores_from_real_runs(services):
    suite_id = services.evaluations.create_suite(ReasoningMode.HEURISTIC)
    report = await services.evaluations.run_suite(suite_id)

    failing = [(s["scenario_id"], s["failure_reasons"]) for s in report["scenarios"] if not s["passed"]]
    assert not failing, failing
    headline = report["headline"]
    assert headline["duplicate_action_rate"]["duplicates"] == 0
    assert headline["duplicate_action_rate"]["mutation_attempts"] > 0
    assert headline["approval_gate_compliance"]["rate"] == 1.0
    assert headline["unsupported_claim_rate"] == 0.0
    assert headline["tool_success_rate"]["injected_failures"] > 0
    assert headline["recovery_success"]["total"] >= 4

    with services.db.session() as db:
        suite = db.get(EvaluationSuite, suite_id)
        assert suite.status == "completed"
        assert suite.report_text.startswith("SURGE RELIABILITY REPORT")
    assert (services.settings.reports_dir / f"{suite_id}.json").exists()


async def test_evaluation_api_exposes_reports(client):
    response = await client.post("/api/evaluations/run", json={"scenario_ids": ["checkout_regression_01", "false_alarm_01"]})
    assert response.status_code == 202
    suite_id = response.json()["id"]
    import asyncio

    for _ in range(400):
        suite = (await client.get(f"/api/evaluations/{suite_id}")).json()
        if suite["status"] != "running":
            break
        await asyncio.sleep(0.05)
    assert suite["status"] == "completed", suite
    assert len(suite["runs"]) == 2 and all(r["passed"] for r in suite["runs"])
    latest = (await client.get("/api/evaluations/latest")).json()
    assert latest["id"] == suite_id
    scenarios = (await client.get("/api/evaluations/scenarios")).json()
    assert scenarios and "ground_truth" not in scenarios[0]
    listed = (await client.get("/api/investigations")).json()
    assert listed["total"] == 0, "evaluation runs must not pollute the run history by default"
