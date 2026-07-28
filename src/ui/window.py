# -*- coding: utf-8 -*-
"""Fenetre principale de l'application."""
from __future__ import print_function, unicode_literals
import tkinter as tk
from tkinter import ttk

from src.database import get_param
from src.ui.modules_eleveurs import EleveursMixin
from src.ui.modules_ventes import VentesMixin
from src.ui.modules_autres import (
    CollectesMixin,
    AvancesMixin,
    FacturationMixin,
    DiversMixin,
)


class MainWindow(
    tk.Tk,
    EleveursMixin,
    VentesMixin,
    CollectesMixin,
    AvancesMixin,
    FacturationMixin,
    DiversMixin,
):
    def __init__(self, user):
        tk.Tk.__init__(self)
        self.user = dict(user)
        nom = get_param("nom_centre", "Centre Collecte Lait")
        self.title(
            "%s - %s"
            % (nom, self.user.get("nom_complet") or self.user.get("username"))
        )
        self.geometry("1180x740")

        sidebar = tk.Frame(self, width=190, bg="#2c3e50")
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="MENU",
            bg="#2c3e50",
            fg="white",
            font=("Arial", 13, "bold"),
        ).pack(pady=12)

        menus = [
            ("Tableau de Bord", self.show_dashboard),
            ("Eleveurs", self.show_eleveurs),
            ("Fiche Eleveur", self.show_fiche_eleveur),
            ("Collectes", self.show_collectes),
            ("Ventes / Stock", self.show_ventes),
            ("Avances", self.show_avances),
            ("Facturation", self.show_facturation),
            ("Agrements", self.show_agrements),
            ("Expeditions", self.show_expeditions),
            ("Laiteries / Clients", self.show_clients),
            ("Parametres Centre", self.show_parametres),
            ("Mon Compte", self.show_compte),
            ("Rapports", self.show_reports),
        ]
        for text, cmd in menus:
            tk.Button(
                sidebar,
                text=text,
                command=cmd,
                width=21,
                anchor="w",
                bg="#34495e",
                fg="white",
                relief="flat",
                activebackground="#1abc9c",
                font=("Arial", 9),
            ).pack(pady=2, padx=5)

        tk.Button(
            sidebar,
            text="Quitter",
            command=self.quit,
            width=21,
            bg="#c0392b",
            fg="white",
            relief="flat",
            font=("Arial", 10),
        ).pack(side="bottom", pady=10, padx=5)

        self.main = ttk.Frame(self)
        self.main.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        self.show_dashboard()

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()
