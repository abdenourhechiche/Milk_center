# -*- coding: utf-8 -*-
"""Autres modules UI : collectes, avances, facturation, agrements, expeditions, clients, params, compte, rapports."""
from __future__ import print_function, unicode_literals
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import os, sys, uuid, csv, hashlib

from src.config import MONNAIE, EXPORTS_DIR
from src.database import get_conn, get_param, set_param
from src.utils import imprimer_fichier, generer_facture_a4


class CollectesMixin(object):
    def show_collectes(self):
        self.clear()
        ttk.Label(self.main, text="Gestion des Collectes", font=("Arial", 15, "bold")).pack(pady=6)

        # Filtres collecteur + dates
        filt = ttk.Frame(self.main)
        filt.pack(fill="x", pady=2)
        ttk.Label(filt, text="Collecteur :").pack(side="left", padx=3)
        conn = get_conn()
        cols_list = conn.execute(
            "SELECT id, nom, prenom, code FROM collecteurs WHERE statut='actif' ORDER BY nom"
        ).fetchall()
        conn.close()
        self._filtre_col_var = tk.StringVar(value="Tous")
        opts = ["Tous"] + ["%d - %s %s" % (c["id"], c["nom"], c["prenom"]) for c in cols_list]
        cb = ttk.Combobox(filt, textvariable=self._filtre_col_var, values=opts, state="readonly", width=28)
        cb.pack(side="left", padx=3)
        ttk.Label(filt, text="Du :").pack(side="left", padx=(8, 2))
        self._col_date_debut = ttk.Entry(filt, width=12)
        self._col_date_debut.insert(0, (date.today() - timedelta(days=30)).isoformat())
        self._col_date_debut.pack(side="left")
        ttk.Label(filt, text="Au :").pack(side="left", padx=(8, 2))
        self._col_date_fin = ttk.Entry(filt, width=12)
        self._col_date_fin.insert(0, date.today().isoformat())
        self._col_date_fin.pack(side="left")
        ttk.Button(filt, text="Filtrer", command=self._refresh_collectes_list).pack(side="left", padx=6)

        tb = ttk.Frame(self.main)
        tb.pack(fill="x")
        ttk.Button(tb, text="Nouvelle Collecte", command=self.add_collecte).pack(side="left", padx=3)
        ttk.Button(tb, text="Modifier", command=self.edit_collecte).pack(side="left", padx=3)
        ttk.Button(tb, text="Supprimer", command=self.del_collecte).pack(side="left", padx=3)
        ttk.Button(tb, text="Actualiser", command=self.show_collectes).pack(side="left", padx=3)

        cols = ("id", "bon", "eleveur", "collecteur", "date", "qte", "acidite", "densite", "agent")
        self.tree_col = ttk.Treeview(self.main, columns=cols, show="headings", height=16)
        for c, t in zip(cols, ["ID", "N Bon", "Eleveur", "Collecteur", "Date", "Qte", "Acidite", "Densite", "Agent"]):
            self.tree_col.heading(c, text=t)
            self.tree_col.column(c, width=85)
        self.tree_col.pack(fill="both", expand=True, pady=4)
        self._refresh_collectes_list()

    def _refresh_collectes_list(self):
        if not hasattr(self, "tree_col"):
            return
        for i in self.tree_col.get_children():
            self.tree_col.delete(i)
        f = getattr(self, "_filtre_col_var", None)
        col_filter = None
        if f and f.get() and f.get() != "Tous":
            try:
                col_filter = int(f.get().split(" - ")[0])
            except Exception:
                col_filter = None
        d1 = getattr(self, "_col_date_debut", None)
        d2 = getattr(self, "_col_date_fin", None)
        date_debut = (d1.get().strip() if d1 else "") or ""
        date_fin = (d2.get().strip() if d2 else "") or ""
        conn = get_conn()
        sql = """SELECT c.*, e.nom||' '||e.prenom as elev_nom,
                        COALESCE(col.nom||' '||col.prenom, '-') as collecteur_nom
                 FROM collectes c
                 LEFT JOIN eleveurs e ON c.eleveur_id=e.id
                 LEFT JOIN collecteurs col ON e.collecteur_id=col.id
                 WHERE 1=1"""
        params = []
        if col_filter:
            sql += " AND e.collecteur_id=?"
            params.append(col_filter)
        if date_debut:
            sql += " AND date(c.date_heure) >= date(?)"
            params.append(date_debut)
        if date_fin:
            sql += " AND date(c.date_heure) <= date(?)"
            params.append(date_fin)
        sql += " ORDER BY c.date_heure DESC LIMIT 500"
        for r in conn.execute(sql, params):
            self.tree_col.insert("", "end", values=(
                r["id"], r["numero_bon"], r["elev_nom"] or "?",
                r["collecteur_nom"] or "-",
                (r["date_heure"] or "")[:16], "%.1f" % (r["quantite"] or 0),
                r["acidite"] if r["acidite"] is not None else "-",
                r["densite"] if r["densite"] is not None else "-",
                r["agent"] or "",
            ))
        conn.close()

    def add_collecte(self):
        self._form_collecte()

    def edit_collecte(self):
        sel = self.tree_col.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez")
            return
        self._form_collecte(self.tree_col.item(sel[0])["values"][0])

    def del_collecte(self):
        sel = self.tree_col.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez")
            return
        if messagebox.askyesno("Confirmation", "Supprimer ?"):
            cid = self.tree_col.item(sel[0])["values"][0]
            conn = get_conn()
            conn.execute("DELETE FROM collectes WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            self.show_collectes()

    def _form_collecte(self, cid=None):
        conn = get_conn()
        collecteurs = conn.execute(
            "SELECT id, nom, prenom, code FROM collecteurs WHERE statut='actif' ORDER BY nom"
        ).fetchall()
        regions = [r[0] for r in conn.execute(
            "SELECT DISTINCT region FROM eleveurs WHERE statut='actif' AND region IS NOT NULL AND region!='' ORDER BY region"
        ).fetchall()]
        all_elevs = conn.execute(
            "SELECT id, code_unique, nom, prenom, region, collecteur_id FROM eleveurs WHERE statut='actif' ORDER BY nom"
        ).fetchall()
        existing = conn.execute("SELECT * FROM collectes WHERE id=?", (cid,)).fetchone() if cid else None
        conn.close()
        if not all_elevs:
            messagebox.showwarning("Attention", "Aucun eleveur actif")
            return

        win = tk.Toplevel(self)
        win.title("Collecte")
        win.geometry("440x520")
        win.grab_set()

        # Filtre Collecteur
        ttk.Label(win, text="Collecteur (filtre)").pack(pady=(8, 0))
        col_var = tk.StringVar(value="Tous")
        col_opts = ["Tous"] + ["%d - %s %s" % (c["id"], c["nom"], c["prenom"]) for c in collecteurs]
        col_cb = ttk.Combobox(win, textvariable=col_var, values=col_opts, state="readonly", width=42)
        col_cb.pack()

        ttk.Label(win, text="Region (filtre)").pack(pady=(6, 0))
        region_var = tk.StringVar(value="Toutes")
        region_cb = ttk.Combobox(
            win, textvariable=region_var, values=["Toutes"] + regions, state="readonly", width=42
        )
        region_cb.pack()

        ttk.Label(win, text="Eleveur *").pack(pady=(6, 0))
        elev_var = tk.StringVar()
        elev_cb = ttk.Combobox(win, textvariable=elev_var, state="readonly", width=42)
        elev_cb.pack()

        def refresh_elevs(*a):
            reg = region_var.get()
            colf = col_var.get()
            col_id = None
            if colf and colf != "Tous":
                try:
                    col_id = int(colf.split(" - ")[0])
                except Exception:
                    col_id = None
            filtered = []
            for e in all_elevs:
                if reg != "Toutes" and (e["region"] or "") != reg:
                    continue
                if col_id is not None:
                    eid_col = e["collecteur_id"] if "collecteur_id" in e.keys() else None
                    if eid_col != col_id:
                        continue
                filtered.append(e)
            opts = [
                "%d - %s %s (%s) [%s]"
                % (e["id"], e["nom"], e["prenom"], e["code_unique"], e["region"] or "-")
                for e in filtered
            ]
            elev_cb["values"] = opts
            if opts:
                if elev_var.get() not in opts:
                    elev_var.set(opts[0])
            else:
                elev_var.set("")

        col_cb.bind("<<ComboboxSelected>>", refresh_elevs)
        region_cb.bind("<<ComboboxSelected>>", refresh_elevs)
        refresh_elevs()

        if existing:
            conn = get_conn()
            elev = conn.execute(
                "SELECT * FROM eleveurs WHERE id=?", (existing["eleveur_id"],)
            ).fetchone()
            conn.close()
            if elev:
                try:
                    cid_e = elev["collecteur_id"]
                    if cid_e:
                        for o in col_opts:
                            if o.startswith("%d -" % cid_e):
                                col_var.set(o)
                                break
                except Exception:
                    pass
                if elev["region"]:
                    region_var.set(elev["region"])
                refresh_elevs()
                for o in elev_cb["values"]:
                    if o.startswith("%d -" % elev["id"]):
                        elev_var.set(o)
                        break

        fields = {}
        for key, label in [
            ("qte", "Quantite (litres) *"),
            ("acidite", "Acidite"),
            ("densite", "Densite"),
            ("agent", "Agent (optionnel)"),
            ("vehicule", "Vehicule"),
        ]:
            ttk.Label(win, text=label).pack(pady=(5, 0))
            e = ttk.Entry(win, width=44)
            e.pack()
            fields[key] = e
        if existing:
            fields["qte"].insert(0, str(existing["quantite"] or ""))
            fields["acidite"].insert(0, str(existing["acidite"] or ""))
            fields["densite"].insert(0, str(existing["densite"] or ""))
            fields["agent"].insert(0, existing["agent"] or "")
            fields["vehicule"].insert(0, existing["vehicule"] or "")

        def save():
            try:
                if not elev_var.get():
                    raise ValueError("Selectionnez un eleveur")
                qte = float(fields["qte"].get().replace(",", "."))
                if qte <= 0:
                    raise ValueError("Quantite > 0")
                elev_id = int(elev_var.get().split(" - ")[0])
                acidite = float(fields["acidite"].get().replace(",", ".") or 0) or None
                densite = float(fields["densite"].get().replace(",", ".") or 0) or None
                agent = fields["agent"].get().strip() or None
                vehicule = fields["vehicule"].get().strip() or None
                conn = get_conn()
                if cid:
                    conn.execute(
                        "UPDATE collectes SET eleveur_id=?,quantite=?,acidite=?,densite=?,agent=?,vehicule=? WHERE id=?",
                        (elev_id, qte, acidite, densite, agent, vehicule, cid),
                    )
                else:
                    numero = "BC-%s-%s" % (
                        datetime.now().strftime("%Y%m%d"),
                        uuid.uuid4().hex[:6].upper(),
                    )
                    conn.execute(
                        "INSERT INTO collectes (numero_bon,eleveur_id,date_heure,quantite,acidite,densite,agent,vehicule) VALUES (?,?,?,?,?,?,?,?)",
                        (
                            numero,
                            elev_id,
                            datetime.now().isoformat(),
                            qte,
                            acidite,
                            densite,
                            agent,
                            vehicule,
                        ),
                    )
                conn.commit()
                conn.close()
                win.destroy()
                self.show_collectes()
                messagebox.showinfo("Succes", "Collecte enregistree")
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

        ttk.Button(win, text="Enregistrer", command=save).pack(pady=10)


class AvancesMixin(object):
    def show_avances(self):
        self.clear()
        ttk.Label(self.main, text="Avances aux Eleveurs", font=("Arial", 15, "bold")).pack(pady=6)
        tb = ttk.Frame(self.main)
        tb.pack(fill="x")
        ttk.Button(tb, text="Nouvelle Avance", command=lambda: self._form_avance()).pack(side="left", padx=3)
        ttk.Button(tb, text="Modifier", command=self.edit_avance).pack(side="left", padx=3)
        ttk.Button(tb, text="Supprimer", command=self.del_avance).pack(side="left", padx=3)
        ttk.Button(tb, text="Actualiser", command=self.show_avances).pack(side="left", padx=3)
        cols = ("id", "eleveur", "date", "montant", "motif", "statut")
        self.tree_av = ttk.Treeview(self.main, columns=cols, show="headings", height=16)
        for c, t in zip(cols, ["ID", "Eleveur", "Date", "Montant", "Motif", "Statut"]):
            self.tree_av.heading(c, text=t)
            self.tree_av.column(c, width=110)
        self.tree_av.pack(fill="both", expand=True, pady=4)
        conn = get_conn()
        for r in conn.execute("""SELECT a.*, e.nom||' '||e.prenom as elev FROM avances a
            LEFT JOIN eleveurs e ON a.eleveur_id=e.id ORDER BY a.date_avance DESC"""):
            self.tree_av.insert("", "end", values=(
                r["id"], r["elev"] or "?", (r["date_avance"] or "")[:10],
                "%.0f" % (r["montant"] or 0), r["motif"] or "", r["statut"]))
        conn.close()

    def edit_avance(self):
        sel = self.tree_av.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez une avance")
            return
        self._form_avance(self.tree_av.item(sel[0])["values"][0])

    def _form_avance(self, aid=None):
        conn = get_conn()
        elevs = conn.execute(
            "SELECT id,nom,prenom FROM eleveurs WHERE statut='actif' ORDER BY nom"
        ).fetchall()
        existing = conn.execute(
            "SELECT * FROM avances WHERE id=?", (aid,)
        ).fetchone() if aid else None
        conn.close()
        if not elevs:
            messagebox.showwarning("Attention", "Aucun eleveur")
            return
        win = tk.Toplevel(self)
        win.title("Avance")
        win.geometry("400x340")
        win.grab_set()
        ttk.Label(win, text="Eleveur *").pack(pady=(10, 0))
        elev_var = tk.StringVar()
        opts = ["%d - %s %s" % (e["id"], e["nom"], e["prenom"]) for e in elevs]
        ttk.Combobox(win, textvariable=elev_var, values=opts, state="readonly", width=40).pack()
        elev_var.set(opts[0])
        ttk.Label(win, text="Montant (%s) *" % MONNAIE).pack(pady=(8, 0))
        montant_e = ttk.Entry(win, width=40)
        montant_e.pack()
        ttk.Label(win, text="Date (AAAA-MM-JJ)").pack(pady=(8, 0))
        date_e = ttk.Entry(win, width=40)
        date_e.insert(0, date.today().isoformat())
        date_e.pack()
        ttk.Label(win, text="Motif").pack(pady=(8, 0))
        motif_e = ttk.Entry(win, width=40)
        motif_e.pack()
        statut_var = tk.StringVar(value="non_deduite")
        ttk.Label(win, text="Statut").pack(pady=(8, 0))
        ttk.Combobox(
            win, textvariable=statut_var,
            values=["non_deduite", "deduite"], state="readonly", width=40
        ).pack()
        if existing:
            for o in opts:
                if o.startswith("%d -" % existing["eleveur_id"]):
                    elev_var.set(o)
                    break
            montant_e.insert(0, str(existing["montant"] or ""))
            date_e.delete(0, "end")
            date_e.insert(0, (existing["date_avance"] or "")[:10])
            motif_e.insert(0, existing["motif"] or "")
            statut_var.set(existing["statut"] or "non_deduite")

        def save():
            try:
                elev_id = int(elev_var.get().split(" - ")[0])
                montant = float(montant_e.get().replace(",", "."))
                if montant <= 0:
                    raise ValueError("Montant > 0")
                conn = get_conn()
                if aid:
                    conn.execute(
                        """UPDATE avances SET eleveur_id=?,date_avance=?,montant=?,
                           motif=?,statut=? WHERE id=?""",
                        (elev_id, date_e.get().strip(), montant,
                         motif_e.get().strip(), statut_var.get(), aid))
                else:
                    conn.execute(
                        """INSERT INTO avances
                           (eleveur_id,date_avance,montant,motif,statut)
                           VALUES (?,?,?,?,?)""",
                        (elev_id, date_e.get().strip(), montant,
                         motif_e.get().strip(), statut_var.get()))
                conn.commit()
                conn.close()
                win.destroy()
                self.show_avances()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

        ttk.Button(win, text="Enregistrer", command=save).pack(pady=12)

    def del_avance(self):
        sel = self.tree_av.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez")
            return
        if messagebox.askyesno("Confirmation", "Supprimer ?"):
            aid = self.tree_av.item(sel[0])["values"][0]
            conn = get_conn()
            conn.execute("DELETE FROM avances WHERE id=?", (aid,))
            conn.commit()
            conn.close()
            self.show_avances()


class FacturationMixin(object):
    def show_facturation(self):
        self.clear()
        ttk.Label(self.main, text="Facturation + Impression", font=("Arial", 15, "bold")).pack(pady=6)
        filt = ttk.Frame(self.main); filt.pack(fill="x", pady=2)
        ttk.Label(filt, text="Date facture Du :").pack(side="left", padx=3)
        self._fac_date_debut = ttk.Entry(filt, width=12)
        self._fac_date_debut.insert(0, (date.today() - timedelta(days=90)).isoformat())
        self._fac_date_debut.pack(side="left")
        ttk.Label(filt, text="Au :").pack(side="left", padx=(8, 2))
        self._fac_date_fin = ttk.Entry(filt, width=12)
        self._fac_date_fin.insert(0, date.today().isoformat())
        self._fac_date_fin.pack(side="left")
        ttk.Button(filt, text="Filtrer", command=self._refresh_factures_list).pack(side="left", padx=6)
        tb = ttk.Frame(self.main); tb.pack(fill="x")
        ttk.Button(tb, text="Generer Facture", command=lambda: self.form_facture()).pack(side="left", padx=3)
        ttk.Button(tb, text="Modifier", command=self.edit_facture).pack(side="left", padx=3)
        ttk.Button(tb, text="Supprimer", command=self.del_facture).pack(side="left", padx=3)
        ttk.Button(tb, text="Imprimer", command=self.imprimer_facture).pack(side="left", padx=3)
        ttk.Button(tb, text="Ouvrir fichier", command=self.ouvrir_facture).pack(side="left", padx=3)
        ttk.Button(tb, text="Actualiser", command=self.show_facturation).pack(side="left", padx=3)
        cols = ("id", "num", "elev", "debut", "fin", "credit", "debit", "avances", "solde", "reglement")
        self.tree_f = ttk.Treeview(self.main, columns=cols, show="headings", height=15)
        for c, t in zip(cols, ["ID", "N", "Eleveur", "Du", "Au", "Credit", "Debit", "Avances", "Solde", "Reglement"]):
            self.tree_f.heading(c, text=t); self.tree_f.column(c, width=85)
        self.tree_f.pack(fill="both", expand=True, pady=4)
        self._refresh_factures_list()

    def _refresh_factures_list(self):
        if not hasattr(self, "tree_f"):
            return
        for i in self.tree_f.get_children():
            self.tree_f.delete(i)
        d1 = getattr(self, "_fac_date_debut", None)
        d2 = getattr(self, "_fac_date_fin", None)
        date_debut = (d1.get().strip() if d1 else "") or ""
        date_fin = (d2.get().strip() if d2 else "") or ""
        conn = get_conn()
        sql = """SELECT f.*, e.nom||' '||e.prenom as elev FROM factures f
            LEFT JOIN eleveurs e ON f.eleveur_id=e.id WHERE 1=1"""
        params = []
        if date_debut:
            sql += " AND date(f.date_facture) >= date(?)"
            params.append(date_debut)
        if date_fin:
            sql += " AND date(f.date_facture) <= date(?)"
            params.append(date_fin)
        sql += " ORDER BY f.date_facture DESC"
        for r in conn.execute(sql, params):
            self.tree_f.insert("", "end", values=(
                r["id"], r["numero"], r["elev"] or "?",
                (r["periode_debut"] or "")[:10], (r["periode_fin"] or "")[:10],
                "%.0f" % (r["credit_lait"] or 0), "%.0f" % (r["debit_aliments"] or 0),
                "%.0f" % (r["debit_avances"] or 0), "%.0f" % (r["solde"] or 0),
                r["mode_reglement"] or "-"))
        conn.close()

    def imprimer_facture(self):
        sel = self.tree_f.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez une facture"); return
        numero = self.tree_f.item(sel[0])["values"][1]
        path = os.path.join(EXPORTS_DIR, "facture_%s.txt" % numero)
        if not os.path.exists(path):
            messagebox.showwarning("Attention", "Fichier absent. Regenerer via Modifier puis enregistrer.")
            return
        imprimer_fichier(path)

    def ouvrir_facture(self):
        sel = self.tree_f.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez"); return
        numero = self.tree_f.item(sel[0])["values"][1]
        path = os.path.join(EXPORTS_DIR, "facture_%s.txt" % numero)
        if not os.path.exists(path):
            messagebox.showwarning("Attention", "Fichier introuvable"); return
        try:
            if sys.platform == "win32": os.startfile(path)
            else: import subprocess; subprocess.Popen(["xdg-open", path])
        except Exception as ex: messagebox.showerror("Erreur", str(ex))

    def edit_facture(self):
        sel = self.tree_f.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez une facture"); return
        self.form_facture(self.tree_f.item(sel[0])["values"][0])

    def form_facture(self, fid=None):
        conn = get_conn()
        elevs = conn.execute("SELECT id,nom,prenom,code_unique,telephone FROM eleveurs WHERE statut='actif'").fetchall()
        existing = conn.execute("SELECT * FROM factures WHERE id=?", (fid,)).fetchone() if fid else None
        conn.close()
        if not elevs: messagebox.showwarning("Attention", "Aucun eleveur"); return
        win = tk.Toplevel(self); win.title("Facture"); win.geometry("420x400"); win.grab_set()
        ttk.Label(win, text="Eleveur").pack(pady=(8, 0))
        elev_var = tk.StringVar()
        elev_opts = ["%d - %s %s" % (e["id"], e["nom"], e["prenom"]) for e in elevs]
        ttk.Combobox(win, textvariable=elev_var, values=elev_opts, state="readonly", width=42).pack(); elev_var.set(elev_opts[0])
        ttk.Label(win, text="Date debut (AAAA-MM-JJ) *").pack(pady=(6, 0)); debut_e = ttk.Entry(win, width=42)
        debut_e.insert(0, (date.today() - timedelta(days=30)).isoformat()); debut_e.pack()
        ttk.Label(win, text="Date fin (AAAA-MM-JJ) *").pack(pady=(6, 0)); fin_e = ttk.Entry(win, width=42)
        fin_e.insert(0, date.today().isoformat()); fin_e.pack()
        ttk.Label(win, text="Prix du litre (%s)" % MONNAIE).pack(pady=(6, 0)); prix_e = ttk.Entry(win, width=42); prix_e.insert(0, "50"); prix_e.pack()
        reglement_var = tk.StringVar(value="Especes")
        ttk.Label(win, text="Mode reglement").pack(pady=(6, 0))
        ttk.Combobox(win, textvariable=reglement_var, values=["Especes", "Cheque", "Virement", "A terme", "Compensation"], state="readonly", width=42).pack()
        deduire = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text="Deduire les avances non deduites", variable=deduire).pack(pady=6)
        imprimer_apres = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text="Imprimer apres generation", variable=imprimer_apres).pack(pady=2)
        if existing:
            for o in elev_opts:
                if o.startswith("%d -" % existing["eleveur_id"]): elev_var.set(o); break
            if existing["periode_debut"]:
                debut_e.delete(0, "end"); debut_e.insert(0, existing["periode_debut"][:10])
            if existing["periode_fin"]:
                fin_e.delete(0, "end"); fin_e.insert(0, existing["periode_fin"][:10])
            reglement_var.set(existing["mode_reglement"] or "Especes")
            deduire.set(False)  # ne pas re-deduire par defaut en modification
        def save():
            try:
                elev_id = int(elev_var.get().split(" - ")[0])
                prix = float(prix_e.get().replace(",", "."))
                debut = debut_e.get().strip(); fin = fin_e.get().strip()
                debut_dt = debut + "T00:00:00"; fin_dt = fin + "T23:59:59"
                conn = get_conn()
                elev = conn.execute("SELECT * FROM eleveurs WHERE id=?", (elev_id,)).fetchone()
                litres = conn.execute("SELECT COALESCE(SUM(quantite),0) FROM collectes WHERE eleveur_id=? AND date_heure>=? AND date_heure<=?",
                                      (elev_id, debut_dt, fin_dt)).fetchone()[0]
                credit = litres * prix
                debit = conn.execute("SELECT COALESCE(SUM(montant),0) FROM ventes WHERE eleveur_id=? AND date_vente>=? AND date_vente<=? AND mode='credit'",
                                     (elev_id, debut_dt, fin_dt)).fetchone()[0]
                avances_m = 0
                if deduire.get():
                    avances_m = conn.execute("SELECT COALESCE(SUM(montant),0) FROM avances WHERE eleveur_id=? AND statut='non_deduite'", (elev_id,)).fetchone()[0]
                elif existing:
                    avances_m = existing["debit_avances"] or 0
                solde = credit - debit - avances_m
                if fid and existing:
                    conn.execute("""UPDATE factures SET eleveur_id=?,periode_debut=?,periode_fin=?,
                        credit_lait=?,debit_aliments=?,debit_avances=?,solde=?,mode_reglement=? WHERE id=?""",
                        (elev_id, debut, fin, credit, debit, avances_m, solde, reglement_var.get(), fid))
                    numero = existing["numero"]
                else:
                    numero = "FAC-%s-%s" % (datetime.now().strftime("%Y%m%d"), uuid.uuid4().hex[:5].upper())
                    conn.execute("""INSERT INTO factures (numero,eleveur_id,date_facture,periode_debut,periode_fin,
                        credit_lait,debit_aliments,debit_avances,solde,mode_reglement) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (numero, elev_id, datetime.now().isoformat(), debut, fin, credit, debit, avances_m, solde, reglement_var.get()))
                if deduire.get() and avances_m > 0:
                    conn.execute("UPDATE avances SET statut='deduite' WHERE eleveur_id=? AND statut='non_deduite'", (elev_id,))
                conn.commit(); conn.close()
                path = generer_facture_a4(numero, elev, litres, prix, credit, debit, avances_m, solde,
                                          "", reglement_var.get(), debut, fin)
                win.destroy(); self.show_facturation()
                messagebox.showinfo("Succes", "Facture %s enregistree" % numero)
                if imprimer_apres.get(): imprimer_fichier(path)
            except Exception as ex: messagebox.showerror("Erreur", str(ex))
        ttk.Button(win, text="Enregistrer + Generer A4", command=save).pack(pady=10)

    def del_facture(self):
        sel = self.tree_f.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez"); return
        if messagebox.askyesno("Confirmation", "Supprimer ?"):
            fid = self.tree_f.item(sel[0])["values"][0]
            conn = get_conn(); conn.execute("DELETE FROM factures WHERE id=?", (fid,)); conn.commit(); conn.close()
            self.show_facturation()


class DiversMixin(object):
    """Agrements, expeditions, clients, parametres, compte, rapports, dashboard."""

    def show_dashboard(self):
        self.clear()
        nom = get_param("nom_centre", "Centre de Collecte de Lait")
        ttk.Label(self.main, text=nom, font=("Arial", 16, "bold")).pack(pady=8)
        conn = get_conn()
        nb_elev = conn.execute("SELECT COUNT(*) FROM eleveurs WHERE statut='actif'").fetchone()[0]
        nb_col = conn.execute("SELECT COUNT(*) FROM collectes").fetchone()[0]
        total_l = conn.execute("SELECT COALESCE(SUM(quantite),0) FROM collectes").fetchone()[0]
        nb_exp = conn.execute("SELECT COUNT(*) FROM expeditions WHERE statut='en_transit'").fetchone()[0]
        total_av = conn.execute("SELECT COALESCE(SUM(montant),0) FROM avances WHERE statut='non_deduite'").fetchone()[0]
        limite = (date.today() + timedelta(days=30)).isoformat()
        alertes = conn.execute("SELECT * FROM agrements WHERE date_expiration<=? ORDER BY date_expiration", (limite,)).fetchall()
        conn.close()
        frame = ttk.Frame(self.main); frame.pack(pady=6)
        for title, val in [("Eleveurs", str(nb_elev)), ("Collectes", str(nb_col)), ("Litres", "%.0f L" % total_l),
                           ("Exped. en cours", str(nb_exp)), ("Avances", "%.0f %s" % (total_av, MONNAIE)), ("Alertes", str(len(alertes)))]:
            f = ttk.LabelFrame(frame, text=title, padding=6); f.pack(side="left", padx=4)
            ttk.Label(f, text=val, font=("Arial", 13, "bold")).pack()
        if alertes:
            af = ttk.LabelFrame(self.main, text="ALERTES AGREMENTS", padding=5); af.pack(fill="x", padx=8, pady=10)
            cols = ("ref", "type", "cible", "exp", "jours")
            tree = ttk.Treeview(af, columns=cols, show="headings", height=min(5, len(alertes)))
            for c, t in zip(cols, ["Reference", "Type", "Cible", "Expiration", "Jours"]):
                tree.heading(c, text=t); tree.column(c, width=110)
            tree.pack(fill="x")
            for a in alertes:
                try:
                    exp = date(*[int(x) for x in a["date_expiration"].split("-")])
                    jours = (exp - date.today()).days
                except Exception: jours = "?"
                jtxt = "EXPIRE" if (isinstance(jours, int) and jours < 0) else str(jours)
                tree.insert("", "end", values=(a["reference"], a["type_agrement"], a["cible"] or "", a["date_expiration"], jtxt))
        else:
            tk.Label(self.main, text="Aucune alerte d'agrement", bg="#27ae60", fg="white",
                     font=("Arial", 10, "bold"), pady=4).pack(fill="x", padx=8, pady=10)

        # Volumes par collecteur
        cf = ttk.LabelFrame(self.main, text="Volumes par collecteur", padding=5)
        cf.pack(fill="x", padx=8, pady=8)
        cols_c = ("collecteur", "nb_elev", "nb_col", "litres")
        tree_c = ttk.Treeview(cf, columns=cols_c, show="headings", height=5)
        for c, t in zip(cols_c, ["Collecteur", "Eleveurs", "Collectes", "Litres"]):
            tree_c.heading(c, text=t)
            tree_c.column(c, width=140)
        tree_c.pack(fill="x")
        conn = get_conn()
        rows = conn.execute("""
            SELECT COALESCE(col.nom||' '||col.prenom, '(Sans collecteur)') as cnom,
                   COUNT(DISTINCT e.id) as nb_elev,
                   COUNT(c.id) as nb_col,
                   COALESCE(SUM(c.quantite), 0) as litres
            FROM eleveurs e
            LEFT JOIN collecteurs col ON e.collecteur_id = col.id
            LEFT JOIN collectes c ON c.eleveur_id = e.id
            GROUP BY e.collecteur_id
            ORDER BY litres DESC
        """).fetchall()
        conn.close()
        for r in rows:
            tree_c.insert("", "end", values=(
                r["cnom"], r["nb_elev"], r["nb_col"], "%.0f L" % (r["litres"] or 0)
            ))

    def show_agrements(self):
        self.clear()
        ttk.Label(self.main, text="Agrements Sanitaires", font=("Arial", 15, "bold")).pack(pady=6)
        tb = ttk.Frame(self.main); tb.pack(fill="x")
        ttk.Button(tb, text="Ajouter", command=lambda: self._form_agrement()).pack(side="left", padx=3)
        ttk.Button(tb, text="Modifier", command=self.edit_agrement).pack(side="left", padx=3)
        ttk.Button(tb, text="Supprimer", command=self.del_agrement).pack(side="left", padx=3)
        ttk.Button(tb, text="Actualiser", command=self.show_agrements).pack(side="left", padx=3)
        cols = ("id", "ref", "type", "cible", "deliv", "exp", "jours", "statut")
        self.tree_a = ttk.Treeview(self.main, columns=cols, show="headings", height=15)
        for c, t in zip(cols, ["ID", "Ref", "Type", "Cible", "Delivrance", "Expiration", "Jours", "Statut"]):
            self.tree_a.heading(c, text=t); self.tree_a.column(c, width=90)
        self.tree_a.pack(fill="both", expand=True, pady=4)
        conn = get_conn()
        for r in conn.execute("SELECT * FROM agrements ORDER BY date_expiration"):
            try:
                exp = date(*[int(x) for x in r["date_expiration"].split("-")]); jours = (exp - date.today()).days
            except Exception: jours = "?"
            st = "EXPIRE" if (isinstance(jours, int) and jours < 0) else r["statut"]
            self.tree_a.insert("", "end", values=(
                r["id"], r["reference"], r["type_agrement"], r["cible"] or "",
                r["date_delivrance"] or "", r["date_expiration"], jours, st))
        conn.close()

    def edit_agrement(self):
        sel = self.tree_a.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un agrement")
            return
        self._form_agrement(self.tree_a.item(sel[0])["values"][0])

    def _form_agrement(self, aid=None):
        win = tk.Toplevel(self)
        win.title("Agrement")
        win.geometry("380x360")
        win.grab_set()
        ttk.Label(win, text="Type").pack(pady=(6, 0))
        type_var = tk.StringVar(value="eleveur")
        ttk.Combobox(win, textvariable=type_var, values=["eleveur", "vehicule", "centre"], state="readonly", width=36).pack()
        ttk.Label(win, text="Reference *").pack(pady=(5, 0))
        ref_e = ttk.Entry(win, width=38); ref_e.pack()
        ttk.Label(win, text="Cible").pack(pady=(5, 0))
        cible_e = ttk.Entry(win, width=38); cible_e.pack()
        ttk.Label(win, text="Date delivrance (AAAA-MM-JJ)").pack(pady=(5, 0))
        deliv_e = ttk.Entry(win, width=38)
        deliv_e.insert(0, date.today().isoformat()); deliv_e.pack()
        ttk.Label(win, text="Date expiration (AAAA-MM-JJ)").pack(pady=(5, 0))
        exp_e = ttk.Entry(win, width=38)
        exp_e.insert(0, (date.today() + timedelta(days=365)).isoformat()); exp_e.pack()
        statut_var = tk.StringVar(value="valide")
        ttk.Label(win, text="Statut").pack(pady=(5, 0))
        ttk.Combobox(win, textvariable=statut_var, values=["valide", "expire", "suspendu"], state="readonly", width=36).pack()
        if aid:
            conn = get_conn()
            r = conn.execute("SELECT * FROM agrements WHERE id=?", (aid,)).fetchone()
            conn.close()
            if r:
                type_var.set(r["type_agrement"] or "eleveur")
                ref_e.insert(0, r["reference"] or "")
                cible_e.insert(0, r["cible"] or "")
                deliv_e.delete(0, "end"); deliv_e.insert(0, r["date_delivrance"] or "")
                exp_e.delete(0, "end"); exp_e.insert(0, r["date_expiration"] or "")
                statut_var.set(r["statut"] or "valide")
        def save():
            try:
                ref = ref_e.get().strip()
                if not ref:
                    raise ValueError("Reference obligatoire")
                conn = get_conn()
                if aid:
                    conn.execute(
                        """UPDATE agrements SET reference=?,type_agrement=?,cible=?,
                           date_delivrance=?,date_expiration=?,statut=? WHERE id=?""",
                        (ref, type_var.get(), cible_e.get().strip(),
                         deliv_e.get().strip(), exp_e.get().strip(), statut_var.get(), aid))
                else:
                    conn.execute(
                        """INSERT INTO agrements
                           (reference,type_agrement,cible,date_delivrance,date_expiration,statut)
                           VALUES (?,?,?,?,?,?)""",
                        (ref, type_var.get(), cible_e.get().strip(),
                         deliv_e.get().strip(), exp_e.get().strip(), statut_var.get()))
                conn.commit(); conn.close()
                win.destroy()
                self.show_agrements()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))
        ttk.Button(win, text="Enregistrer", command=save).pack(pady=12)

    def del_agrement(self):
        sel = self.tree_a.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez")
            return
        if messagebox.askyesno("Confirmation", "Supprimer ?"):
            aid = self.tree_a.item(sel[0])["values"][0]
            conn = get_conn()
            conn.execute("DELETE FROM agrements WHERE id=?", (aid,))
            conn.commit(); conn.close()
            self.show_agrements()

    def show_expeditions(self):
        self.clear()
        ttk.Label(self.main, text="Expeditions vers Laiteries", font=("Arial", 15, "bold")).pack(pady=6)
        filt = ttk.Frame(self.main); filt.pack(fill="x", pady=2)
        ttk.Label(filt, text="Du :").pack(side="left", padx=3)
        self._exp_date_debut = ttk.Entry(filt, width=12)
        self._exp_date_debut.insert(0, (date.today() - timedelta(days=30)).isoformat())
        self._exp_date_debut.pack(side="left")
        ttk.Label(filt, text="Au :").pack(side="left", padx=(8, 2))
        self._exp_date_fin = ttk.Entry(filt, width=12)
        self._exp_date_fin.insert(0, date.today().isoformat())
        self._exp_date_fin.pack(side="left")
        ttk.Button(filt, text="Filtrer", command=self._refresh_expeditions_list).pack(side="left", padx=6)
        tb = ttk.Frame(self.main); tb.pack(fill="x")
        ttk.Button(tb, text="Nouveau", command=self.add_expedition).pack(side="left", padx=3)
        ttk.Button(tb, text="Supprimer", command=self.del_expedition).pack(side="left", padx=3)
        ttk.Button(tb, text="Marquer Recu", command=self.marquer_recu).pack(side="left", padx=3)
        ttk.Button(tb, text="Actualiser", command=self.show_expeditions).pack(side="left", padx=3)
        cols = ("id", "numero", "date", "destination", "qte", "vehicule", "agent", "statut")
        self.tree_exp = ttk.Treeview(self.main, columns=cols, show="headings", height=15)
        for c, t in zip(cols, ["ID", "N", "Date", "Destination", "Qte", "Vehicule", "Agent", "Statut"]):
            self.tree_exp.heading(c, text=t); self.tree_exp.column(c, width=95)
        self.tree_exp.pack(fill="both", expand=True, pady=4)
        self._refresh_expeditions_list()

    def _refresh_expeditions_list(self):
        if not hasattr(self, "tree_exp"):
            return
        for i in self.tree_exp.get_children():
            self.tree_exp.delete(i)
        d1 = getattr(self, "_exp_date_debut", None)
        d2 = getattr(self, "_exp_date_fin", None)
        date_debut = (d1.get().strip() if d1 else "") or ""
        date_fin = (d2.get().strip() if d2 else "") or ""
        conn = get_conn()
        sql = "SELECT * FROM expeditions WHERE 1=1"
        params = []
        if date_debut:
            sql += " AND date(date_expedition) >= date(?)"
            params.append(date_debut)
        if date_fin:
            sql += " AND date(date_expedition) <= date(?)"
            params.append(date_fin)
        sql += " ORDER BY date_expedition DESC"
        for r in conn.execute(sql, params):
            self.tree_exp.insert("", "end", values=(
                r["id"], r["numero_bordereau"], (r["date_expedition"] or "")[:16],
                r["destination"] or "", "%.0f" % (r["quantite_totale"] or 0),
                r["vehicule"] or "", r["agent"] or "", r["statut"] or ""))
        conn.close()

    def add_expedition(self):
        conn = get_conn()
        clients = conn.execute("SELECT nom FROM clients ORDER BY nom").fetchall(); conn.close()
        win = tk.Toplevel(self); win.title("Expedition"); win.geometry("400x380"); win.grab_set()
        ttk.Label(win, text="Destination").pack(pady=(8, 0)); dest_var = tk.StringVar()
        if clients:
            opts = [c["nom"] for c in clients]
            ttk.Combobox(win, textvariable=dest_var, values=opts, width=40).pack(); dest_var.set(opts[0])
        else:
            dest_e = ttk.Entry(win, width=40); dest_e.pack(); dest_var = dest_e
        fields = {}
        for key, label in [("quantite", "Quantite (L) *"), ("temperature", "Temperature"),
                           ("vehicule", "Vehicule *"), ("agent", "Agent *"), ("observations", "Observations")]:
            ttk.Label(win, text=label).pack(pady=(5, 0)); e = ttk.Entry(win, width=40); e.pack(); fields[key] = e
        def save():
            try:
                dest = dest_var.get().strip() if hasattr(dest_var, "get") else dest_var.get().strip()
                qte = float(fields["quantite"].get().replace(",", "."))
                vehicule = fields["vehicule"].get().strip(); agent = fields["agent"].get().strip()
                if not dest or not vehicule or not agent or qte <= 0: raise ValueError("Champs obligatoires manquants")
                temp = float(fields["temperature"].get().replace(",", ".") or 0) or None
                obs = fields["observations"].get().strip() or None
                numero = "EXP-%s-%s" % (datetime.now().strftime("%Y%m%d"), uuid.uuid4().hex[:5].upper())
                conn = get_conn()
                conn.execute("""INSERT INTO expeditions (numero_bordereau,date_expedition,destination,quantite_totale,
                    temperature,vehicule,agent,statut,observations) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (numero, datetime.now().isoformat(), dest, qte, temp, vehicule, agent, "en_transit", obs))
                conn.commit(); conn.close(); win.destroy(); self.show_expeditions()
            except Exception as ex: messagebox.showerror("Erreur", str(ex))
        ttk.Button(win, text="Enregistrer", command=save).pack(pady=10)

    def del_expedition(self):
        sel = self.tree_exp.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez"); return
        if messagebox.askyesno("Confirmation", "Supprimer ?"):
            eid = self.tree_exp.item(sel[0])["values"][0]
            conn = get_conn(); conn.execute("DELETE FROM expeditions WHERE id=?", (eid,)); conn.commit(); conn.close()
            self.show_expeditions()

    def marquer_recu(self):
        sel = self.tree_exp.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez"); return
        eid = self.tree_exp.item(sel[0])["values"][0]
        conn = get_conn(); conn.execute("UPDATE expeditions SET statut='recu' WHERE id=?", (eid,)); conn.commit(); conn.close()
        self.show_expeditions()

    def show_clients(self):
        self.clear()
        ttk.Label(self.main, text="Laiteries & Clients", font=("Arial", 15, "bold")).pack(pady=6)
        tb = ttk.Frame(self.main); tb.pack(fill="x")
        ttk.Button(tb, text="Ajouter", command=self.add_client).pack(side="left", padx=3)
        ttk.Button(tb, text="Modifier", command=self.edit_client).pack(side="left", padx=3)
        ttk.Button(tb, text="Supprimer", command=self.del_client).pack(side="left", padx=3)
        ttk.Button(tb, text="Actualiser", command=self.show_clients).pack(side="left", padx=3)
        cols = ("id", "code", "nom", "type", "tel", "adresse")
        self.tree_cli = ttk.Treeview(self.main, columns=cols, show="headings", height=16)
        for c, t in zip(cols, ["ID", "Code", "Nom", "Type", "Tel", "Adresse"]):
            self.tree_cli.heading(c, text=t); self.tree_cli.column(c, width=110)
        self.tree_cli.pack(fill="both", expand=True, pady=4)
        conn = get_conn()
        for r in conn.execute("SELECT * FROM clients ORDER BY type_client, nom"):
            self.tree_cli.insert("", "end", values=(r["id"], r["code"], r["nom"], r["type_client"], r["telephone"] or "", r["adresse"] or ""))
        conn.close()

    def add_client(self):
        self._form_client()

    def edit_client(self):
        sel = self.tree_cli.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez une laiterie / client")
            return
        self._form_client(self.tree_cli.item(sel[0])["values"][0])

    def _form_client(self, cid=None):
        win = tk.Toplevel(self)
        win.title("Laiterie / Client")
        win.geometry("400x400")
        win.grab_set()
        fields = {}
        for key, label in [
            ("code", "Code *"),
            ("nom", "Nom *"),
            ("tel", "Telephone"),
            ("adresse", "Adresse"),
            ("contact", "Contact"),
            ("notes", "Notes"),
        ]:
            ttk.Label(win, text=label).pack(pady=(5, 0))
            e = ttk.Entry(win, width=40)
            e.pack()
            fields[key] = e
        type_var = tk.StringVar(value="laiterie")
        ttk.Label(win, text="Type").pack(pady=(5, 0))
        ttk.Combobox(
            win,
            textvariable=type_var,
            values=["laiterie", "autre", "grossiste"],
            state="readonly",
            width=38,
        ).pack()
        if cid:
            conn = get_conn()
            r = conn.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone()
            conn.close()
            if r:
                fields["code"].insert(0, r["code"] or "")
                fields["nom"].insert(0, r["nom"] or "")
                fields["tel"].insert(0, r["telephone"] or "")
                fields["adresse"].insert(0, r["adresse"] or "")
                fields["contact"].insert(0, r["contact"] or "")
                fields["notes"].insert(0, r["notes"] or "")
                type_var.set(r["type_client"] or "laiterie")
        def save():
            try:
                code = fields["code"].get().strip()
                nom = fields["nom"].get().strip()
                if not code or not nom:
                    raise ValueError("Code et nom obligatoires")
                conn = get_conn()
                if cid:
                    conn.execute(
                        """UPDATE clients SET code=?,nom=?,type_client=?,telephone=?,
                           adresse=?,contact=?,notes=? WHERE id=?""",
                        (
                            code, nom, type_var.get(),
                            fields["tel"].get().strip(),
                            fields["adresse"].get().strip(),
                            fields["contact"].get().strip(),
                            fields["notes"].get().strip(),
                            cid,
                        ),
                    )
                else:
                    conn.execute(
                        """INSERT INTO clients
                           (code,nom,type_client,telephone,adresse,contact,notes)
                           VALUES (?,?,?,?,?,?,?)""",
                        (
                            code, nom, type_var.get(),
                            fields["tel"].get().strip(),
                            fields["adresse"].get().strip(),
                            fields["contact"].get().strip(),
                            fields["notes"].get().strip(),
                        ),
                    )
                conn.commit()
                conn.close()
                win.destroy()
                self.show_clients()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))
        bf = ttk.Frame(win)
        bf.pack(pady=12)
        ttk.Button(bf, text="Enregistrer", command=save, width=14).pack(side="left", padx=8)
        ttk.Button(bf, text="Annuler", command=win.destroy, width=14).pack(side="left", padx=8)

    def del_client(self):
        sel = self.tree_cli.selection()
        if not sel: messagebox.showwarning("Attention", "Selectionnez"); return
        if messagebox.askyesno("Confirmation", "Supprimer ?"):
            cid = self.tree_cli.item(sel[0])["values"][0]
            conn = get_conn(); conn.execute("DELETE FROM clients WHERE id=?", (cid,)); conn.commit(); conn.close()
            self.show_clients()

    def show_parametres(self):
        self.clear()
        ttk.Label(self.main, text="Parametres du Centre", font=("Arial", 15, "bold")).pack(pady=10)
        form = ttk.Frame(self.main); form.pack(pady=8)
        fields = {}
        labels = [("nom_centre", "Nom du centre"), ("adresse_centre", "Adresse"), ("tel_centre", "Telephone"),
                  ("rc_centre", "RC"), ("nif_centre", "NIF"), ("entete_facture", "En-tete facture"), ("pied_facture", "Pied de page")]
        for i, (key, label) in enumerate(labels):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="ne", padx=5, pady=5)
            if key in ("entete_facture", "pied_facture"):
                e = tk.Text(form, width=48, height=3, font=("Arial", 10)); e.grid(row=i, column=1, padx=5, pady=5); e.insert("1.0", get_param(key, ""))
            else:
                e = ttk.Entry(form, width=48); e.grid(row=i, column=1, padx=5, pady=5); e.insert(0, get_param(key, ""))
            fields[key] = e
        def save():
            for key, widget in fields.items():
                val = widget.get("1.0", "end").strip() if isinstance(widget, tk.Text) else widget.get().strip()
                set_param(key, val)
            messagebox.showinfo("Succes", "Parametres enregistres")
            self.title("%s - %s" % (get_param("nom_centre"), self.user.get("nom_complet") or self.user.get("username")))
        ttk.Button(self.main, text="Enregistrer", command=save).pack(pady=12)

    def show_compte(self):
        self.clear()
        ttk.Label(self.main, text="Mon Compte", font=("Arial", 15, "bold")).pack(pady=15)
        form = ttk.Frame(self.main); form.pack(pady=10)
        ttk.Label(form, text="Utilisateur actuel :").grid(row=0, column=0, sticky="e", padx=5, pady=8)
        ttk.Label(form, text=self.user.get("username", ""), font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Nouveau utilisateur :").grid(row=1, column=0, sticky="e", padx=5, pady=8)
        new_user = ttk.Entry(form, width=30); new_user.grid(row=1, column=1, padx=5, pady=8); new_user.insert(0, self.user.get("username", ""))
        ttk.Label(form, text="Nom complet :").grid(row=2, column=0, sticky="e", padx=5, pady=8)
        new_nom = ttk.Entry(form, width=30); new_nom.grid(row=2, column=1, padx=5, pady=8); new_nom.insert(0, self.user.get("nom_complet") or "")
        ttk.Label(form, text="Mot de passe actuel :").grid(row=3, column=0, sticky="e", padx=5, pady=8)
        old_pwd = ttk.Entry(form, width=30, show="*"); old_pwd.grid(row=3, column=1, padx=5, pady=8)
        ttk.Label(form, text="Nouveau mot de passe :").grid(row=4, column=0, sticky="e", padx=5, pady=8)
        new_pwd = ttk.Entry(form, width=30, show="*"); new_pwd.grid(row=4, column=1, padx=5, pady=8)
        ttk.Label(form, text="Confirmer :").grid(row=5, column=0, sticky="e", padx=5, pady=8)
        conf_pwd = ttk.Entry(form, width=30, show="*"); conf_pwd.grid(row=5, column=1, padx=5, pady=8)
        def save():
            try:
                uid = self.user["id"]
                if not old_pwd.get(): raise ValueError("Mot de passe actuel obligatoire")
                old_hash = hashlib.sha256(old_pwd.get().encode("utf-8")).hexdigest()
                conn = get_conn()
                if not conn.execute("SELECT id FROM users WHERE id=? AND password_hash=?", (uid, old_hash)).fetchone():
                    conn.close(); raise ValueError("Mot de passe actuel incorrect")
                username = new_user.get().strip(); nom = new_nom.get().strip()
                if not username: raise ValueError("Nom d'utilisateur obligatoire")
                if conn.execute("SELECT id FROM users WHERE username=? AND id!=?", (username, uid)).fetchone():
                    conn.close(); raise ValueError("Ce nom d'utilisateur existe deja")
                if new_pwd.get():
                    if new_pwd.get() != conf_pwd.get(): conn.close(); raise ValueError("Mots de passe differents")
                    if len(new_pwd.get()) < 4: conn.close(); raise ValueError("Mot de passe trop court")
                    nh = hashlib.sha256(new_pwd.get().encode("utf-8")).hexdigest()
                    conn.execute("UPDATE users SET username=?,nom_complet=?,password_hash=? WHERE id=?", (username, nom, nh, uid))
                else:
                    conn.execute("UPDATE users SET username=?,nom_complet=? WHERE id=?", (username, nom, uid))
                conn.commit(); conn.close()
                self.user["username"] = username; self.user["nom_complet"] = nom
                messagebox.showinfo("Succes", "Identifiants mis a jour")
            except Exception as ex: messagebox.showerror("Erreur", str(ex))
        ttk.Button(self.main, text="Enregistrer", command=save).pack(pady=15)

    def show_reports(self):
        self.clear()
        ttk.Label(self.main, text="Rapports & Exports", font=("Arial", 15, "bold")).pack(pady=8)

        filt = ttk.Frame(self.main)
        filt.pack(fill="x", pady=4)
        ttk.Label(filt, text="Periode Du :").pack(side="left", padx=3)
        self._rap_date_debut = ttk.Entry(filt, width=12)
        self._rap_date_debut.insert(0, (date.today() - timedelta(days=30)).isoformat())
        self._rap_date_debut.pack(side="left")
        ttk.Label(filt, text="Au :").pack(side="left", padx=(8, 2))
        self._rap_date_fin = ttk.Entry(filt, width=12)
        self._rap_date_fin.insert(0, date.today().isoformat())
        self._rap_date_fin.pack(side="left")
        ttk.Label(filt, text="(AAAA-MM-JJ)").pack(side="left", padx=6)
        ttk.Button(filt, text="Actualiser stats", command=self.show_reports).pack(side="left", padx=6)

        # Stats periode
        try:
            d1 = self._rap_date_debut.get().strip()
            d2 = self._rap_date_fin.get().strip()
            conn = get_conn()
            total_l = conn.execute(
                "SELECT COALESCE(SUM(quantite),0) FROM collectes WHERE date(date_heure)>=date(?) AND date(date_heure)<=date(?)",
                (d1, d2)).fetchone()[0]
            ca = conn.execute(
                "SELECT COALESCE(SUM(montant),0) FROM ventes WHERE date(date_vente)>=date(?) AND date(date_vente)<=date(?)",
                (d1, d2)).fetchone()[0]
            nb_exp = conn.execute(
                "SELECT COUNT(*) FROM expeditions WHERE date(date_expedition)>=date(?) AND date(date_expedition)<=date(?)",
                (d1, d2)).fetchone()[0]
            qte_exp = conn.execute(
                "SELECT COALESCE(SUM(quantite_totale),0) FROM expeditions WHERE date(date_expedition)>=date(?) AND date(date_expedition)<=date(?)",
                (d1, d2)).fetchone()[0]
            conn.close()
        except Exception:
            total_l = ca = nb_exp = qte_exp = 0

        frame = ttk.Frame(self.main)
        frame.pack(pady=10)
        for title, val in [
            ("Volume collectes", "%.0f L" % total_l),
            ("CA Aliments", "%.0f %s" % (ca, MONNAIE)),
            ("Expeditions", str(nb_exp)),
            ("Volume expedie", "%.0f L" % qte_exp),
        ]:
            f = ttk.LabelFrame(frame, text=title, padding=8)
            f.pack(side="left", padx=5)
            ttk.Label(f, text=val, font=("Arial", 12, "bold")).pack()

        btn = ttk.Frame(self.main)
        btn.pack(pady=10)
        ttk.Button(btn, text="Export Collectes CSV", command=self.export_collectes).pack(side="left", padx=4)
        ttk.Button(btn, text="Export Ventes CSV", command=self.export_ventes).pack(side="left", padx=4)
        ttk.Button(btn, text="Export Expeditions CSV", command=self.export_expeditions).pack(side="left", padx=4)

        btn2 = ttk.Frame(self.main)
        btn2.pack(pady=6)
        ttk.Button(btn2, text="Export Eleveurs CSV", command=self.export_eleveurs).pack(side="left", padx=4)
        ttk.Button(btn2, text="Export Collecteurs CSV", command=self.export_collecteurs).pack(side="left", padx=4)
        ttk.Button(btn2, text="Export Avances CSV", command=self.export_avances).pack(side="left", padx=4)

        tk.Label(
            self.main,
            text="Les exports Collectes / Ventes / Expeditions / Avances respectent la periode ci-dessus.",
            fg="#555555",
        ).pack(pady=4)

    def _rapport_dates(self):
        """Retourne (debut, fin) pour les exports, ou ('', '') si vides."""
        d1 = getattr(self, "_rap_date_debut", None)
        d2 = getattr(self, "_rap_date_fin", None)
        return ((d1.get().strip() if d1 else "") or "",
                (d2.get().strip() if d2 else "") or "")

    def export_collectes(self):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "collectes_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
        d1, d2 = self._rapport_dates()
        conn = get_conn()
        sql = """
            SELECT c.numero_bon, e.code_unique, e.nom||' '||e.prenom as elev,
                   e.region, COALESCE(col.nom||' '||col.prenom,'') as collecteur,
                   COALESCE(l.nom,'') as laiterie,
                   c.date_heure, c.quantite, c.acidite, c.densite, c.agent, c.vehicule
            FROM collectes c
            LEFT JOIN eleveurs e ON c.eleveur_id=e.id
            LEFT JOIN collecteurs col ON e.collecteur_id=col.id
            LEFT JOIN clients l ON e.laiterie_id=l.id
            WHERE 1=1"""
        params = []
        if d1:
            sql += " AND date(c.date_heure) >= date(?)"
            params.append(d1)
        if d2:
            sql += " AND date(c.date_heure) <= date(?)"
            params.append(d2)
        sql += " ORDER BY c.date_heure"
        rows = conn.execute(sql, params).fetchall(); conn.close()
        with open(path, "w") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["N Bon", "Code elev", "Eleveur", "Region", "Collecteur", "Laiterie",
                        "Date", "Qte", "Acidite", "Densite", "Agent", "Vehicule"])
            for r in rows:
                w.writerow([r["numero_bon"], r["code_unique"], r["elev"], r["region"],
                            r["collecteur"], r["laiterie"], r["date_heure"], r["quantite"],
                            r["acidite"], r["densite"], r["agent"], r["vehicule"]])
        messagebox.showinfo("Succes", path)

    def export_ventes(self):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "ventes_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
        d1, d2 = self._rapport_dates()
        conn = get_conn()
        sql = """
            SELECT v.numero, e.code_unique, e.nom||' '||e.prenom as elev,
                   COALESCE(col.nom||' '||col.prenom,'') as collecteur,
                   p.reference, p.nom as prod, v.quantite, v.montant, v.mode, v.date_vente
            FROM ventes v
            LEFT JOIN eleveurs e ON v.eleveur_id=e.id
            LEFT JOIN collecteurs col ON e.collecteur_id=col.id
            LEFT JOIN produits p ON v.produit_id=p.id
            WHERE 1=1"""
        params = []
        if d1:
            sql += " AND date(v.date_vente) >= date(?)"
            params.append(d1)
        if d2:
            sql += " AND date(v.date_vente) <= date(?)"
            params.append(d2)
        sql += " ORDER BY v.date_vente"
        rows = conn.execute(sql, params).fetchall(); conn.close()
        with open(path, "w") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["N", "Code elev", "Eleveur", "Collecteur", "Ref produit", "Produit",
                        "Qte", "Montant", "Mode", "Date"])
            for r in rows:
                w.writerow([r["numero"], r["code_unique"], r["elev"], r["collecteur"],
                            r["reference"], r["prod"], r["quantite"], r["montant"], r["mode"], r["date_vente"]])
        messagebox.showinfo("Succes", path)

    def export_expeditions(self):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "expeditions_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
        d1, d2 = self._rapport_dates()
        conn = get_conn()
        sql = "SELECT * FROM expeditions WHERE 1=1"
        params = []
        if d1:
            sql += " AND date(date_expedition) >= date(?)"
            params.append(d1)
        if d2:
            sql += " AND date(date_expedition) <= date(?)"
            params.append(d2)
        sql += " ORDER BY date_expedition"
        rows = conn.execute(sql, params).fetchall(); conn.close()
        with open(path, "w") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["N", "Date", "Destination", "Qte", "Temp", "Vehicule", "Agent", "Statut", "Observations"])
            for r in rows:
                w.writerow([r["numero_bordereau"], r["date_expedition"], r["destination"],
                            r["quantite_totale"], r["temperature"], r["vehicule"], r["agent"],
                            r["statut"], r["observations"]])
        messagebox.showinfo("Succes", path)

    def export_eleveurs(self):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "eleveurs_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
        conn = get_conn()
        rows = conn.execute("""
            SELECT e.code_unique, e.nom, e.prenom, e.telephone, e.adresse, e.region,
                   e.date_adhesion, e.statut,
                   COALESCE(c.nom||' '||c.prenom,'') as collecteur,
                   COALESCE(l.nom,'') as laiterie
            FROM eleveurs e
            LEFT JOIN collecteurs c ON e.collecteur_id=c.id
            LEFT JOIN clients l ON e.laiterie_id=l.id
            ORDER BY e.nom
        """).fetchall(); conn.close()
        with open(path, "w") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Code", "Nom", "Prenom", "Tel", "Adresse", "Region", "Adhesion",
                        "Statut", "Collecteur", "Laiterie"])
            for r in rows:
                w.writerow([r["code_unique"], r["nom"], r["prenom"], r["telephone"], r["adresse"],
                            r["region"], r["date_adhesion"], r["statut"], r["collecteur"], r["laiterie"]])
        messagebox.showinfo("Succes", path)

    def export_collecteurs(self):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "collecteurs_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
        conn = get_conn()
        rows = conn.execute("""
            SELECT c.code, c.nom, c.prenom, c.telephone, c.region, c.vehicule, c.statut,
                   COUNT(DISTINCT e.id) as nb_elev,
                   COALESCE(SUM(col.quantite),0) as volume
            FROM collecteurs c
            LEFT JOIN eleveurs e ON e.collecteur_id=c.id
            LEFT JOIN collectes col ON col.eleveur_id=e.id
            GROUP BY c.id
            ORDER BY c.nom
        """).fetchall(); conn.close()
        with open(path, "w") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Code", "Nom", "Prenom", "Tel", "Region", "Vehicule", "Statut",
                        "Nb eleveurs", "Volume litres"])
            for r in rows:
                w.writerow([r["code"], r["nom"], r["prenom"], r["telephone"], r["region"],
                            r["vehicule"], r["statut"], r["nb_elev"], r["volume"]])
        messagebox.showinfo("Succes", path)

    def export_avances(self):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "avances_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
        d1, d2 = self._rapport_dates()
        conn = get_conn()
        sql = """
            SELECT a.date_avance, e.code_unique, e.nom||' '||e.prenom as elev,
                   COALESCE(c.nom||' '||c.prenom,'') as collecteur,
                   a.montant, a.motif, a.statut
            FROM avances a
            LEFT JOIN eleveurs e ON a.eleveur_id=e.id
            LEFT JOIN collecteurs c ON e.collecteur_id=c.id
            WHERE 1=1"""
        params = []
        if d1:
            sql += " AND date(a.date_avance) >= date(?)"
            params.append(d1)
        if d2:
            sql += " AND date(a.date_avance) <= date(?)"
            params.append(d2)
        sql += " ORDER BY a.date_avance"
        rows = conn.execute(sql, params).fetchall(); conn.close()
        with open(path, "w") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Date", "Code elev", "Eleveur", "Collecteur", "Montant", "Motif", "Statut"])
            for r in rows:
                w.writerow([r["date_avance"], r["code_unique"], r["elev"], r["collecteur"],
                            r["montant"], r["motif"], r["statut"]])
        messagebox.showinfo("Succes", path)
