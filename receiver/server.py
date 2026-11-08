import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_FILE = PROJECT_ROOT / "test-report.json"
app = Flask(__name__)


def validate_report(report):
    if not isinstance(report, dict):
        return "Request body must be a JSON object."

    required_fields = {
        "repository",
        "branch",
        "commit_sha",
        "run_id",
        "timestamp",
        "tests",
        "total",
        "passed",
        "failed",
        "status",
    }
    missing_fields = sorted(required_fields - report.keys())
    if missing_fields:
        return f"Missing required report fields: {', '.join(missing_fields)}."

    for field in ("repository", "branch", "commit_sha", "run_id", "timestamp"):
        if not isinstance(report[field], str) or not report[field].strip():
            return f"{field} must be a non-empty string."

    try:
        timestamp = report["timestamp"].replace("Z", "+00:00")
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except ValueError:
        return "timestamp must be a valid ISO-8601 timestamp."
    if parsed_timestamp.tzinfo is None:
        return "timestamp must include a timezone."

    if not isinstance(report["tests"], list):
        return "tests must be a list."
    for test in report["tests"]:
        if not isinstance(test, dict):
            return "Each test result must be a JSON object."
        if not isinstance(test.get("name"), str) or not test["name"].strip():
            return "Each test result requires a non-empty name."
        if test.get("result") not in {"passed", "failed", "skipped"}:
            return "Each test result must be passed, failed, or skipped."
        if test.get("failure_message") is not None and not isinstance(
            test["failure_message"], str
        ):
            return "failure_message must be a string or null."

    for field in ("total", "passed", "failed"):
        if isinstance(report[field], bool) or not isinstance(report[field], int):
            return f"{field} must be an integer."
        if report[field] < 0:
            return f"{field} must not be negative."

    result_counts = {
        "total": len(report["tests"]),
        "passed": sum(test["result"] == "passed" for test in report["tests"]),
        "failed": sum(test["result"] == "failed" for test in report["tests"]),
    }
    for field, expected_value in result_counts.items():
        if report[field] != expected_value:
            return f"{field} does not match the supplied test results."

    expected_status = "failed" if report["failed"] else "passed"
    if report["status"] != expected_status:
        return f"status must be '{expected_status}' for the supplied test results."

    return None


@app.post("/report")
def receive_report():
    report = request.get_json(silent=True)
    validation_error = validate_report(report)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    REPORT_FILE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return jsonify({"message": "Test report saved successfully."}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)