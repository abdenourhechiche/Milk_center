# -*- coding: utf-8 -*-
"""Module Ventes & Stock (aliments)."""
from __future__ import print_function, unicode_literals
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import uuid

from src.database import get_conn
from src.config import MONNAIE


class VentesMixin(object):
    def show_ventes(self):
        self.clear()
        ttk.Label(
            self.main, text="Ventes & Stock Aliments", font=("Arial", 15, "bold")
        ).pack(pady=6)
        nb = ttk.Notebook(self.main)
        nb.pack(fill="both", expand=True)

        # --- Ventes ---
        f1 = ttk.Frame(nb)
        nb.add(f1, text="Ventes")
        tb = ttk.Frame(f1)
        tb.pack(fill="x")
        ttk.Button(tb, text="Nouvelle Vente", command=self.add_vente).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Modifier", command=self.edit_vente).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Supprimer", command=self.del_vente).pack(
            side="left", padx=3
        )
        ttk.Button(tb, text="Actualiser", command=self.show_ventes).pack(
            side="left", padx=3
        )

        cols = ("id", "num", "elev", "prod", "qte", "montant", "date")
        self.tree_v = ttk.Treeview(f1, columns=cols, show="headings", height=13)
        for c, t in zip(
            cols, ["ID", "N", "Eleveur", "Produit", "Qte", "Montant", "Date"]
        ):
            self.tree_v.heading(c, text=t)
            self.tree_v.column(c, width=95)
        self.tree_v.pack(fill="both", expand=True, pady=3)

        conn = get_conn()
        for r in conn.execute(
            """SELECT v.*, e.nom||' '||e.prenom as elev, p.nom as prod
               FROM ventes v
               LEFT JOIN eleveurs e ON v.eleveur_id=e.id
               LEFT JOIN produits p ON v.produit_id=p.id
               ORDER BY v.date_vente DESC LIMIT 200"""
        ):
            self.tree_v.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["numero"],
                    r["elev"] or "?",
                    r["prod"] or "?",
                    r["quantite"],
                    "%.0f" % (r["montant"] or 0),
                    (r["date_vente"] or "")[:10],
                ),
            )

        # --- Produits ---
        f2 = ttk.Frame(nb)
        nb.add(f2, text="Produits / Stock")
        tb2 = ttk.Frame(f2)
        tb2.pack(fill="x")
        ttk.Button(tb2, text="Ajouter Produit", command=lambda: self.form_produit()).pack(
            side="left", padx=3
        )
        ttk.Button(tb2, text="Modifier", command=self.edit_produit).pack(
            side="left", padx=3
        )
        ttk.Button(tb2, text="Supprimer", command=self.del_produit).pack(
            side="left", padx=3
        )
        ttk.Button(tb2, text="Actualiser", command=self.show_ventes).pack(
            side="left", padx=3
        )

        cols2 = ("id", "ref", "nom", "prix", "stock", "alerte")
        self.tree_s = ttk.Treeview(f2, columns=cols2, show="headings", height=13)
        for c, t in zip(
            cols2, ["ID", "Ref", "Nom", "Prix", "Stock", "Alerte"]
        ):
            self.tree_s.heading(c, text=t)
            self.tree_s.column(c, width=100)
        self.tree_s.pack(fill="both", expand=True, pady=3)

        for r in conn.execute("SELECT * FROM produits"):
            alerte = (
                "BAS"
                if (r["stock"] or 0) <= (r["seuil_alerte"] or 10)
                else "OK"
            )
            self.tree_s.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["reference"],
                    r["nom"],
                    "%.0f" % (r["prix"] or 0),
                    "%.1f" % (r["stock"] or 0),
                    alerte,
                ),
            )
        conn.close()

    def form_produit(self, pid=None):
        win = tk.Toplevel(self)
        win.title("Produit")
        win.geometry("360x300")
        win.grab_set()
        fields = {}
        for key, label in [
            ("ref", "Reference *"),
            ("nom", "Nom *"),
            ("prix", "Prix (%s) *" % MONNAIE),
            ("stock", "Stock initial"),
            ("seuil", "Seuil alerte"),
        ]:
            ttk.Label(win, text=label).pack(pady=(5, 0))
            e = ttk.Entry(win, width=34)
            e.pack()
            fields[key] = e
        fields["seuil"].insert(0, "10")
        fields["stock"].insert(0, "0")

        if pid:
            conn = get_conn()
            r = conn.execute(
                "SELECT * FROM produits WHERE id=?", (pid,)
            ).fetchone()
            conn.close()
            if r:
                fields["ref"].insert(0, r["reference"] or "")
                fields["nom"].insert(0, r["nom"] or "")
                fields["prix"].delete(0, "end")
                fields["prix"].insert(0, str(r["prix"] or ""))
                fields["stock"].delete(0, "end")
                fields["stock"].insert(0, str(r["stock"] or 0))
                fields["seuil"].delete(0, "end")
                fields["seuil"].insert(0, str(r["seuil_alerte"] or 10))

        def save():
            try:
                ref = fields["ref"].get().strip()
                nom = fields["nom"].get().strip()
                if not ref or not nom:
                    messagebox.showerror(
                        "Erreur", "Reference et Nom sont obligatoires"
                    )
                    return
                try:
                    prix = float(
                        fields["prix"].get().replace(",", ".").strip()
                    )
                except Exception:
                    messagebox.showerror(
                        "Erreur", "Prix invalide (ex: 4500 ou 4500.5)"
                    )
                    return
                try:
                    stock = float(
                        (fields["stock"].get() or "0")
                        .replace(",", ".")
                        .strip()
                        or "0"
                    )
                except Exception:
                    messagebox.showerror("Erreur", "Stock invalide")
                    return
                try:
                    seuil = float(
                        (fields["seuil"].get() or "10")
                        .replace(",", ".")
                        .strip()
                        or "10"
                    )
                except Exception:
                    seuil = 10.0
                if prix < 0 or stock < 0:
                    messagebox.showerror(
                        "Erreur", "Prix et stock doivent etre >= 0"
                    )
                    return

                conn = get_conn()
                if pid:
                    conn.execute(
                        "UPDATE produits SET reference=?,nom=?,prix=?,stock=?,seuil_alerte=? WHERE id=?",
                        (ref, nom, prix, stock, seuil, pid),
                    )
                else:
                    if conn.execute(
                        "SELECT id FROM produits WHERE reference=?", (ref,)
                    ).fetchone():
                        conn.close()
                        messagebox.showerror(
                            "Erreur", "Cette reference existe deja"
                        )
                        return
                    conn.execute(
                        "INSERT INTO produits (reference,nom,prix,stock,seuil_alerte) VALUES (?,?,?,?,?)",
                        (ref, nom, prix, stock, seuil),
                    )
                conn.commit()
                conn.close()
                win.destroy()
                self.show_ventes()
                messagebox.showinfo("Succes", "Produit enregistre")
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

        ttk.Button(win, text="Enregistrer", command=save).pack(pady=10)

    def edit_produit(self):
        sel = self.tree_s.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un produit")
            return
        self.form_produit(self.tree_s.item(sel[0])["values"][0])

    def del_produit(self):
        sel = self.tree_s.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez un produit")
            return
        if not messagebox.askyesno("Confirmation", "Supprimer ce produit ?"):
            return
        pid = self.tree_s.item(sel[0])["values"][0]
        conn = get_conn()
        conn.execute("DELETE FROM produits WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        self.show_ventes()

    def add_vente(self):
        self._form_vente()

    def edit_vente(self):
        sel = self.tree_v.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez une vente")
            return
        self._form_vente(self.tree_v.item(sel[0])["values"][0])

    def _form_vente(self, vid=None):
        conn = get_conn()
        regions = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT region FROM eleveurs WHERE statut='actif' AND region IS NOT NULL AND region!='' ORDER BY region"
            ).fetchall()
        ]
        all_elevs = conn.execute(
            "SELECT id, nom, prenom, region FROM eleveurs WHERE statut='actif' ORDER BY nom"
        ).fetchall()
        prods = conn.execute(
            "SELECT id, nom, prix, stock FROM produits"
        ).fetchall()
        existing = None
        if vid:
            existing = conn.execute(
                "SELECT * FROM ventes WHERE id=?", (vid,)
            ).fetchone()
        conn.close()

        if not all_elevs:
            messagebox.showwarning("Attention", "Aucun eleveur actif")
            return
        if not prods:
            messagebox.showwarning(
                "Attention",
                "Aucun produit en stock.\nAjoutez d'abord un produit dans l'onglet Produits.",
            )
            return

        win = tk.Toplevel(self)
        win.title("Vente")
        win.geometry("420x420")
        win.grab_set()

        ttk.Label(win, text="Region (filtre)").pack(pady=(8, 0))
        region_var = tk.StringVar(value="Toutes")
        region_cb = ttk.Combobox(
            win,
            textvariable=region_var,
            values=["Toutes"] + regions,
            state="readonly",
            width=40,
        )
        region_cb.pack()

        ttk.Label(win, text="Eleveur").pack(pady=(6, 0))
        elev_var = tk.StringVar()
        elev_cb = ttk.Combobox(
            win, textvariable=elev_var, state="readonly", width=40
        )
        elev_cb.pack()

        def refresh_elevs(*a):
            reg = region_var.get()
            filtered = (
                all_elevs
                if reg == "Toutes"
                else [e for e in all_elevs if (e["region"] or "") == reg]
            )
            opts = [
                "%d - %s %s [%s]"
                % (e["id"], e["nom"], e["prenom"], e["region"] or "-")
                for e in filtered
            ]
            elev_cb["values"] = opts
            if opts:
                elev_var.set(
                    opts[0]
                    if elev_var.get() not in opts
                    else elev_var.get()
                )
            else:
                elev_var.set("")

        region_cb.bind("<<ComboboxSelected>>", refresh_elevs)
        refresh_elevs()

        ttk.Label(win, text="Produit").pack(pady=(6, 0))
        prod_var = tk.StringVar()
        prod_opts = [
            "%d - %s (stock: %.0f)" % (p["id"], p["nom"], p["stock"] or 0)
            for p in prods
        ]
        prod_cb = ttk.Combobox(
            win,
            textvariable=prod_var,
            values=prod_opts,
            state="readonly",
            width=40,
        )
        prod_cb.pack()
        prod_var.set(prod_opts[0])

        ttk.Label(win, text="Quantite").pack(pady=(6, 0))
        qte_e = ttk.Entry(win, width=40)
        qte_e.pack()

        mode_var = tk.StringVar(value="credit")
        ttk.Label(win, text="Mode paiement").pack(pady=(6, 0))
        ttk.Combobox(
            win,
            textvariable=mode_var,
            values=["credit", "comptant"],
            state="readonly",
            width=40,
        ).pack()

        if existing:
            for e in all_elevs:
                if e["id"] == existing["eleveur_id"]:
                    if e["region"]:
                        region_var.set(e["region"])
                        refresh_elevs()
                    for o in elev_cb["values"]:
                        if o.startswith("%d -" % e["id"]):
                            elev_var.set(o)
                            break
                    break
            for o in prod_opts:
                if o.startswith("%d -" % existing["produit_id"]):
                    prod_var.set(o)
                    break
            qte_e.insert(0, str(existing["quantite"] or ""))
            mode_var.set(existing["mode"] or "credit")

        def save():
            try:
                if not elev_var.get() or not prod_var.get():
                    messagebox.showerror(
                        "Erreur", "Selectionnez un eleveur et un produit"
                    )
                    return
                qtxt = qte_e.get().strip().replace(",", ".")
                if not qtxt:
                    messagebox.showerror("Erreur", "Saisissez la quantite")
                    return
                try:
                    qte = float(qtxt)
                except Exception:
                    messagebox.showerror(
                        "Erreur", "Quantite invalide (ex: 10 ou 10.5)"
                    )
                    return
                if qte <= 0:
                    messagebox.showerror(
                        "Erreur", "La quantite doit etre > 0"
                    )
                    return

                elev_id = int(elev_var.get().split(" - ")[0])
                prod_id = int(prod_var.get().split(" - ")[0])
                conn = get_conn()
                prod = conn.execute(
                    "SELECT * FROM produits WHERE id=?", (prod_id,)
                ).fetchone()
                if not prod:
                    conn.close()
                    messagebox.showerror("Erreur", "Produit introuvable")
                    return

                if vid and existing:
                    # restaurer ancien stock puis appliquer nouveau
                    old_pid = existing["produit_id"]
                    old_qte = existing["quantite"] or 0
                    conn.execute(
                        "UPDATE produits SET stock=stock+? WHERE id=?",
                        (old_qte, old_pid),
                    )
                    prod = conn.execute(
                        "SELECT * FROM produits WHERE id=?", (prod_id,)
                    ).fetchone()
                    if (prod["stock"] or 0) < qte:
                        # rollback partial - subtract back? better re-read
                        conn.execute(
                            "UPDATE produits SET stock=stock-? WHERE id=?",
                            (old_qte, old_pid),
                        )
                        conn.close()
                        messagebox.showerror(
                            "Erreur",
                            "Stock insuffisant (disponible: %.1f)"
                            % (prod["stock"] or 0),
                        )
                        return
                    montant = qte * prod["prix"]
                    conn.execute(
                        "UPDATE produits SET stock=stock-? WHERE id=?",
                        (qte, prod_id),
                    )
                    conn.execute(
                        """UPDATE ventes SET eleveur_id=?,produit_id=?,quantite=?,
                           montant=?,mode=? WHERE id=?""",
                        (elev_id, prod_id, qte, montant, mode_var.get(), vid),
                    )
                else:
                    if (prod["stock"] or 0) < qte:
                        messagebox.showerror(
                            "Erreur",
                            "Stock insuffisant (disponible: %.1f)"
                            % (prod["stock"] or 0),
                        )
                        conn.close()
                        return
                    montant = qte * prod["prix"]
                    from datetime import datetime
                    import uuid
                    numero = "VT-%s-%s" % (
                        datetime.now().strftime("%Y%m%d"),
                        uuid.uuid4().hex[:5].upper(),
                    )
                    conn.execute(
                        "INSERT INTO ventes (numero,eleveur_id,produit_id,quantite,montant,mode,date_vente) VALUES (?,?,?,?,?,?,?)",
                        (
                            numero,
                            elev_id,
                            prod_id,
                            qte,
                            montant,
                            mode_var.get(),
                            datetime.now().isoformat(),
                        ),
                    )
                    conn.execute(
                        "UPDATE produits SET stock=stock-? WHERE id=?",
                        (qte, prod_id),
                    )
                conn.commit()
                conn.close()
                win.destroy()
                self.show_ventes()
                messagebox.showinfo(
                    "Succes",
                    "Vente enregistree\nMontant : %.0f %s" % (montant, MONNAIE),
                )
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

        bf = ttk.Frame(win)
        bf.pack(pady=12)
        ttk.Button(bf, text="Enregistrer", command=save, width=14).pack(
            side="left", padx=8
        )
        ttk.Button(bf, text="Annuler", command=win.destroy, width=14).pack(
            side="left", padx=8
        )

    def del_vente(self):
        sel = self.tree_v.selection()
        if not sel:
            messagebox.showwarning("Attention", "Selectionnez une vente")
            return
        if not messagebox.askyesno(
            "Confirmation", "Supprimer cette vente ?\n(Le stock sera restaure)"
        ):
            return
        vid = self.tree_v.item(sel[0])["values"][0]
        conn = get_conn()
        v = conn.execute(
            "SELECT * FROM ventes WHERE id=?", (vid,)
        ).fetchone()
        if v:
            conn.execute(
                "UPDATE produits SET stock=stock+? WHERE id=?",
                (v["quantite"], v["produit_id"]),
            )
            conn.execute("DELETE FROM ventes WHERE id=?", (vid,))
            conn.commit()
        conn.close()
        self.show_ventes()
