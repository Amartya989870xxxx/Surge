from app.agent.hypotheses import aggregate, provisional_status


def test_no_evidence_leaves_the_prior_unchanged():
    assert aggregate(0.2, []) == (0.2, [])


def test_repeated_reports_from_one_source_have_diminishing_weight():
    one, _ = aggregate(0.2, [("slack", "supports", "moderate")])
    ten, _ = aggregate(0.2, [("slack", "supports", "moderate")] * 10)
    corroborated, _ = aggregate(0.2, [("sheets", "supports", "strong"), ("github", "supports", "strong")])
    assert ten - one < 0.3
    assert ten < corroborated


def test_contradiction_lowers_confidence():
    supported, _ = aggregate(0.2, [("github", "supports", "strong")])
    contested, _ = aggregate(0.2, [("github", "supports", "strong"), ("sheets", "contradicts", "strong")])
    assert contested < supported


def test_neutral_links_do_not_move_confidence():
    assert aggregate(0.2, [("slack", "neutral", "strong")])[0] == 0.2


def test_single_source_cannot_reach_supported_status():
    confidence, apps = aggregate(0.2, [("slack", "supports", "strong")] * 8)
    assert apps == ["slack"]
    assert provisional_status(confidence, apps, False) != "supported"


def test_two_independent_sources_can_reach_supported_status():
    confidence, apps = aggregate(
        0.2, [("sheets", "supports", "strong"), ("github", "supports", "strong"), ("slack", "supports", "moderate")]
    )
    assert provisional_status(confidence, apps, False) == "supported"


def test_rejection_requires_actual_contradicting_evidence():
    assert provisional_status(0.05, [], has_contradiction=False) == "candidate"
    assert provisional_status(0.05, [], has_contradiction=True) == "rejected"
