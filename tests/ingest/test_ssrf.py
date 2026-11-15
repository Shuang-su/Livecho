from __future__ import annotations

from livecho_backend.ingest.ssrf import UrlPolicy, validate_redirect_target, validate_url

POLICY = UrlPolicy(allowed_hosts=frozenset({"api.example.test", "play.example.test"}))


def test_accepts_allowlisted_https() -> None:
    decision = validate_url("https://api.example.test/v1/room", POLICY)
    assert decision.accepted
    assert decision.host == "api.example.test"


def test_rejects_ssrf_sensitive_urls() -> None:
    cases = [
        ("file:///etc/passwd", "scheme_forbidden"),
        ("http://api.example.test/x", "scheme_forbidden"),
        ("https://user:pass@api.example.test/x", "userinfo_forbidden"),
        ("https://127.0.0.1/x", "host_blocked"),
        ("https://10.0.0.1/x", "host_blocked"),
        ("https://169.254.169.254/latest", "host_blocked"),
        ("https://localhost/x", "host_blocked"),
        ("https://evil.example/x", "host_not_allowlisted"),
        ("https://api.example.test:8443/x", "port_forbidden"),
        ("https://api.example.test/x#frag", "fragment_forbidden"),
        ("", "url_invalid"),
    ]
    for url, reason in cases:
        decision = validate_url(url, POLICY)
        assert not decision.accepted, url
        assert decision.reason == reason, url


def test_redirect_hop_limit_and_off_allowlist() -> None:
    ok = validate_redirect_target("https://play.example.test/next", POLICY, hop=0)
    assert ok.accepted
    limited = validate_redirect_target("https://play.example.test/next", POLICY, hop=3)
    assert not limited.accepted
    assert limited.reason == "redirect_limit"
    off = validate_redirect_target("https://evil.example/next", POLICY, hop=0)
    assert not off.accepted
