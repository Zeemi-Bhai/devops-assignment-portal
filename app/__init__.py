from pathlib import Path

from flask import Flask


def create_app(test_config=None):
    project_root = Path(__file__).parent.parent
    app = Flask(__name__, template_folder=str(project_root / "templates"))
    app.config.from_mapping(
        SECRET_KEY="devops-assignment-portal-development-key",
        DATA_FILE=project_root / "data" / "submissions.json",
    )

    if test_config is not None:
        app.config.update(test_config)

    data_file = Path(app.config["DATA_FILE"])
    data_file.parent.mkdir(parents=True, exist_ok=True)
    if not data_file.exists():
        data_file.write_text("[]", encoding="utf-8")

    from app.routes import main

    app.register_blueprint(main)
    return app