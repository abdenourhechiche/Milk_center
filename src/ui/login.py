# -*- coding: utf-8 -*-
"""Fenetre de connexion."""
from __future__ import print_function, unicode_literals
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox

from src.config import DEFAULT_USER, DEFAULT_PASSWORD
from src.database import get_conn


class LoginWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Centre Collecte Lait - Connexion")
        self.geometry("400x280")
        self.resizable(False, False)
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 200
        y = (self.winfo_screenheight() // 2) - 140
        self.geometry("+%d+%d" % (x, y))

        tk.Label(
            self, text="Centre de Collecte de Lait", font=("Arial", 14, "bold")
        ).pack(pady=(25, 5))
        tk.Label(self, text="Connexion", font=("Arial", 11)).pack(pady=(0, 15))

        frame = ttk.Frame(self)
        frame.pack()
        ttk.Label(frame, text="Utilisateur :").grid(
            row=0, column=0, sticky="e", padx=5, pady=8
        )
        self.username = ttk.Entry(frame, width=22)
        self.username.grid(row=0, column=1, padx=5, pady=8)
        self.username.insert(0, DEFAULT_USER)

        ttk.Label(frame, text="Mot de passe :").grid(
            row=1, column=0, sticky="e", padx=5, pady=8
        )
        self.password = ttk.Entry(frame, width=22, show="*")
        self.password.grid(row=1, column=1, padx=5, pady=8)
        self.password.insert(0, DEFAULT_PASSWORD)

        ttk.Button(self, text="Se Connecter", command=self.login).pack(pady=15)
        tk.Label(
            self,
            text="Compte demo : %s / %s" % (DEFAULT_USER, DEFAULT_PASSWORD),
            fg="gray",
            font=("Arial", 9),
        ).pack()
        self.bind("<Return>", lambda e: self.login())

    def login(self):
        user = self.username.get().strip()
        pwd = self.password.get()
        if not user or not pwd:
            messagebox.showerror("Erreur", "Remplissez tous les champs")
            return
        pwd_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
        conn = get_conn()
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (user, pwd_hash),
        ).fetchone()
        conn.close()
        if row:
            self.destroy()
            from src.ui.window import MainWindow

            MainWindow(row)
        else:
            messagebox.showerror("Erreur", "Identifiants incorrects")
