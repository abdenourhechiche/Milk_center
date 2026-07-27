#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centre de Collecte de Lait - Point d'entree
Compatible Python 3.6 / Windows 7 32-64 bits
Monnaie : Dinar Algerien (DA)

Lancement developpement : python main.py
Lancement compile       : CentreCollecteLait.exe
"""
from __future__ import print_function, unicode_literals
import os
import sys

# Dossier de base (exe ou script)
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))

if BASE not in sys.path:
    sys.path.insert(0, BASE)

from src.database import init_db
from src.ui.login import LoginWindow


def main():
    init_db()
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
