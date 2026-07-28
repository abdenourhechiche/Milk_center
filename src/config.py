# -*- coding: utf-8 -*-
"""Configuration globale de l'application."""
from __future__ import unicode_literals
import os
import sys


def _base_dir():
    """Dossier racine : a cote de l'exe si compile, sinon dossier du projet."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _base_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
DB_PATH = os.path.join(DATA_DIR, "db.sqlite3")

MONNAIE = "DA"
DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "admin123"
