# -*- coding: utf-8 -*-
"""Module Collecteurs - chaque eleveur est relie a un collecteur."""
from __future__ import print_function, unicode_literals
import tkinter as tk
from tkinter import ttk, messagebox

from src.database import get_conn
from src.utils import imprimer_fichier, generer_fiche_collecteur
from src.config import MONNAIE


class CollecteursMixin(object):
    def show_collecteurs(self):
        self.clear()
        ttk.Label(
            self.main, text="Gestion des Collecteurs", font=("Arial", 15, "bold")
        ).pack(pady=6)
        tb = ttk.Frame(self.main)
        tb.pack(fill="x")
        ttk.Button(tb, text="Ajouter", command=self.add_collecteur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Modifier", command=self.edit_collecteur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Supprimer", command=self.del_collecteur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Fiche", command=self.fiche_collecteur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Imprimer fiche", command=self.print_fiche_collecteur).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Actualiser", command=self.show_collecteurs).pack(
            side="left", padx=3
        )

        cols = ("id", "code", "nom", "prenom", "tel", "region", "vehicule", "statut")
        self.tree_collec = ttk.Treeview(
            self.main, columns=cols, show="headings", height=16
        )
        for c, t in zip(
            cols,
            ["ID", "Code", "Nom", "Prenom", "Telephone", "Region", "Vehicule", "Statut"],
        ):
            self.tree_collec.heading(c, text=t)
            self.tree_collec.column(c, width=100)
        self.tree_collec.pack(fill="both", expand=True, pady=4)

        conn = get_conn()
        for r in conn.execute("SELECT * FROM collecteurs ORDER BY nom"):
            self.tree_collec.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["code"],
                    r["nom"],
                    r["prenom"],
                    r["telephone"] or "",
                    r["region"] or "",
                    r["vehicule"] or "",
                    r["statut"] or "",
                ),
            )
        conn.close()

    def add_collecteur(self):
        self._form_collecteur()

    def edit_collecteur(self):
        sel = self.tree_collec.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un collecteur")
            return
        self._form_collecteur(self.tree_collec.item(sel[0])["values"][0])

    def del_collecteur(self):
        sel = self.tree_collec.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un collecteur")
            return
        cid = self.tree_collec.item(sel[0])["values"][0]
        conn = get_conn()
        nb = conn.execute(
            "SELECT COUNT(*) FROM eleveurs WHERE collecteur_id=?", (cid,)
        ).fetchone()[0]
        if nb > 0:
            conn.close()
            messagebox.showerror(
                "Erreur",
                "Ce collecteur est relie a %d eleveur(s).\n"
                "Modifiez d'abord les eleveurs." % nb,
            )
            return
        if messagebox.askyesno("Confirmation", "Supprimer ce collecteur ?"):
            conn.execute("DELETE FROM collecteurs WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            self.show_collecteurs()
        else:
            conn.close()

    def _form_collecteur(self, cid=None):
        win = tk.Toplevel(self)
        win.title("Collecteur")
        win.geometry("400x380")
        win.grab_set()

        fields = {}
        for key, label in [
            ("code", "Code *"),
            ("nom", "Nom *"),
            ("prenom", "Prenom *"),
            ("tel", "Telephone"),
            ("region", "Region"),
            ("vehicule", "Vehicule"),
            ("notes", "Notes"),
        ]:
            ttk.Label(win, text=label).pack(pady=(5, 0))
            e = ttk.Entry(win, width=40)
            e.pack()
            fields[key] = e

        statut_var = tk.StringVar(value="actif")
        ttk.Label(win, text="Statut").pack(pady=(5, 0))
        ttk.Combobox(
            win,
            textvariable=statut_var,
            values=["actif", "inactif"],
            state="readonly",
            width=38,
        ).pack()

        if cid:
            conn = get_conn()
            r = conn.execute(
                "SELECT * FROM collecteurs WHERE id=?", (cid,)
            ).fetchone()
            conn.close()
            if r:
                fields["code"].insert(0, r["code"] or "")
                fields["nom"].insert(0, r["nom"] or "")
                fields["prenom"].insert(0, r["prenom"] or "")
                fields["tel"].insert(0, r["telephone"] or "")
                fields["region"].insert(0, r["region"] or "")
                fields["vehicule"].insert(0, r["vehicule"] or "")
                fields["notes"].insert(0, r["notes"] or "")
                statut_var.set(r["statut"] or "actif")
        else:
            conn = get_conn()
            row = conn.execute(
                "SELECT code FROM collecteurs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            n = 1
            if row and row["code"]:
                try:
                    n = int(row["code"].replace("COL-", "").replace("col-", "")) + 1
                except Exception:
                    n = 1
            fields["code"].insert(0, "COL-%03d" % n)
            fields["code"].config(state="readonly")

        def save():
            try:
                code = fields["code"].get().strip()
                nom = fields["nom"].get().strip()
                prenom = fields["prenom"].get().strip()
                if not code or not nom or not prenom:
                    messagebox.showerror(
                        "Erreur", "Code, nom et prenom obligatoires"
                    )
                    return
                conn = get_conn()
                if cid:
                    conn.execute(
                        """UPDATE collecteurs SET code=?,nom=?,prenom=?,telephone=?,
                           region=?,vehicule=?,statut=?,notes=? WHERE id=?""",
                        (
                            code,
                            nom,
                            prenom,
                            fields["tel"].get().strip(),
                            fields["region"].get().strip(),
                            fields["vehicule"].get().strip(),
                            statut_var.get(),
                            fields["notes"].get().strip(),
                            cid,
                        ),
                    )
                else:
                    conn.execute(
                        """INSERT INTO collecteurs
                           (code,nom,prenom,telephone,region,vehicule,statut,notes)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            code,
                            nom,
                            prenom,
                            fields["tel"].get().strip(),
                            fields["region"].get().strip(),
                            fields["vehicule"].get().strip(),
                            statut_var.get(),
                            fields["notes"].get().strip(),
                        ),
                    )
                conn.commit()
                conn.close()
                win.destroy()
                self.show_collecteurs()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

        ttk.Button(win, text="Enregistrer", command=save).pack(pady=12)


    def fiche_collecteur(self):
        sel = self.tree_collec.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un collecteur")
            return
        self._afficher_fiche_collecteur(self.tree_collec.item(sel[0])["values"][0])

    def print_fiche_collecteur(self):
        sel = self.tree_collec.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un collecteur")
            return
        self._imprimer_fiche_collecteur(self.tree_collec.item(sel[0])["values"][0])

    def _afficher_fiche_collecteur(self, cid):
        self.clear()
        conn = get_conn()
        col = conn.execute("SELECT * FROM collecteurs WHERE id=?", (cid,)).fetchone()
        if not col:
            conn.close()
            return
        elevs = conn.execute(
            "SELECT * FROM eleveurs WHERE collecteur_id=? ORDER BY nom", (cid,)
        ).fetchall()
        vol = conn.execute("""
            SELECT COALESCE(SUM(c.quantite),0), COUNT(c.id)
            FROM collectes c
            JOIN eleveurs e ON c.eleveur_id=e.id
            WHERE e.collecteur_id=?
        """, (cid,)).fetchone()
        conn.close()
        volume_total = vol[0] if vol else 0
        nb_col = vol[1] if vol else 0

        ttk.Label(
            self.main,
            text="Fiche collecteur : %s %s (%s)" % (col["nom"], col["prenom"], col["code"]),
            font=("Arial", 14, "bold"),
        ).pack(pady=6)
        info = ttk.LabelFrame(self.main, text="Informations", padding=8)
        info.pack(fill="x", padx=10, pady=5)
        ttk.Label(
            info,
            text="Tel: %s | Region: %s | Vehicule: %s | Statut: %s"
            % (col["telephone"] or "-", col["region"] or "-", col["vehicule"] or "-", col["statut"]),
        ).pack(anchor="w")
        stats = ttk.LabelFrame(self.main, text="Resume", padding=8)
        stats.pack(fill="x", padx=10, pady=5)
        ttk.Label(
            stats,
            text="Eleveurs: %d | Collectes: %d | Volume: %.0f L" % (len(elevs), nb_col, volume_total),
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")

        ef = ttk.LabelFrame(self.main, text="Eleveurs rattaches", padding=5)
        ef.pack(fill="both", expand=True, padx=10, pady=5)
        cols = ("code", "nom", "tel", "region", "statut")
        tree = ttk.Treeview(ef, columns=cols, show="headings", height=10)
        for c, t in zip(cols, ["Code", "Nom", "Tel", "Region", "Statut"]):
            tree.heading(c, text=t)
            tree.column(c, width=120)
        tree.pack(fill="both", expand=True)
        for e in elevs:
            tree.insert("", "end", values=(
                e["code_unique"], "%s %s" % (e["nom"], e["prenom"]),
                e["telephone"] or "", e["region"] or "", e["statut"],
            ))

        bf = ttk.Frame(self.main)
        bf.pack(pady=8)
        ttk.Button(bf, text="Imprimer la fiche", command=lambda: self._imprimer_fiche_collecteur(cid)).pack(side="left", padx=5)
        ttk.Button(bf, text="Retour liste", command=self.show_collecteurs).pack(side="left", padx=5)

    def _imprimer_fiche_collecteur(self, cid):
        conn = get_conn()
        col = conn.execute("SELECT * FROM collecteurs WHERE id=?", (cid,)).fetchone()
        if not col:
            conn.close()
            return
        elevs = conn.execute(
            "SELECT * FROM eleveurs WHERE collecteur_id=? ORDER BY nom", (cid,)
        ).fetchall()
        vol = conn.execute("""
            SELECT COALESCE(SUM(c.quantite),0), COUNT(c.id)
            FROM collectes c JOIN eleveurs e ON c.eleveur_id=e.id
            WHERE e.collecteur_id=?
        """, (cid,)).fetchone()
        conn.close()
        path = generer_fiche_collecteur(col, elevs, vol[0] if vol else 0, vol[1] if vol else 0)
        imprimer_fichier(path)
