"""Phase 0 spike: can a self-built client use the Lovable MCP server on our plan?

Throwaway code. Standard library only. Tokens go to data/sessions/ (gitignored) and are
never printed.

    python -m backend.scripts.spike_lovable_mcp auth      # DCR + browser consent (human clicks Allow)
    python -m backend.scripts.spike_lovable_mcp probe     # free calls: tools/list, get_me, list_projects, refresh
    python -m backend.scripts.spike_lovable_mcp call get_project '{"project_id": "..."}'
    python -m backend.scripts.spike_lovable_mcp build --prompt-file p.md --i-accept-credit-cost
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN_FILE = ROOT / "data" / "sessions" / "lovable_spike_tokens.json"
TOOLS_FILE = ROOT / "docs" / "module-2-lovable" / "mcp-tools.json"
AUTH_URL_FILE = ROOT / "data" / "sessions" / "lovable_spike_authorize_url.txt"

MCP_URL = "https://mcp.lovable.dev"
AS_BASE = "https://lovable.dev/oauth"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"
SCOPES = "offline projects:read projects:write workspaces:read"
UA = "ashencrm-spike/0.1"


# --------------------------------------------------------------------------- http
def _http(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None,
          timeout: int = 60) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def _post_form(url: str, form: dict) -> tuple[int, dict]:
    status, _, body = _http("POST", url, data=urllib.parse.urlencode(form).encode(),
                            headers={"Content-Type": "application/x-www-form-urlencoded",
                                     "Accept": "application/json"})
    try:
        return status, json.loads(body or b"{}")
    except json.JSONDecodeError:
        return status, {"raw": body.decode(errors="replace")[:500]}


# --------------------------------------------------------------------------- tokens
def _save(tokens: dict) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _load() -> dict:
    if not TOKEN_FILE.exists():
        sys.exit("No tokens. Run `auth` first.")
    return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))


def _describe_token(tok: dict) -> dict:
    return {
        "token_type": tok.get("token_type"),
        "scope_granted": tok.get("scope"),
        "expires_in": tok.get("expires_in"),
        "has_refresh_token": bool(tok.get("refresh_token")),
    }


def _refresh(state: dict) -> dict:
    status, tok = _post_form(f"{AS_BASE}/token", {
        "grant_type": "refresh_token",
        "refresh_token": state["refresh_token"],
        "client_id": state["client_id"],
        "resource": MCP_URL,
    })
    if status != 200 or "access_token" not in tok:
        sys.exit(f"Refresh failed: HTTP {status} {tok.get('error')} {tok.get('error_description')}")
    state.update(access_token=tok["access_token"],
                 refresh_token=tok.get("refresh_token", state["refresh_token"]),
                 expires_at=int(time.time()) + int(tok.get("expires_in") or 3600),
                 scope=tok.get("scope", state.get("scope")))
    _save(state)
    return _describe_token(tok)


def _valid_access(state: dict) -> str:
    if int(state.get("expires_at", 0)) - 60 < time.time():
        print("access token expired -> refreshing:", _refresh(state))
    return state["access_token"]


# --------------------------------------------------------------------------- auth
def cmd_auth(_args) -> None:
    # 1. Dynamic client registration (public client, PKCE, no secret).
    reg = {
        "client_name": "AshenCRM (spike)",
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": SCOPES,
    }
    status, _, body = _http("POST", f"{AS_BASE}/register", data=json.dumps(reg).encode(),
                            headers={"Content-Type": "application/json", "Accept": "application/json"})
    if status not in (200, 201):
        sys.exit(f"DCR refused: HTTP {status} {body[:500]!r}")
    client = json.loads(body)
    client_id = client["client_id"]
    print(f"DCR ok. client_id={client_id[:8]}… scope_registered={client.get('scope')}")

    # 2. PKCE + authorize URL.
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    url = f"{AS_BASE}/authorize?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "scope": SCOPES, "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256", "resource": MCP_URL,
    })
    AUTH_URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_URL_FILE.write_text(url, encoding="utf-8")

    # 3. Local callback server.
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if not self.path.startswith("/callback"):
                self.send_response(404); self.end_headers(); return
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            ok = "code" in result and result.get("state") == state
            self.wfile.write(("<h2>AshenCRM spike: " + ("autorizado, puedes cerrar esta pestaña" if ok
                              else "error: " + result.get("error", "desconocido")) + "</h2>").encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Authorize URL written to {AUTH_URL_FILE}")
    print("Waiting for consent (10 min)…", flush=True)
    deadline = time.time() + 600
    while not result and time.time() < deadline:
        time.sleep(0.5)
    server.shutdown()

    if not result:
        sys.exit("Timed out waiting for consent.")
    if result.get("state") != state:
        sys.exit("State mismatch, aborting.")
    if "error" in result:
        sys.exit(f"Consent returned error: {result.get('error')} {result.get('error_description')}")

    # 4. Code exchange.
    status, tok = _post_form(f"{AS_BASE}/token", {
        "grant_type": "authorization_code", "code": result["code"], "redirect_uri": REDIRECT_URI,
        "client_id": client_id, "code_verifier": verifier, "resource": MCP_URL,
    })
    if status != 200 or "access_token" not in tok:
        sys.exit(f"Token exchange failed: HTTP {status} {tok.get('error')} {tok.get('error_description')}")
    _save({
        "client_id": client_id,
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token"),
        "expires_at": int(time.time()) + int(tok.get("expires_in") or 3600),
        "scope": tok.get("scope"),
    })
    print("Token exchange ok:", json.dumps(_describe_token(tok)))


# --------------------------------------------------------------------------- MCP
class Mcp:
    def __init__(self, token: str):
        self.token = token
        self.session: str | None = None
        self._id = 0

    def _rpc(self, method: str, params: dict | None = None, *, notify: bool = False, timeout: int = 120):
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._id += 1
            msg["id"] = self._id
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   "Authorization": f"Bearer {self.token}", "Mcp-Protocol-Version": "2025-06-18"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        status, resp_headers, body = _http("POST", MCP_URL, data=json.dumps(msg).encode(),
                                           headers=headers, timeout=timeout)
        sid = {k.lower(): v for k, v in resp_headers.items()}.get("mcp-session-id")
        if sid:
            self.session = sid
        if notify:
            return {"http": status}
        text = body.decode(errors="replace")
        ctype = {k.lower(): v for k, v in resp_headers.items()}.get("content-type", "")
        if "text/event-stream" in ctype:
            for line in text.splitlines():
                if line.startswith("data:"):
                    try:
                        obj = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if obj.get("id") == msg["id"]:
                        return {"http": status, **obj}
            return {"http": status, "error": {"message": "no matching SSE response", "raw": text[:500]}}
        try:
            return {"http": status, **json.loads(text)}
        except json.JSONDecodeError:
            return {"http": status, "error": {"message": "non-JSON", "raw": text[:500]}}

    def init(self) -> dict:
        r = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "ashencrm-spike", "version": "0.1"}})
        self._rpc("notifications/initialized", notify=True)
        return r

    def tool(self, name: str, args: dict | None = None, timeout: int = 120) -> dict:
        return self._rpc("tools/call", {"name": name, "arguments": args or {}}, timeout=timeout)


def _summ(r: dict, limit: int = 1500) -> str:
    if "error" in r:
        return f"HTTP {r.get('http')} ERROR {json.dumps(r['error'])[:limit]}"
    res = r.get("result", {})
    parts = []
    for c in res.get("content", []) or []:
        if c.get("type") == "text":
            parts.append(c["text"])
        else:
            parts.append(f"<{c.get('type')}>")
    flag = " isError" if res.get("isError") else ""
    return f"HTTP {r.get('http')}{flag} " + ("\n".join(parts) or json.dumps(res))[:limit]


def cmd_probe(_args) -> None:
    st = _load()
    print("granted scope:", st.get("scope"))
    mcp = Mcp(_valid_access(st))
    init = mcp.init()
    print("initialize:", _summ(init, 400) if "error" in init else
          json.dumps(init.get("result", {}).get("serverInfo")))
    tools = mcp._rpc("tools/list")
    if "error" in tools:
        sys.exit("tools/list failed: " + _summ(tools))
    tl = tools["result"]["tools"]
    TOOLS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOOLS_FILE.write_text(json.dumps(tl, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"tools/list: {len(tl)} tools -> {TOOLS_FILE.relative_to(ROOT)}")
    print("  ", ", ".join(t["name"] for t in tl))
    for name in ("get_me", "list_workspaces", "list_projects"):
        print(f"\n== {name}\n{_summ(mcp.tool(name), 1200)}")
    print("\n== refresh test:", _refresh(st))


def cmd_call(args) -> None:
    st = _load()
    mcp = Mcp(_valid_access(st))
    mcp.init()
    print(_summ(mcp.tool(args.name, json.loads(args.arguments or "{}"), timeout=600), 6000))


def cmd_build(args) -> None:
    if not args.i_accept_credit_cost:
        sys.exit("create_project spends Lovable credits. Re-run with --i-accept-credit-cost.")
    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    st = _load()
    mcp = Mcp(_valid_access(st))
    mcp.init()
    t0 = time.time()
    extra = json.loads(args.extra or "{}")
    r = mcp.tool("create_project", {"initial_message": prompt, **extra}, timeout=900)
    print(f"create_project ({time.time() - t0:.0f}s):\n{_summ(r, 6000)}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(fn=cmd_auth)
    sub.add_parser("probe").set_defaults(fn=cmd_probe)
    c = sub.add_parser("call"); c.add_argument("name"); c.add_argument("arguments", nargs="?")
    c.set_defaults(fn=cmd_call)
    b = sub.add_parser("build"); b.add_argument("--prompt-file", required=True)
    b.add_argument("--extra", help="extra create_project args as JSON")
    b.add_argument("--i-accept-credit-cost", action="store_true"); b.set_defaults(fn=cmd_build)
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args.fn(args)


if __name__ == "__main__":
    main()
