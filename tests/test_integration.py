"""End-to-end integration test: boots backend + Next.js frontend, walks the quiz.

Used by the pre-commit hook to verify the app actually runs before a commit
lands. Spins up:

1. A FastAPI backend (uvicorn, in-process subprocess) on a free port.
2. The Next.js frontend in prod mode (`next build` + `next start`) with
   `NEXT_PUBLIC_API_URL` pointed at the backend.

Then drives the full 15-question flow with Playwright and asserts a result
card renders. Prod mode is used (rather than `next dev`) because hydration is
faster and more deterministic — it matches what's deployed and avoids the
dev-mode HMR websocket that prevents `networkidle` from settling.
"""

from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_DIR = REPO_ROOT / "api"

SERVER_READY_TIMEOUT_S = 90.0
SERVER_SHUTDOWN_TIMEOUT_S = 10.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, proc: subprocess.Popen, timeout: float, label: str) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read().decode("utf-8", errors="replace") if proc.stdout else ""
            raise RuntimeError(
                f"{label} exited early with code {proc.returncode}.\n"
                f"--- output ---\n{output}"
            )
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return
        except requests.RequestException as e:
            last_err = e
        time.sleep(0.5)
    raise RuntimeError(
        f"{label} didn't become ready at {url} within {timeout}s "
        f"(last error: {last_err})"
    )


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=SERVER_SHUTDOWN_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=SERVER_SHUTDOWN_TIMEOUT_S)
        except ProcessLookupError:
            pass


@pytest.fixture(scope="module")
def backend_server() -> str:
    """Boot the FastAPI backend on a free port; yield the base URL."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(f"{base_url}/healthz", proc, SERVER_READY_TIMEOUT_S, "Backend (uvicorn)")
        yield base_url
    finally:
        _terminate(proc)


@pytest.fixture(scope="module")
def frontend_server(backend_server: str) -> str:
    """Build + start the Next.js frontend on a free port; yield the base URL."""
    if shutil.which("npm") is None:
        pytest.skip("npm not found on PATH; cannot run frontend integration test")
    if not (FRONTEND_DIR / "node_modules").exists():
        pytest.fail(
            f"Frontend dependencies are not installed. "
            f"Run `npm install` inside {FRONTEND_DIR}."
        )

    # NEXT_PUBLIC_* values are baked at build time, so the build needs to know
    # which backend the frontend should call.
    build_env = {
        **os.environ,
        "BROWSER": "none",
        "NEXT_PUBLIC_API_URL": backend_server,
    }
    build = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(FRONTEND_DIR),
        env=build_env,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        raise RuntimeError(
            f"`npm run build` failed in {FRONTEND_DIR} (exit {build.returncode}).\n"
            f"--- stdout ---\n{build.stdout}\n--- stderr ---\n{build.stderr}"
        )

    port = _free_port()
    env = {
        **os.environ,
        "PORT": str(port),
        "BROWSER": "none",
        "NEXT_PUBLIC_API_URL": backend_server,
    }
    proc = subprocess.Popen(
        ["npm", "run", "start"],
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(base_url, proc, SERVER_READY_TIMEOUT_S, "Frontend (next start)")
        yield base_url
    finally:
        _terminate(proc)


def test_full_quiz_flow_renders_result(frontend_server: str, page) -> None:
    """Walk all 15 questions and verify a result card renders."""
    page.goto(f"{frontend_server}/", wait_until="networkidle")

    start_btn = page.get_by_text("START QUIZ ▶")
    expect(start_btn).to_be_visible()
    start_btn.click()

    for i in range(1, 16):
        expect(page.get_by_text(f"QUESTION {i} OF 15")).to_be_visible()
        page.locator(".option-btn").first.click()
        page.locator(".next-btn").click()

    expect(page.locator(".result-card")).to_be_visible()
    expect(page.locator(".result-headline")).not_to_be_empty()
    expect(page.locator(".result-type")).not_to_be_empty()
    expect(page.locator(".type-tag")).not_to_be_empty()
