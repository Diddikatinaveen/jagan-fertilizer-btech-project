import os

# Importing app.py runs additive migrations, so tests must select an isolated DB first.
os.environ["DATABASE_URL"] = "sqlite://"

import app as project

if project.app.config["SQLALCHEMY_DATABASE_URI"] != "sqlite://":
    raise RuntimeError("Tests must use the isolated in-memory SQLite database.")
