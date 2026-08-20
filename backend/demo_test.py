"""
CodePulse-AI backend workflow demo.

Tests the full pipeline against a running server:
  1. Single-file analysis (POST /analyze) with WebSocket progress streaming
  2. Cache hit on repeat submission
  3. History endpoints (GET /scans)
  4. Repo analysis via ZIP upload (POST /analyze-repo)
  5. Repo analysis via GitHub URL (needs network)
  6. Repo history endpoints (GET /repo-scans)

Usage:
    python demo_test.py                     # against http://127.0.0.1:8000
    python demo_test.py http://127.0.0.1:8131

Requires: websockets (already in the venv). Run with ../.venv/bin/python.
"""

import asyncio
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile

import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
WS_BASE = BASE.replace("http", "ws")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
DIM = "\033[90m"
END = "\033[0m"


def api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def multipart(path: str, fields: dict) -> dict:
    boundary = "----codepulse" + hashlib.md5(str(fields).encode()).hexdigest()
    parts = []
    for name, value in fields.items():
        if isinstance(value, tuple):  # file upload: (filename, bytes)
            filename, content = value
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            .encode() + content + b"\r\n"
            )
        else:  # plain text field
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n".encode()
            )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  [{PASS if condition else FAIL}] {name}" + (f" {DIM}{detail}{END}" if detail else ""))


def make_test_zip(unique_marker: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("main.py", "from app.helper import helper\n\ndef main():\n    print(helper(21))\n")
        z.writestr("app/__init__.py", "")
        z.writestr("app/helper.py", "def helper(x):\n    return x * 2\n")
        z.writestr("app/app.js", "function greet(name) {\n  if (name) { return 'hi ' + name; }\n  return 'hi';\n}\n")
        z.writestr(f"marker_{unique_marker}.py", "# uniqueness marker to force a cache miss on first run\n")
    return buf.getvalue()


async def stream_job(job_id: str) -> dict:
    """Connect to the job WebSocket and collect frames until a terminal state."""
    frames = []
    async with websockets.connect(f"{WS_BASE}/api/v1/ws/jobs/{job_id}") as ws:
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
            frames.append(msg)
            print(f"      {DIM}-> {msg['status']} {msg['progress']}%{END}")
            if msg["status"] in ("COMPLETED", "CACHE_HIT", "FAILED"):
                return msg, frames
    return frames[-1], frames


async def test_single_file() -> None:
    print("\n1. Single-file analysis (POST /analyze)")
    # unique marker forces a genuine pipeline run (not a stale cache hit)
    code = "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)\n# demo-" + str(int(time.time()))
    resp = api("POST", "/api/v1/analyze", {"title": "demo fib", "language": "python", "code": code})
    check("returns job_id + websocket_url", "job_id" in resp and "websocket_url" in resp, resp.get("status"))

    final, frames = await stream_job(resp["job_id"])
    check("live progress frames streamed", len(frames) >= 2, f"{len(frames)} frames")
    check("final status COMPLETED", final["status"] == "COMPLETED", f"security={final['data'].get('security_score')} maint={final['data'].get('maintainability_score')}")
    check("result has scores/issues/refactored", all(k in final["data"] for k in ("security_score", "issues_list", "refactored_code")))
    scan_id = final["data"]["id"]

    print("\n2. Repeat submission (cache)")
    resp2 = api("POST", "/api/v1/analyze", {"title": "demo fib", "language": "python", "code": code})
    final2, _ = await stream_job(resp2["job_id"])
    check("same code -> CACHE_HIT", final2["status"] == "CACHE_HIT", f"cached={final2['data'].get('cached')}")
    check("cached payload matches", final2["data"]["id"] == scan_id, "same scan id")

    print("\n3. History (GET /scans)")
    scans = api("GET", "/api/v1/scans?limit=5")
    check("scans listed", len(scans) >= 1, f"{len(scans)} records")
    one = api("GET", f"/api/v1/scans/{scan_id}")
    check("GET /scans/{id}", one["id"] == scan_id)


async def test_repo_zip() -> None:
    print("\n4. Repo analysis via ZIP upload (POST /analyze-repo)")
    # same bytes used for both submissions: run 1 = miss, run 2 = cache hit
    zbytes = make_test_zip(str(int(time.time())))
    resp = multipart("/api/v1/analyze-repo", {"file": ("demo_repo.zip", zbytes)})
    check("returns job_id", "job_id" in resp, resp.get("status"))

    final, frames = await stream_job(resp["job_id"])
    check("repo streamed live frames", len(frames) >= 1, f"{len(frames)} frames (stages may pass before connect on tiny repos)")
    check("repo COMPLETED with summary", final["status"] == "COMPLETED" and "summary" in final["data"], f"files={final['data']['summary']['total_files']}")
    check("dependency graph mapped", len(final["data"]["dependency_graph"]) >= 1, str(list(final["data"]["dependency_graph"].keys())))
    check("scores present", "architecture_score" in final["data"] and "maintainability_score" in final["data"])
    repo_id = final["data"]["id"]

    print("\n5. Same ZIP again (cache)")
    resp2 = multipart("/api/v1/analyze-repo", {"file": ("demo_repo.zip", zbytes)})
    final2, _ = await stream_job(resp2["job_id"])
    check("same zip -> CACHE_HIT", final2["status"] == "CACHE_HIT", f"cached={final2['data'].get('cached')}")

    print("\n6. Repo history (GET /repo-scans)")
    scans = api("GET", "/api/v1/repo-scans?limit=5")
    check("repo scans listed", len(scans) >= 1, f"{len(scans)} records")
    one = api("GET", f"/api/v1/repo-scans/{repo_id}")
    check("GET /repo-scans/{id}", one["id"] == repo_id)


async def test_repo_github() -> None:
    print("\n7. Repo analysis via GitHub URL (network required)")
    try:
        resp = multipart("/api/v1/analyze-repo", {"github_url": "https://github.com/RehanIlyas-dev/insta-daemon"})
    except Exception as e:
        check("GitHub flow (skipped - network error)", False, str(e))
        return
    check("returns job_id", "job_id" in resp, resp.get("status"))
    final, _ = await stream_job(resp["job_id"])
    check("repo finished (COMPLETED or CACHE_HIT)", final["status"] in ("COMPLETED", "CACHE_HIT"), f"{final['status']} (URL may already be cached)")
    if final["status"] == "COMPLETED":
        print("      (submit again for a CACHE_HIT)")


async def main() -> None:
    print(f"CodePulse-AI demo against {BASE}\n")
    try:
        api("GET", "/")
        print("  server reachable")
    except Exception as e:
        print(f"  {FAIL} cannot reach {BASE}: {e}")
        print("  start it with: cd backend && ../.venv/bin/uvicorn main:app --reload")
        return

    await test_single_file()
    await test_repo_zip()
    await test_repo_github()
    print("\nAll demo checks done.")


if __name__ == "__main__":
    asyncio.run(main())
