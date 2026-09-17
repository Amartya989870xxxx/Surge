from app.observability.logging import redact

FAKE_GROQ = "gsk_" + "A1b2" * 12
FAKE_GOOGLE_NEW = "AQ." + "Xy9_" * 10
FAKE_GOOGLE_OLD = "AIza" + "Sy0-" * 9
FAKE_ORG = "org_" + "0a1b" * 7


def test_llm_provider_keys_and_account_ids_are_redacted():
    text = f"groq failed with {FAKE_GROQ} in organization {FAKE_ORG}; gemini used {FAKE_GOOGLE_NEW} and {FAKE_GOOGLE_OLD}"
    cleaned = redact(text)
    for secret in (FAKE_GROQ, FAKE_ORG, FAKE_GOOGLE_NEW, FAKE_GOOGLE_OLD):
        assert secret not in cleaned
    assert cleaned.count("[REDACTED]") == 4


def test_key_value_pairs_are_redacted():
    assert "supersecretvalue123456" not in redact("x-goog-api-key: supersecretvalue123456")
    assert "supersecretvalue123456" not in redact('api_key="supersecretvalue123456"')
