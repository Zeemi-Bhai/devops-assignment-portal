import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_SETTINGS = (
    "MAIL_SERVER",
    "MAIL_PORT",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_FROM",
    "MAIL_TO",
)


def report_candidates():
    configured = os.environ.get("TEST_REPORT_FILE", "").strip()
    candidates = [Path(configured)] if configured else [PROJECT_ROOT / "test-report.json"]

    # The self-hosted runner checks out under _work/, while the receiver writes
    # test-report.json beside the main project folder. Search those roots too.
    workspace = os.environ.get("GITHUB_WORKSPACE", "").strip()
    if workspace:
        workspace_path = Path(workspace).resolve()
        candidates.extend(
            root / "test-report.json"
            for root in (workspace_path, workspace_path.parent)
        )

    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def find_report():
    candidates = report_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise RuntimeError(
        f"Test report not found. Searched: {searched}. "
        "Ensure the local receiver is running so scripts/run_tests.py can save it."
    )


def load_report():
    report_file = find_report()
    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"Unable to read test report {report_file}: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Test report is not valid JSON: {error}") from error

    if not isinstance(report, dict) or report.get("status") not in {"passed", "failed"}:
        raise RuntimeError("Test report does not contain a valid status.")
    return report


def load_settings():
    missing = [name for name in REQUIRED_SETTINGS if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"Missing email settings: {', '.join(missing)}.")

    try:
        port = int(os.environ["MAIL_PORT"])
    except ValueError:
        raise RuntimeError("MAIL_PORT must be an integer.") from None

    return {
        "server": os.environ["MAIL_SERVER"].strip(),
        "port": port,
        "username": os.environ["MAIL_USERNAME"].strip(),
        "password": os.environ["MAIL_PASSWORD"],
        "sender": os.environ["MAIL_FROM"].strip(),
        "recipients": [
            address.strip()
            for address in os.environ["MAIL_TO"].split(",")
            if address.strip()
        ],
    }


def build_message(report, settings):
    status = report["status"]
    subject = (
        f"[CI {status.upper()}] {report['repository']} - {report['branch']} "
        f"(run {report['run_id']})"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = ", ".join(settings["recipients"])

    text_lines = [
        "Assignment Portal CI test report",
        "",
        f"Repository: {report['repository']}",
        f"Branch: {report['branch']}",
        f"Commit: {report['commit_sha']}",
        f"Run ID: {report['run_id']}",
        f"Timestamp: {report['timestamp']}",
        f"Status: {status.upper()}",
        f"Tests: {report['total']} total, {report['passed']} passed, {report['failed']} failed",
        "",
    ]
    for test in report["tests"]:
        text_lines.append(f"[{test['result'].upper()}] {test['name']}")
        if test["failure_message"]:
            text_lines.extend(("", test["failure_message"], ""))
    message.set_content("\n".join(text_lines))

    rows = "".join(
        "<tr>"
        f"<td>{escape(test['name'])}</td>"
        f"<td class='{escape(test['result'])}'>{escape(test['result'].upper())}</td>"
        f"<td><pre>{escape(test['failure_message'] or '')}</pre></td>"
        "</tr>"
        for test in report["tests"]
    )
    html = f"""\
<!doctype html>
<html lang="en">
<body style="margin:0;padding:24px;background:#f3f7fa;color:#1b2b3a;font-family:Segoe UI,Arial,sans-serif;">
  <table role="presentation" style="width:100%;max-width:800px;margin:0 auto;border-collapse:collapse;background:#ffffff;border:1px solid #d7e2eb;">
    <tr>
      <td style="padding:22px 26px;background:#12355b;color:#ffffff;">
        <h1 style="margin:0;font-size:21px;">Assignment Portal CI Report</h1>
        <p style="margin:7px 0 0;color:#d8e9f5;">{escape(report['repository'])} &middot; {escape(report['branch'])}</p>
      </td>
    </tr>
    <tr>
      <td style="padding:22px 26px;">
        <p style="margin:0 0 16px;font-size:17px;">
          Result: <strong style="color:{'#176b4d' if status == 'passed' else '#a23838'};">{escape(status.upper())}</strong>
        </p>
        <table role="presentation" style="border-collapse:collapse;margin-bottom:22px;font-size:14px;">
          <tr><td style="padding:4px 18px 4px 0;color:#607387;">Total tests</td><td>{report['total']}</td></tr>
          <tr><td style="padding:4px 18px 4px 0;color:#607387;">Passed</td><td>{report['passed']}</td></tr>
          <tr><td style="padding:4px 18px 4px 0;color:#607387;">Failed</td><td>{report['failed']}</td></tr>
          <tr><td style="padding:4px 18px 4px 0;color:#607387;">Commit</td><td><code>{escape(report['commit_sha'])}</code></td></tr>
          <tr><td style="padding:4px 18px 4px 0;color:#607387;">Run ID</td><td>{escape(report['run_id'])}</td></tr>
          <tr><td style="padding:4px 18px 4px 0;color:#607387;">Timestamp</td><td>{escape(report['timestamp'])}</td></tr>
        </table>
        <table role="presentation" style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#eaf4fb;text-align:left;">
              <th style="padding:10px;border:1px solid #d7e2eb;">Test</th>
              <th style="padding:10px;border:1px solid #d7e2eb;">Result</th>
              <th style="padding:10px;border:1px solid #d7e2eb;">Failure</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    message.add_alternative(html, subtype="html")
    return message


def send_message(message, settings):
    context = ssl.create_default_context()
    if settings["port"] == 465:
        with smtplib.SMTP_SSL(
            settings["server"], settings["port"], context=context, timeout=30
        ) as smtp:
            smtp.login(settings["username"], settings["password"])
            smtp.send_message(message)
        return

    with smtplib.SMTP(settings["server"], settings["port"], timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(settings["username"], settings["password"])
        smtp.send_message(message)


def main():
    try:
        settings = load_settings()
        report = load_report()
        message = build_message(report, settings)
        send_message(message, settings)
    except (OSError, RuntimeError, smtplib.SMTPException) as error:
        print(f"Unable to send test report email: {error}", flush=True)
        return 1

    print(f"Test report email sent to {', '.join(settings['recipients'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
