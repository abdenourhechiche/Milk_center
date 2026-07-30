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

        cols = ("id", "code", "nom", "prenom", "tel", "region", "collecteur", "laiterie", "statut")
        self.tree_elev = ttk.Treeview(
            self.main, columns=cols, show="headings", height=17
        )
        for c, t in zip(
            cols,
            ["ID", "Code", "Nom", "Prenom", "Tel", "Region", "Collecteur", "Laiterie", "Statut"],
        ):
            self.tree_elev.heading(c, text=t)
            self.tree_elev.column(c, width=85)
        self.tree_elev.pack(fill="both", expand=True, pady=4)

        conn = get_conn()
        for r in conn.execute("""
            SELECT e.*,
                   COALESCE(c.nom||' '||c.prenom, '') as collecteur_nom,
                   COALESCE(l.nom, '') as laiterie_nom
            FROM eleveurs e
            LEFT JOIN collecteurs c ON e.collecteur_id = c.id
            LEFT JOIN clients l ON e.laiterie_id = l.id
            ORDER BY e.nom
        """):
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
                    r["collecteur_nom"] or "",
                    r["laiterie_nom"] or "",
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
        win.geometry("420x520")
        win.grab_set()

        conn = get_conn()
        collecteurs = conn.execute(
            "SELECT id, code, nom, prenom FROM collecteurs WHERE statut='actif' ORDER BY nom"
        ).fetchall()
        laiteries = conn.execute(
            "SELECT id, code, nom FROM clients WHERE type_client='laiterie' OR type_client LIKE '%lait%' ORDER BY nom"
        ).fetchall()
        if not laiteries:
            laiteries = conn.execute(
                "SELECT id, code, nom FROM clients ORDER BY nom"
            ).fetchall()
        existing = None
        if eid:
            existing = conn.execute(
                "SELECT * FROM eleveurs WHERE id=?", (eid,)
            ).fetchone()
        conn.close()

        ttk.Label(win, text="Code unique").grid(
            row=0, column=0, sticky="e", padx=5, pady=5
        )
        code_e = ttk.Entry(win, width=30)
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
            e = ttk.Entry(win, width=30)
            e.grid(row=i, column=1, padx=5, pady=5)
            fields[key] = e

        # Collecteur
        ttk.Label(win, text="Collecteur").grid(
            row=6, column=0, sticky="e", padx=5, pady=5
        )
        col_var = tk.StringVar(value="")
        col_opts = ["(Aucun)"]
        col_map = {"": None}
        for c in collecteurs:
            label = "%d - %s %s (%s)" % (c["id"], c["nom"], c["prenom"], c["code"])
            col_opts.append(label)
            col_map[label] = c["id"]
        col_cb = ttk.Combobox(
            win, textvariable=col_var, values=col_opts, state="readonly", width=28
        )
        col_cb.grid(row=6, column=1, padx=5, pady=5)
        col_var.set(col_opts[0])

        # Laiterie
        ttk.Label(win, text="Laiterie").grid(
            row=7, column=0, sticky="e", padx=5, pady=5
        )
        lait_var = tk.StringVar(value="")
        lait_opts = ["(Aucune)"]
        lait_map = {"": None}
        for l in laiteries:
            label = "%d - %s (%s)" % (l["id"], l["nom"], l["code"])
            lait_opts.append(label)
            lait_map[label] = l["id"]
        lait_cb = ttk.Combobox(
            win, textvariable=lait_var, values=lait_opts, state="readonly", width=28
        )
        lait_cb.grid(row=7, column=1, padx=5, pady=5)
        lait_var.set(lait_opts[0])

        statut_var = tk.StringVar(value="actif")
        ttk.Label(win, text="Statut").grid(
            row=8, column=0, sticky="e", padx=5, pady=5
        )
        ttk.Combobox(
            win,
            textvariable=statut_var,
            values=["actif", "inactif", "bloque"],
            state="readonly",
            width=28,
        ).grid(row=8, column=1, padx=5, pady=5)

        if existing:
            code_e.insert(0, existing["code_unique"] or "")
            code_e.config(state="readonly")
            fields["nom"].insert(0, existing["nom"] or "")
            fields["prenom"].insert(0, existing["prenom"] or "")
            fields["tel"].insert(0, existing["telephone"] or "")
            fields["adresse"].insert(0, existing["adresse"] or "")
            fields["region"].insert(0, existing["region"] or "")
            statut_var.set(existing["statut"] or "actif")
            cid = existing["collecteur_id"] if "collecteur_id" in existing.keys() else None
            lid = existing["laiterie_id"] if "laiterie_id" in existing.keys() else None
            if cid:
                for o in col_opts:
                    if o.startswith("%d -" % cid):
                        col_var.set(o)
                        break
            if lid:
                for o in lait_opts:
                    if o.startswith("%d -" % lid):
                        lait_var.set(o)
                        break
        else:
            from src.database import next_eleveur_code
            code_e.insert(0, next_eleveur_code())
            code_e.config(state="readonly")

        def save():
            nom = fields["nom"].get().strip()
            prenom = fields["prenom"].get().strip()
            if not nom or not prenom:
                messagebox.showerror("Erreur", "Nom et prenom obligatoires")
                return
            code = code_e.get().strip()
            col_id = col_map.get(col_var.get())
            lait_id = lait_map.get(lait_var.get())
            conn = get_conn()
            if eid:
                conn.execute(
                    """UPDATE eleveurs SET nom=?,prenom=?,telephone=?,adresse=?,
                       region=?,statut=?,collecteur_id=?,laiterie_id=? WHERE id=?""",
                    (
                        nom,
                        prenom,
                        fields["tel"].get().strip(),
                        fields["adresse"].get().strip(),
                        fields["region"].get().strip(),
                        statut_var.get(),
                        col_id,
                        lait_id,
                        eid,
                    ),
                )
            else:
                from datetime import date
                conn.execute(
                    """INSERT INTO eleveurs
                       (code_unique,nom,prenom,telephone,adresse,region,date_adhesion,
                        statut,collecteur_id,laiterie_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        code,
                        nom,
                        prenom,
                        fields["tel"].get().strip(),
                        fields["adresse"].get().strip(),
                        fields["region"].get().strip(),
                        date.today().isoformat(),
                        statut_var.get(),
                        col_id,
                        lait_id,
                    ),
                )
            conn.commit()
            conn.close()
            win.destroy()
            self.show_eleveurs()

        ttk.Button(win, text="Enregistrer", command=save).grid(
            row=9, column=0, columnspan=2, pady=12
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
        col_nom = "-"
        lait_nom = "-"
        try:
            cid = elev["collecteur_id"]
            if cid:
                cr = conn.execute("SELECT nom,prenom FROM collecteurs WHERE id=?", (cid,)).fetchone()
                if cr:
                    col_nom = "%s %s" % (cr["nom"], cr["prenom"])
        except Exception:
            pass
        try:
            lid = elev["laiterie_id"]
            if lid:
                lr = conn.execute("SELECT nom FROM clients WHERE id=?", (lid,)).fetchone()
                if lr:
                    lait_nom = lr["nom"]
        except Exception:
            pass
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
        ttk.Label(
            info,
            text="Collecteur: %s | Laiterie: %s" % (col_nom, lait_nom),
            font=("Arial", 10, "bold"),
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
