from app.agent.classify import assess_change, assess_message, change_areas


def kinds(assessments):
    return {(a.hypothesis_kind, a.relation.value, a.strength.value) for a in assessments}


def test_checkout_failure_report():
    found = kinds(assess_message("m", "Several customers say the Place order button just spins and they can't finish checkout."))
    assert ("checkout_regression", "supports", "moderate") in found


def test_orders_normal_supports_tracking_and_contradicts_checkout():
    found = kinds(assess_message("m", "Orders in Postgres look normal for today — real purchases are fine."))
    assert ("tracking_failure", "supports", "moderate") in found
    assert ("checkout_regression", "contradicts", "moderate") in found


def test_provider_report():
    found = kinds(assess_message("m", "Stripe status page shows elevated error rates on card payments in EU."))
    assert ("payment_provider_issue", "supports", "moderate") in found


def test_irrelevant_message_produces_nothing():
    assert assess_message("m", "Reminder: team offsite planning doc is due Friday.") == []


def test_code_areas():
    assert change_areas(["src/checkout/PaymentForm.tsx"]) == {"checkout"}
    assert change_areas(["src/analytics/segment.ts"]) == {"analytics"}
    assert change_areas(["docs/api.md", "README.md"]) == {"non_runtime"}


def test_checkout_change_just_before_onset_is_strong_support():
    found = kinds(assess_change("c", "checkout-v2.4.1", ["src/checkout/PaymentForm.tsx"], minutes_before_onset=18))
    assert found == {("checkout_regression", "supports", "strong")}


def test_docs_only_change_contradicts_code_level_causes():
    found = kinds(assess_change("c", "web-v3.1.11", ["docs/api.md", "README.md"], minutes_before_onset=10))
    assert ("checkout_regression", "contradicts", "moderate") in found
    assert ("tracking_failure", "contradicts", "moderate") in found


def test_old_change_is_only_weak_support():
    found = kinds(assess_change("c", "checkout-v2.4.0", ["src/checkout/Cart.tsx"], minutes_before_onset=600))
    assert found == {("checkout_regression", "supports", "weak")}
