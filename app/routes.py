import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for


main = Blueprint("main", __name__)

REQUIRED_FIELDS = {
    "name": "Student name",
    "registration_number": "Registration number",
    "assignment_title": "Assignment title",
    "submission_url": "Submission URL",
}
HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}\.?$)([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.?$"
)


def load_submissions(data_file):
    try:
        submissions = json.loads(Path(data_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return submissions if isinstance(submissions, list) else []


def save_submissions(data_file, submissions):
    Path(data_file).write_text(
        json.dumps(submissions, indent=2),
        encoding="utf-8",
    )


def is_valid_submission_url(value):
    if any(character.isspace() for character in value):
        return False
    try:
        parsed_url = urlsplit(value)
        hostname = parsed_url.hostname
        parsed_url.port
    except ValueError:
        return False

    return (
        parsed_url.scheme in {"http", "https"}
        and bool(parsed_url.netloc)
        and bool(hostname)
        and bool(HOSTNAME_PATTERN.fullmatch(hostname))
    )


@main.route("/", methods=["GET", "POST"])
def index():
    form_values = {field: "" for field in REQUIRED_FIELDS}

    if request.method == "POST":
        form_values = {
            field: request.form.get(field, "").strip()
            for field in REQUIRED_FIELDS
        }
        errors = []

        for field, label in REQUIRED_FIELDS.items():
            if field != "registration_number" and not form_values[field]:
                errors.append(f"{label} is required.")

        if form_values["submission_url"] and not is_valid_submission_url(
            form_values["submission_url"]
        ):
            errors.append("Submission URL must be a valid HTTP or HTTPS URL.")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            submissions = load_submissions(current_app.config["DATA_FILE"])
            submissions.append(form_values)
            save_submissions(current_app.config["DATA_FILE"], submissions)
            flash("Assignment submitted successfully.", "success")
            return redirect(url_for("main.index"))

    submissions = load_submissions(current_app.config["DATA_FILE"])
    return render_template("index.html", form_values=form_values, submissions=submissions)