"""
Tests for the Firebase service-account parsing (TIME-061).

Uses a FABRICATED service account — never the real credential. The real .env value is validated
out-of-band; these tests only prove the parse helper handles both storage forms.
"""
import json

from app.core.firebase import _load_service_account

# A fake service account whose private_key contains newlines (as the real one does), so we exercise
# the tricky flattening path. This is NOT a real key.
_FAKE_SA = {
    "type": "service_account",
    "project_id": "timesense-test",
    "private_key_id": "abc123",
    "private_key": "-----BEGIN PRIVATE KEY-----\nFAKELINE1\nFAKELINE2\n-----END PRIVATE KEY-----\n",
    "client_email": "sa@timesense-test.iam.gserviceaccount.com",
    "client_id": "000",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def test_parses_compact_json():
    raw = json.dumps(_FAKE_SA)  # compact, correctly-escaped
    sa = _load_service_account(raw)
    assert sa is not None
    assert sa["project_id"] == "timesense-test"
    assert sa["private_key"].startswith("-----BEGIN PRIVATE KEY-----")
    assert "\n" in sa["private_key"]


def test_parses_pretty_printed_flattened_to_literal_backslash_n():
    # Reproduce how the value is stored in .env: pretty-printed JSON with EVERY real newline
    # (structural + private_key) flattened to the two-character literal \n on a single line.
    pretty = json.dumps(_FAKE_SA, indent=2)      # structural real newlines, private_key \n escapes
    flattened = pretty.replace("\n", "\\n")       # single line, all newlines now literal \n
    assert "\n" not in flattened                   # truly single-line

    sa = _load_service_account(flattened)
    assert sa is not None
    assert sa["project_id"] == "timesense-test"
    # private_key recovered with REAL newlines and a well-formed PEM envelope
    assert sa["private_key"].startswith("-----BEGIN PRIVATE KEY-----")
    assert sa["private_key"].rstrip().endswith("-----END PRIVATE KEY-----")
    assert "\n" in sa["private_key"]


def test_empty_and_blank_return_none():
    assert _load_service_account("") is None
    assert _load_service_account("   ") is None
    assert _load_service_account("{}") is None


def test_unparseable_returns_none():
    assert _load_service_account("not json at all") is None
