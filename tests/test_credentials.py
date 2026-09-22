import httpx
import pytest

from jev_context.doctor import check
from jev_context.provider import Client, ProviderError, credential


def test_env_credentials_and_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    assert credential() == "test-key"
    monkeypatch.setenv("TYPESAFE_API_KEY", "contains space")
    with pytest.raises(ProviderError):
        credential()
    monkeypatch.delenv("TYPESAFE_API_KEY")
    monkeypatch.setenv("TYPESAFE_API_KEY_FILE", str(tmp_path / "missing"))
    assert not check()["api_key_configured"]
    assert not check(True)["ok"]


def test_private_file_and_symlink(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    p = tmp_path / "key"
    p.write_text("test-key")
    p.chmod(0o600)
    monkeypatch.setenv("TYPESAFE_API_KEY_FILE", str(p))
    assert credential() == "test-key"
    p.chmod(0o644)
    with pytest.raises(ProviderError):
        credential()
    p.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(p)
    monkeypatch.setenv("TYPESAFE_API_KEY_FILE", str(link))
    with pytest.raises(ProviderError):
        credential()


def test_closed_and_large_response():
    body = {
        "model": "jev-1.13.0",
        "state": "x",
        "questions": {"q": {"type": "noul", "instructions": "Is x present?"}},
    }
    with Client(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, content=b"x" * (4 * 1024 * 1024 + 1))
        ),
    ) as c:
        with pytest.raises(ProviderError):
            c.call(body)
    with pytest.raises(ProviderError):
        c.call(body)
