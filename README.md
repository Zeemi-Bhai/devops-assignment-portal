# DevOps Assignment Submission Portal

A lightweight Flask web application for submitting and viewing university assignment details. The project also includes isolated pytest tests, a local HTTP receiver that stores real test execution reports as JSON, GitHub Actions CI, and a static GitHub Pages demo.

## Technologies

- Python 3.12
- Flask 3.1.3
- HTML5 and CSS3
- JSON file storage
- Pytest 9.2.0
- Requests 2.34.2

## Project Structure

```text
devops-assignment-portal/
├── .github/
│   └── workflows/
│       └── ci.yml           # Test reporting and GitHub Pages deployment
├── app/
│   ├── __init__.py          # Flask application factory
│   └── routes.py            # Form handling, validation, and JSON storage
├── data/
│   └── submissions.json     # Assignment submissions created at runtime
├── docs/
│   └── index.html           # Static GitHub Pages demo
├── receiver/
│   └── server.py            # Local HTTP test report receiver
├── scripts/
│   └── run_tests.py         # Runs pytest and delivers the test report
├── templates/
│   └── index.html           # Submission portal interface
├── tests/
│   └── test_submissions.py  # Automated application tests
├── requirements.txt
├── run.py
└── test-report.json         # Latest received test report
```

`data/submissions.json` and `test-report.json` are generated runtime files and are excluded from Git by `.gitignore`.

## Static GitHub Pages Demo

`docs/index.html` is a self-contained static demonstration of the portal interface. It uses plain HTML, CSS, and JavaScript, with browser-side required-field and HTTP/HTTPS URL validation. Its submitted assignments include sample entries and newly added demo entries.

The static demo does not connect to the Flask backend, send data to a server, or save data persistently. Refreshing the page restores only the bundled sample entries.

## Prerequisites

- Windows
- Python 3.12 installed and available as `python`
- Internet access when installing packages from `requirements.txt`

## Installation

Open PowerShell in the project directory and install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Windows Virtual Environment

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell activation is restricted, use Command Prompt instead:

```bat
venv\Scripts\activate.bat
```

Then install the dependencies inside the activated environment:

```powershell
python -m pip install -r requirements.txt
```

## Run the Flask Application

From the project root:

```powershell
python run.py
```

Open <http://127.0.0.1:5000/> in a browser. Valid assignment submissions are appended to `data/submissions.json` and displayed below the form.

## Run Automated Tests

Run the application tests directly with:

```powershell
python -m pytest -v
```

The tests use Flask's test client and a separate temporary JSON file for each test, so the real `data/submissions.json` is not modified.

## Start the Local Report Receiver

The receiver must run in a separate terminal:

```powershell
python receiver/server.py
```

It listens at `http://127.0.0.1:5001` and accepts JSON reports at `POST /report`. It validates the report and overwrites the project-root `test-report.json` with the latest valid report.

## Generate and Send a Test Report

With the receiver running, execute the report runner from another terminal:

```powershell
python scripts/run_tests.py
```

The runner executes the tests, captures each test name, result, and failure message, calculates the totals, and sends the report to `http://127.0.0.1:5001/report`. It returns pytest's non-zero exit code when a test fails. If report delivery fails during a passing run, it also returns a non-zero code.

## JSON Test Report

The receiver stores reports with this structure:

```json
{
  "repository": "devops-assignment-portal",
  "branch": "main",
  "commit_sha": "commit-hash",
  "run_id": "pipeline-run-id",
  "timestamp": "2026-11-08T08:17:28.091917+00:00",
  "tests": [
    {
      "name": "tests/test_submissions.py::test_successful_assignment_submission_is_saved_and_displayed",
      "result": "passed",
      "failure_message": null
    }
  ],
  "total": 3,
  "passed": 3,
  "failed": 0,
  "status": "passed"
}
```

- `repository`, `branch`, `commit_sha`, and `run_id` come from GitHub Actions environment variables when available.
- `timestamp` is generated at runtime as an ISO-8601 timestamp.
- `tests` contains actual pytest results. A failed test includes its failure message.
- `total`, `passed`, and `failed` are calculated from the collected results.
- `status` is `passed` when there are no failed tests; otherwise it is `failed`.

## GitHub Actions CI and Pages Deployment

`.github/workflows/ci.yml` runs on every push and supports manual `workflow_dispatch` runs.

The `test` job runs on the self-hosted runner with labels `[self-hosted, Windows, X64]`. It installs `requirements.txt`, then runs `python scripts/run_tests.py`, which executes pytest, sends the actual report to the local receiver at `http://127.0.0.1:5001/report`, and preserves a non-zero exit code when tests fail. Because the runner is self-hosted on the same Windows computer, `127.0.0.1` reaches the local receiver; start it before running the workflow.

The separate `deploy` job only starts after the `test` job succeeds and only when the pushed branch is `main`. It publishes the `docs/` folder to GitHub Pages with the official Pages actions. It uses GitHub-hosted `ubuntu-latest` because Pages deployment does not need access to the local receiver.

One-time repository setup: open **Settings → Pages** and set **Source** to **GitHub Actions**. The repository must be public, or the GitHub account must support Pages for private repositories.

## Future Improvements

Additional CI features such as email notifications can be added later without changing the Flask application or its test suite.