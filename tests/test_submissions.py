import json

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    data_file = tmp_path / "submissions.json"
    return create_app({"TESTING": True, "DATA_FILE": data_file})


@pytest.fixture
def client(app):
    return app.test_client()


def test_successful_assignment_submission_is_saved_and_displayed(client, app):
    submission = {
        "name": "Ali Khan",
        "registration_number": "FA24-BCS-001",
        "assignment_title": "DevOps Lab Mid",
        "submission_url": "https://github.com/example/assignment",
    }

    response = client.post("/", data=submission, follow_redirects=True)

    assert response.status_code == 200
    assert b"Assignment submitted successfully." in response.data
    assert b"Ali Khan" in response.data
    assert b"DevOps Lab Mid" in response.data

    stored_submissions = json.loads(app.config["DATA_FILE"].read_text(encoding="utf-8"))
    assert stored_submissions == [submission]


def test_missing_registration_number_is_rejected_and_not_saved(client, app):
    submission = {
        "name": "Ali Khan",
        "registration_number": "",
        "assignment_title": "DevOps Lab Mid",
        "submission_url": "https://github.com/example/assignment",
    }

    response = client.post("/", data=submission)

    assert response.status_code == 200
    assert b"Registration number is required." in response.data
    assert json.loads(app.config["DATA_FILE"].read_text(encoding="utf-8")) == []


def test_invalid_submission_url_is_rejected_and_not_saved(client, app):
    submission = {
        "name": "Ali Khan",
        "registration_number": "FA24-BCS-001",
        "assignment_title": "DevOps Lab Mid",
        "submission_url": "invalid-url",
    }

    response = client.post("/", data=submission)

    assert response.status_code == 200
    assert b"Submission URL must be a valid HTTP or HTTPS URL." in response.data
    assert json.loads(app.config["DATA_FILE"].read_text(encoding="utf-8")) == []