"""Security checks on repository configuration (security/SECURITY_TEST_RESULTS.md).

Static checks that fail the build if a hardening setting is undone: browser security headers, CORS
default, development service bindings, CI token scope, secrets in tracked files, admin key in URLs.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def _csp() -> dict[str, str]:
    config = json.loads((FRONTEND / "vercel.json").read_text(encoding="utf-8"))
    for block in config["headers"]:
        if block["source"] == "/(.*)":
            for header in block["headers"]:
                if header["key"] == "Content-Security-Policy":
                    return {d.split()[0]: d for d in (p.strip() for p in header["value"].split(";")) if d}
    raise AssertionError("no CSP on the site")


def test_csp_blocks_inline_script_and_plugins():
    csp = _csp()
    assert csp["script-src"] == "script-src 'self'"
    assert csp["object-src"] == "object-src 'none'"
    assert "base-uri" in csp and "'self'" in csp["base-uri"]


def test_csp_frame_ancestors_only_the_university():
    frame = _csp()["frame-ancestors"]
    assert "vercel.app" not in frame and "localhost" not in frame and "127.0.0.1" not in frame
    assert "https://sru.edu.in" in frame and "https://*.sru.edu.in" in frame


def test_csp_connect_src_has_no_third_party_ai_or_any_vercel_site():
    connect = _csp()["connect-src"]
    assert "vercel.app" not in connect and "googleapis" not in connect


def test_cors_default_does_not_allow_any_vercel_site():
    from app.config import Settings

    regex = re.compile(Settings.model_fields["CORS_ORIGIN_REGEX"].default)
    assert not regex.fullmatch("https://attacker.vercel.app")
    assert regex.fullmatch("https://university-ai-companion.vercel.app")


def test_development_services_listen_on_localhost_only():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    for name, service in compose["services"].items():
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name} publishes {port} on every interface"


def test_workflows_declare_token_permissions():
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        assert "permissions" in data, f"{wf.name} has no permissions block"


def test_dependabot_covers_python_npm_and_actions():
    data = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert {u["package-ecosystem"] for u in data["updates"]} >= {"pip", "npm", "github-actions"}


def test_example_env_files_hold_placeholders_only():
    for f in (ROOT / "backend" / ".env.example", ROOT / "backend" / ".env.production.example",
              FRONTEND / ".env.example"):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if not m or not any(w in m.group(1) for w in ("KEY", "SECRET", "PASSWORD", "TOKEN")):
                continue
            value = m.group(2)
            if m.group(1).endswith(("_SECONDS", "_COOLDOWN")):
                continue
            assert not value or re.search(r"your|change|replace|example|xxx|<|placeholder|generate|dummy|here",
                                          value, re.I), f"{f.name}: {m.group(1)} looks like a real value"


_SECRET = re.compile(r"AIza[0-9A-Za-z_\-]{35}|\bghp_[A-Za-z0-9]{36}|-----BEGIN (?:RSA |EC )?PRIVATE KEY")


def test_no_secrets_in_tracked_files():
    try:
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git not available")
    hits = []
    for rel in files.splitlines():
        path = ROOT / rel
        if not path.is_file() or path.stat().st_size > 2_000_000 or "test_security" in rel:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _SECRET.search(text):
            hits.append(rel)               # file name only: never print the secret itself
    assert not hits, f"secret-shaped strings in: {hits}"


def test_frontend_never_puts_the_admin_key_in_a_url():
    for f in (FRONTEND / "src").rglob("*.ts*"):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"[?&]admin_key=\$\{", text), f"{f.name} builds a URL with the admin key"


def test_frontend_has_no_raw_html_sinks():
    for f in (FRONTEND / "src").rglob("*.tsx"):
        assert "dangerouslySetInnerHTML" not in f.read_text(encoding="utf-8"), f.name


def test_docker_image_excludes_local_env_files():
    ignore = (ROOT / "backend" / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignore and ".env.*" in ignore
