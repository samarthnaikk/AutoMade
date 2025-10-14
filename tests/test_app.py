import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path so tests can import app.py
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app import app, DATA_DIR
import os


def test_post_task(tmp_path, monkeypatch):
    client = app.test_client()
    payload = {
        "email": "student@example.com",
        "secret": "s3cr3t",
        "task": "captcha-solver-test",
        "round": 1,
        "nonce": "ab12-345",
        "brief": "Create a captcha solver that handles ?url=/files/sample.png. Default to attached sample.",
        "checks": ["Repo has MIT license", "README.md is professional"],
        "evaluation_url": "http://example.com/notify",
        "attachments": [{"name": "sample.png", "url": "data:image/png;base64,iVBORw0KGgo="}]
    }

    resp = client.post('/task', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'view_url' in data
    # check file saved
    task_dir = DATA_DIR / 'captcha-solver-test'
    assert (task_dir / 'payload.json').exists()
