# -*- coding: utf-8 -*-
"""Module Eleveurs + Fiche eleveur."""
from __future__ import print_function, unicode_literals
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from src.database import get_conn, next_eleveur_code
from src.config import MONNAIE


class EleveursMixin(object):
    def show_eleveurs(self):
        self.clear()
        ttk.Label(
            self.main, text="Gestion des Eleveurs", font=("Arial", 15, "bold")
        ).pack(pady=6)
        tb = ttk.Frame(self.main)
        tb.pack(fill="x")
        ttk.Button(tb, text="Ajouter", command=self.add_eleveur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Modifier", command=self.edit_eleveur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Supprimer", command=self.del_eleveur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Fiche", command=self.fiche_from_list).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Actualiser", command=self.show_eleveurs).pack(
            side="left", padx=3
        )

        cols = ("id", "code", "nom", "prenom", "tel", "region", "statut")
        self.tree_elev = ttk.Treeview(
            self.main, columns=cols, show="headings", height=17
        )
        for c, t in zip(
            cols, ["ID", "Code", "Nom", "Prenom", "Telephone", "Region", "Statut"]
        ):
            self.tree_elev.heading(c, text=t)
            self.tree_elev.column(c, width=95)
        self.tree_elev.pack(fill="both", expand=True, pady=4)

        conn = get_conn()
        for r in conn.execute("SELECT * FROM eleveurs ORDER BY nom"):
            self.tree_elev.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["code_unique"],
                    r["nom"],
                    r["prenom"],
                    r["telephone"],
                    r["region"] or "",
                    r["statut"],
                ),
            )
        conn.close()

    def fiche_from_list(self):
        sel = self.tree_elev.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un eleveur")
            return
        self._afficher_fiche(self.tree_elev.item(sel[0])["values"][0])

    def add_eleveur(self):
        self._form_eleveur()

    def edit_eleveur(self):
        sel = self.tree_elev.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un eleveur")
            return
        self._form_eleveur(self.tree_elev.item(sel[0])["values"][0])

    def del_eleveur(self):
        sel = self.tree_elev.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un eleveur")
            return
        if messagebox.askyesno("Confirmation", "Supprimer cet eleveur ?"):
            eid = self.tree_elev.item(sel[0])["values"][0]
            conn = get_conn()
            conn.execute("DELETE FROM eleveurs WHERE id=?", (eid,))
            conn.commit()
            conn.close()
            self.show_eleveurs()

    def _form_eleveur(self, eid=None):
        win = tk.Toplevel(self)
        win.title("Eleveur")
        win.geometry("380x360")
        win.grab_set()

        ttk.Label(win, text="Code unique").grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        code_e = ttk.Entry(win, width=28)
        code_e.grid(row=0, column=1, padx=5, pady=5)

        fields = {}
        for i, (key, label) in enumerate(
            [
                ("nom", "Nom *"),
                ("prenom", "Prenom *"),
                ("tel", "Telephone"),
                ("adresse", "Adresse"),
                ("region", "Region"),
            ],
            1,
        ):
            ttk.Label(win, text=label).grid(
                row=i, column=0, sticky="e", padx=5, pady=5
            )
            e = ttk.Entry(win, width=28)
            e.grid(row=i, column=1, padx=5, pady=5)
            fields[key] = e

        statut_var = tk.StringVar(value="actif")
        ttk.Label(win, text="Statut").grid(
            row=6, column=0, sticky="e", padx=5, pady=5
        )
        ttk.Combobox(
            win,
            textvariable=statut_var,
            values=["actif", "inactif", "bloque"],
            state="readonly",
            width=26,
        ).grid(row=6, column=1, padx=5, pady=5)

        if eid:
            conn = get_conn()
            r = conn.execute(
                "SELECT * FROM eleveurs WHERE id=?", (eid,)
            ).fetchone()
            conn.close()
            if r:
                code_e.insert(0, r["code_unique"] or "")
                code_e.config(state="readonly")
                fields["nom"].insert(0, r["nom"] or "")
                fields["prenom"].insert(0, r["prenom"] or "")
                fields["tel"].insert(0, r["telephone"] or "")
                fields["adresse"].insert(0, r["adresse"] or "")
                fields["region"].insert(0, r["region"] or "")
                statut_var.set(r["statut"])
        else:
            code_e.insert(0, next_eleveur_code())
            code_e.config(state="readonly")

        def save():
            nom = fields["nom"].get().strip()
            prenom = fields["prenom"].get().strip()
            if not nom or not prenom:
                messagebox.showerror("Erreur", "Nom et prenom obligatoires")
                return
            code = code_e.get().strip()
            conn = get_conn()
            if eid:
                conn.execute(
                    "UPDATE eleveurs SET nom=?,prenom=?,telephone=?,adresse=?,region=?,statut=? WHERE id=?",
                    (
                        nom,
                        prenom,
                        fields["tel"].get().strip(),
                        fields["adresse"].get().strip(),
                        fields["region"].get().strip(),
                        statut_var.get(),
                        eid,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO eleveurs (code_unique,nom,prenom,telephone,adresse,region,date_adhesion,statut) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        code,
                        nom,
                        prenom,
                        fields["tel"].get().strip(),
                        fields["adresse"].get().strip(),
                        fields["region"].get().strip(),
                        date.today().isoformat(),
                        statut_var.get(),
                    ),
                )
            conn.commit()
            conn.close()
            win.destroy()
            self.show_eleveurs()

        ttk.Button(win, text="Enregistrer", command=save).grid(
            row=7, column=0, columnspan=2, pady=12
        )

    def show_fiche_eleveur(self):
        self.clear()
        ttk.Label(
            self.main, text="Fiche Eleveur", font=("Arial", 15, "bold")
        ).pack(pady=8)
        conn = get_conn()
        elevs = conn.execute(
            "SELECT id, code_unique, nom, prenom FROM eleveurs ORDER BY nom"
        ).fetchall()
        conn.close()
        if not elevs:
            ttk.Label(self.main, text="Aucun eleveur").pack()
            return
        frame = ttk.Frame(self.main)
        frame.pack(pady=5)
        ttk.Label(frame, text="Choisir eleveur :").pack(side="left", padx=5)
        elev_var = tk.StringVar()
        opts = [
            "%d - %s %s (%s)" % (e["id"], e["nom"], e["prenom"], e["code_unique"])
            for e in elevs
        ]
        ttk.Combobox(
            frame, textvariable=elev_var, values=opts, state="readonly", width=45
        ).pack(side="left", padx=5)
        elev_var.set(opts[0])

        def afficher():
            self._afficher_fiche(int(elev_var.get().split(" - ")[0]))

        ttk.Button(frame, text="Afficher la fiche", command=afficher).pack(
            side="left", padx=8
        )

    def _afficher_fiche(self, eid):
        self.clear()
        conn = get_conn()
        elev = conn.execute(
            "SELECT * FROM eleveurs WHERE id=?", (eid,)
        ).fetchone()
        if not elev:
            conn.close()
            return

        ttk.Label(
            self.main,
            text="Fiche : %s %s (%s)"
            % (elev["nom"], elev["prenom"], elev["code_unique"]),
            font=("Arial", 14, "bold"),
        ).pack(pady=6)

        info = ttk.LabelFrame(self.main, text="Informations", padding=8)
        info.pack(fill="x", padx=10, pady=5)
        ttk.Label(
            info,
            text="Tel: %s | Region: %s | Adresse: %s | Statut: %s"
            % (
                elev["telephone"] or "-",
                elev["region"] or "-",
                elev["adresse"] or "-",
                elev["statut"],
            ),
        ).pack(anchor="w")

        total_l = conn.execute(
            "SELECT COALESCE(SUM(quantite),0) FROM collectes WHERE eleveur_id=?",
            (eid,),
        ).fetchone()[0]
        nb_col = conn.execute(
            "SELECT COUNT(*) FROM collectes WHERE eleveur_id=?", (eid,)
        ).fetchone()[0]
        total_v = conn.execute(
            "SELECT COALESCE(SUM(montant),0) FROM ventes WHERE eleveur_id=?",
            (eid,),
        ).fetchone()[0]
        total_av = conn.execute(
            "SELECT COALESCE(SUM(montant),0) FROM avances WHERE eleveur_id=? AND statut='non_deduite'",
            (eid,),
        ).fetchone()[0]

        stats = ttk.LabelFrame(self.main, text="Resume", padding=8)
        stats.pack(fill="x", padx=10, pady=5)
        ttk.Label(
            stats,
            text="Collectes: %d | Volume: %.0f L | Achats: %.0f %s | Avances non deduites: %.0f %s"
            % (nb_col, total_l, total_v, MONNAIE, total_av, MONNAIE),
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")

        cf = ttk.LabelFrame(self.main, text="Dernieres collectes", padding=5)
        cf.pack(fill="x", padx=10, pady=5)
        cols = ("date", "qte", "acidite", "densite", "agent")
        tree = ttk.Treeview(cf, columns=cols, show="headings", height=5)
        for c, t in zip(cols, ["Date", "Qte", "Acidite", "Densite", "Agent"]):
            tree.heading(c, text=t)
            tree.column(c, width=110)
        tree.pack(fill="x")
        for r in conn.execute(
            "SELECT * FROM collectes WHERE eleveur_id=? ORDER BY date_heure DESC LIMIT 10",
            (eid,),
        ):
            tree.insert(
                "",
                "end",
                values=(
                    (r["date_heure"] or "")[:16],
                    "%.1f" % (r["quantite"] or 0),
                    r["acidite"] if r["acidite"] is not None else "-",
                    r["densite"] if r["densite"] is not None else "-",
                    r["agent"] or "",
                ),
            )

        af = ttk.LabelFrame(self.main, text="Avances", padding=5)
        af.pack(fill="x", padx=10, pady=5)
        cols2 = ("date", "montant", "motif", "statut")
        tree2 = ttk.Treeview(af, columns=cols2, show="headings", height=4)
        for c, t in zip(cols2, ["Date", "Montant", "Motif", "Statut"]):
            tree2.heading(c, text=t)
            tree2.column(c, width=130)
        tree2.pack(fill="x")
        for r in conn.execute(
            "SELECT * FROM avances WHERE eleveur_id=? ORDER BY date_avance DESC",
            (eid,),
        ):
            tree2.insert(
                "",
                "end",
                values=(
                    (r["date_avance"] or "")[:10],
                    "%.0f %s" % (r["montant"] or 0, MONNAIE),
                    r["motif"] or "",
                    r["statut"],
                ),
            )
        conn.close()
        ttk.Button(
            self.main, text="Retour liste", command=self.show_eleveurs
        ).pack(pady=8)
