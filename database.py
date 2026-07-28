# -*- coding: utf-8 -*-
"""Acces base de donnees SQLite."""
from __future__ import print_function, unicode_literals
import os
import hashlib
import sqlite3
from datetime import date

from src.config import DB_PATH, DATA_DIR, DEFAULT_USER, DEFAULT_PASSWORD


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def next_eleveur_code():
    conn = get_conn()
    row = conn.execute(
        "SELECT code_unique FROM eleveurs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row and row["code_unique"]:
        try:
            num = int(
                row["code_unique"].replace("ELV-", "").replace("elv-", "")
            )
            return "ELV-%03d" % (num + 1)
        except Exception:
            pass
    return "ELV-001"


def get_param(cle, defaut=""):
    conn = get_conn()
    row = conn.execute(
        "SELECT valeur FROM parametres WHERE cle=?", (cle,)
    ).fetchone()
    conn.close()
    return row["valeur"] if row else defaut


def set_param(cle, valeur):
    conn = get_conn()
    if conn.execute("SELECT id FROM parametres WHERE cle=?", (cle,)).fetchone():
        conn.execute(
            "UPDATE parametres SET valeur=? WHERE cle=?", (valeur, cle)
        )
    else:
        conn.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?)", (cle, valeur)
        )
    conn.commit()
    conn.close()


def init_db():
    conn = get_conn()
    c = conn.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
            nom_complet TEXT, role TEXT DEFAULT 'admin')""",
        """CREATE TABLE IF NOT EXISTS eleveurs (
            id INTEGER PRIMARY KEY, code_unique TEXT UNIQUE, nom TEXT, prenom TEXT,
            telephone TEXT, adresse TEXT, region TEXT, date_adhesion TEXT,
            statut TEXT DEFAULT 'actif')""",
        """CREATE TABLE IF NOT EXISTS collectes (
            id INTEGER PRIMARY KEY, numero_bon TEXT UNIQUE, eleveur_id INTEGER,
            date_heure TEXT, quantite REAL, acidite REAL, densite REAL,
            agent TEXT, vehicule TEXT)""",
        """CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY, reference TEXT UNIQUE, nom TEXT, prix REAL,
            stock REAL DEFAULT 0, seuil_alerte REAL DEFAULT 10)""",
        """CREATE TABLE IF NOT EXISTS ventes (
            id INTEGER PRIMARY KEY, numero TEXT UNIQUE, eleveur_id INTEGER,
            produit_id INTEGER, quantite REAL, montant REAL,
            mode TEXT DEFAULT 'credit', date_vente TEXT)""",
        """CREATE TABLE IF NOT EXISTS factures (
            id INTEGER PRIMARY KEY, numero TEXT UNIQUE, eleveur_id INTEGER,
            date_facture TEXT, periode_debut TEXT, periode_fin TEXT,
            credit_lait REAL, debit_aliments REAL, debit_avances REAL,
            solde REAL, statut TEXT DEFAULT 'impaye', mode_reglement TEXT)""",
        """CREATE TABLE IF NOT EXISTS avances (
            id INTEGER PRIMARY KEY, eleveur_id INTEGER, date_avance TEXT,
            montant REAL, motif TEXT, statut TEXT DEFAULT 'non_deduite')""",
        """CREATE TABLE IF NOT EXISTS agrements (
            id INTEGER PRIMARY KEY, reference TEXT UNIQUE, type_agrement TEXT,
            cible TEXT, date_delivrance TEXT, date_expiration TEXT,
            statut TEXT DEFAULT 'valide')""",
        """CREATE TABLE IF NOT EXISTS expeditions (
            id INTEGER PRIMARY KEY, numero_bordereau TEXT UNIQUE,
            date_expedition TEXT, destination TEXT, quantite_totale REAL,
            temperature REAL, vehicule TEXT, agent TEXT,
            statut TEXT DEFAULT 'en_transit', observations TEXT)""",
        """CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY, code TEXT UNIQUE, nom TEXT, type_client TEXT,
            telephone TEXT, adresse TEXT, contact TEXT, notes TEXT)""",
        """CREATE TABLE IF NOT EXISTS parametres (
            id INTEGER PRIMARY KEY, cle TEXT UNIQUE, valeur TEXT)""",
    ]
    for t in tables:
        c.execute(t)

    for col in [
        "ALTER TABLE collectes ADD COLUMN acidite REAL",
        "ALTER TABLE collectes ADD COLUMN densite REAL",
        "ALTER TABLE factures ADD COLUMN mode_reglement TEXT",
        "ALTER TABLE factures ADD COLUMN periode_debut TEXT",
        "ALTER TABLE factures ADD COLUMN periode_fin TEXT",
        "ALTER TABLE factures ADD COLUMN debit_avances REAL",
        "ALTER TABLE eleveurs ADD COLUMN region TEXT",
    ]:
        try:
            c.execute(col)
        except Exception:
            pass

    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        pwd = hashlib.sha256(DEFAULT_PASSWORD.encode("utf-8")).hexdigest()
        c.execute(
            "INSERT INTO users (username, password_hash, nom_complet, role) VALUES (?,?,?,?)",
            (DEFAULT_USER, pwd, "Administrateur", "admin"),
        )

    if c.execute("SELECT COUNT(*) FROM eleveurs").fetchone()[0] == 0:
        elevs = [
            ("ELV-001", "Diallo", "Amadou", "0550000001", "Village Nord", "Blida", date.today().isoformat(), "actif"),
            ("ELV-002", "Benali", "Fatima", "0550000002", "Village Sud", "Medea", date.today().isoformat(), "actif"),
            ("ELV-003", "Khelil", "Mohamed", "0550000003", "Douar Est", "Tipaza", date.today().isoformat(), "actif"),
            ("ELV-004", "Saidi", "Karim", "0550000004", "Zone Ouest", "Blida", date.today().isoformat(), "actif"),
        ]
        c.executemany(
            "INSERT INTO eleveurs (code_unique,nom,prenom,telephone,adresse,region,date_adhesion,statut) VALUES (?,?,?,?,?,?,?,?)",
            elevs,
        )

    if c.execute("SELECT COUNT(*) FROM produits").fetchone()[0] == 0:
        prods = [
            ("ALIM-001", "Tourteau de coton", 4500, 500, 50),
            ("ALIM-002", "Son de ble", 3200, 300, 30),
            ("ALIM-003", "Complement mineral", 8500, 80, 10),
        ]
        c.executemany(
            "INSERT INTO produits (reference,nom,prix,stock,seuil_alerte) VALUES (?,?,?,?,?)",
            prods,
        )

    if c.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0:
        clients = [
            ("LAIT-001", "Laiterie Centrale Alger", "laiterie", "021000001", "Alger", "M. Boudiaf", ""),
            ("LAIT-002", "Laiterie du Sahel", "laiterie", "024000002", "Tipaza", "Mme Cherif", ""),
        ]
        c.executemany(
            "INSERT INTO clients (code,nom,type_client,telephone,adresse,contact,notes) VALUES (?,?,?,?,?,?,?)",
            clients,
        )

    defaults = {
        "nom_centre": "Centre de Collecte de Lait",
        "adresse_centre": "Route Nationale, Wilaya de Blida",
        "tel_centre": "025 00 00 00",
        "rc_centre": "RC 00/00-0000000B00",
        "nif_centre": "000000000000000",
        "entete_facture": "Centre de Collecte de Lait\nRoute Nationale - Blida\nTel: 025 00 00 00",
        "pied_facture": "Merci de votre confiance - Document genere automatiquement",
    }
    for k, v in defaults.items():
        if not c.execute("SELECT id FROM parametres WHERE cle=?", (k,)).fetchone():
            c.execute("INSERT INTO parametres (cle, valeur) VALUES (?,?)", (k, v))

    conn.commit()
    conn.close()
    print("Base de donnees prete.")
