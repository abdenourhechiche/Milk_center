# -*- coding: utf-8 -*-
"""Utilitaires : impression, generation facture A4."""
from __future__ import print_function, unicode_literals
import os
import sys
import subprocess
from datetime import datetime

from src.config import EXPORTS_DIR, MONNAIE
from src.database import get_param


def imprimer_fichier(path):
    """Envoie un fichier texte a l'imprimante (Windows 7 compatible)."""
    from tkinter import messagebox

    if not os.path.exists(path):
        messagebox.showerror("Erreur", "Fichier introuvable :\n%s" % path)
        return False
    try:
        if sys.platform == "win32":
            try:
                os.startfile(path, "print")
                messagebox.showinfo("Impression", "Facture envoyee a l'imprimante.")
                return True
            except Exception:
                pass
            try:
                subprocess.Popen(["notepad.exe", "/p", path])
                messagebox.showinfo("Impression", "Impression lancee via Notepad.")
                return True
            except Exception:
                pass
            os.startfile(path)
            messagebox.showinfo(
                "Info",
                "Fichier ouvert.\nUtilisez Fichier > Imprimer dans le bloc-notes.",
            )
            return True
        else:
            for cmd in (["lp", path], ["lpr", path], ["xdg-open", path]):
                try:
                    subprocess.Popen(cmd)
                    messagebox.showinfo("Impression", "Commande d'impression lancee.")
                    return True
                except Exception:
                    continue
            messagebox.showwarning(
                "Attention", "Impossible d'imprimer.\nFichier : %s" % path
            )
            return False
    except Exception as ex:
        messagebox.showerror("Erreur impression", str(ex))
        return False


def generer_facture_a4(
    numero, elev, litres, prix, credit, debit, avances, solde,
    statut, reglement, debut, fin
):
    """Genere un fichier texte format A4 pour une facture."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    path = os.path.join(EXPORTS_DIR, "facture_%s.txt" % numero)

    nom_centre = get_param("nom_centre", "Centre de Collecte de Lait")
    adresse = get_param("adresse_centre", "")
    tel = get_param("tel_centre", "")
    rc = get_param("rc_centre", "")
    nif = get_param("nif_centre", "")
    entete = get_param("entete_facture", nom_centre)
    pied = get_param("pied_facture", "Merci de votre confiance")
    W = 78

    def ligne(car="="):
        return car * W + "\n"

    def centre(txt):
        return txt.center(W) + "\n"

    def g(label, val, largeur=24):
        return "  %-*s : %s\n" % (largeur, label, val)

    with open(path, "w") as f:
        f.write("\n")
        f.write(ligne("="))
        for line in entete.split("\n"):
            f.write(centre(line.strip()))
        f.write(ligne("="))
        f.write("\n")
        f.write(centre("F A C T U R E"))
        f.write("\n")
        f.write(g("N facture", numero))
        f.write(g("Date emission", datetime.now().strftime("%d/%m/%Y %H:%M")))
        f.write(g("Periode", "Du %s au %s" % (debut, fin)))
        f.write(g("Mode reglement", reglement))
        if statut:
            f.write(g("Statut", statut.upper()))
        f.write("\n")
        f.write(ligne("-"))
        f.write(centre("CLIENT / ELEVEUR"))
        f.write(ligne("-"))
        f.write(g("Nom", "%s %s" % (elev["nom"], elev["prenom"])))
        f.write(g("Code", elev["code_unique"]))
        f.write(g("Telephone", elev["telephone"] or "N/A"))
        f.write("\n")
        f.write(ligne("-"))
        f.write(centre("DETAIL"))
        f.write(ligne("-"))
        f.write("  %-38s %14s %12s\n" % ("Designation", "Detail", "Montant"))
        f.write(ligne("-"))
        f.write(
            "  %-38s %14s %12.0f\n"
            % ("Credit lait livre", "%.1f L x %.0f" % (litres, prix), credit)
        )
        f.write("  %-38s %14s %12.0f\n" % ("Debit aliments (credit)", "-", debit))
        f.write("  %-38s %14s %12.0f\n" % ("Avances deduites", "-", avances))
        f.write(ligne("-"))
        f.write(
            "  %-38s %14s %12.0f  %s\n" % ("SOLDE NET", "", solde, MONNAIE)
        )
        if solde >= 0:
            f.write(centre("(a payer a l'eleveur)"))
        else:
            f.write(centre("(a recevoir de l'eleveur)"))
        f.write("\n")
        f.write(ligne("="))
        if rc:
            f.write(g("RC", rc))
        if nif:
            f.write(g("NIF", nif))
        f.write(g("Tel centre", tel))
        f.write(g("Adresse", adresse))
        f.write(ligne("="))
        f.write(centre(pied))
        f.write(ligne("="))
        f.write("\n")
    return path
