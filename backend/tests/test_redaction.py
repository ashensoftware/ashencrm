from backend.core.logger import SCRAPE_LOGS, add_scrape_log
from backend.core.redaction import REDACTED, redact_data, redact_headers, redact_text


def test_redact_headers_hide_credentials():
    redacted = redact_headers(
        {
            "Authorization": "Bearer eyJhbGciOi.super-secret.payload",
            "Cookie": "session=abc123",
            "X-Api-Key": "sk-live-should-not-leak",
            "Content-Type": "application/json",
        }
    )
    blob = str(redacted)
    assert "super-secret" not in blob
    assert "abc123" not in blob
    assert "sk-live-should-not-leak" not in blob
    assert redacted["Authorization"] == REDACTED
    assert redacted["Cookie"] == REDACTED
    assert redacted["X-Api-Key"] == REDACTED
    assert redacted["Content-Type"] == "application/json"


def test_redact_text_and_nested_secrets():
    text = redact_text(
        'Authorization: Bearer raw-token password=hunter2 {"refresh_token":"r1","access_token":"a1"}'
    )
    assert "raw-token" not in text
    assert "hunter2" not in text
    assert "r1" not in text
    assert "a1" not in text
    nested = redact_data(
        {
            "password": "plaintext-password",
            "profile": {"api_key": "key-123", "city": "Medellín"},
        }
    )
    assert nested["password"] == REDACTED
    assert nested["profile"]["api_key"] == REDACTED
    assert nested["profile"]["city"] == "Medellín"


def test_scrape_log_does_not_keep_bearer_or_password():
    SCRAPE_LOGS.clear()
    add_scrape_log("falló Authorization: Bearer session-token-999 password=sekret")
    stored = SCRAPE_LOGS[-1]
    assert "session-token-999" not in stored
    assert "sekret" not in stored
    assert REDACTED in stored
