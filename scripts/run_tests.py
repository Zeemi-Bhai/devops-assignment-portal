import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_URL = "http://127.0.0.1:5001/report"


class PytestResultCollector:
    def __init__(self):
        self.results = {}

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.failed or report.skipped:
            if report.passed:
                result = "passed"
                failure_message = None
            elif report.skipped:
                result = "skipped"
                failure_message = None
            else:
                result = "failed"
                failure_message = str(report.longrepr)

            self.results[report.nodeid] = {
                "name": report.nodeid,
                "result": result,
                "failure_message": failure_message,
            }


def git_value(*arguments):
    completed = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def collect_ci_metadata():
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "repository": os.environ.get("GITHUB_REPOSITORY")
        or PROJECT_ROOT.name,
        "branch": os.environ.get("GITHUB_REF_NAME") or git_value(
            "branch", "--show-current"
        )
        or "unknown",
        "commit_sha": os.environ.get("GITHUB_SHA") or git_value("rev-parse", "HEAD")
        or "unknown",
        "run_id": os.environ.get("GITHUB_RUN_ID") or f"local-{timestamp}",
        "timestamp": timestamp,
    }


def build_report(collector, exit_code):
    tests = list(collector.results.values())
    passed = sum(test["result"] == "passed" for test in tests)
    failed = sum(test["result"] == "failed" for test in tests)
    return {
        **collect_ci_metadata(),
        "tests": tests,
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "status": "failed" if exit_code != 0 or failed else "passed",
    }


def main():
    sys.path.insert(0, str(PROJECT_ROOT))
    collector = PytestResultCollector()
    pytest_exit_code = int(pytest.main(["-v", "tests"], plugins=[collector]))
    report = build_report(collector, pytest_exit_code)

    try:
        response = requests.post(REPORT_URL, json=report, timeout=10)
        response.raise_for_status()
        print(f"Test report delivered to {REPORT_URL}")
    except requests.RequestException as error:
        print(f"Unable to deliver test report: {error}", file=sys.stderr)
        if pytest_exit_code == 0:
            return 1

    return pytest_exit_code


if __name__ == "__main__":
    raise SystemExit(main())