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


def generer_fiche_eleveur(elev, stats, collectes_rows, avances_rows, collecteur_nom="", laiterie_nom=""):
    """Genere un fichier texte fiche eleveur pour impression."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    code = elev["code_unique"] or str(elev["id"])
    path = os.path.join(EXPORTS_DIR, "fiche_eleveur_%s.txt" % code.replace("/", "-"))
    nom_centre = get_param("nom_centre", "Centre de Collecte de Lait")
    W = 72

    def ligne(car="="):
        return car * W + "\n"

    def centre(txt):
        return txt.center(W) + "\n"

    def g(label, val, largeur=22):
        return "  %-*s : %s\n" % (largeur, label, val if val not in (None, "") else "-")

    with open(path, "w") as f:
        f.write("\n")
        f.write(ligne("="))
        f.write(centre(nom_centre))
        f.write(centre("FICHE ELEVEUR"))
        f.write(ligne("="))
        f.write(g("Code", elev["code_unique"]))
        f.write(g("Nom", "%s %s" % (elev["nom"], elev["prenom"])))
        f.write(g("Telephone", elev["telephone"]))
        f.write(g("Adresse", elev["adresse"]))
        f.write(g("Region", elev["region"]))
        f.write(g("Statut", elev["statut"]))
        f.write(g("Collecteur", collecteur_nom))
        f.write(g("Laiterie", laiterie_nom))
        f.write(g("Date adhesion", elev["date_adhesion"]))
        f.write(ligne("-"))
        f.write(centre("RESUME"))
        f.write(ligne("-"))
        f.write(g("Nb collectes", stats.get("nb_col", 0)))
        f.write(g("Volume total", "%.1f L" % stats.get("total_l", 0)))
        f.write(g("Achats aliments", "%.0f %s" % (stats.get("total_v", 0), MONNAIE)))
        f.write(g("Avances non deduites", "%.0f %s" % (stats.get("total_av", 0), MONNAIE)))
        f.write(ligne("-"))
        f.write(centre("DERNIERES COLLECTES"))
        f.write(ligne("-"))
        f.write("  %-16s %8s %8s %8s %s\n" % ("Date", "Qte", "Acid.", "Dens.", "Agent"))
        for r in collectes_rows[:15]:
            f.write("  %-16s %8.1f %8s %8s %s\n" % (
                (r["date_heure"] or "")[:16],
                r["quantite"] or 0,
                r["acidite"] if r["acidite"] is not None else "-",
                r["densite"] if r["densite"] is not None else "-",
                r["agent"] or "",
            ))
        f.write(ligne("-"))
        f.write(centre("AVANCES"))
        f.write(ligne("-"))
        for r in avances_rows[:10]:
            f.write("  %s  %10.0f %s  %s  [%s]\n" % (
                (r["date_avance"] or "")[:10],
                r["montant"] or 0,
                MONNAIE,
                r["motif"] or "",
                r["statut"] or "",
            ))
        f.write(ligne("="))
        f.write(centre("Imprime le %s" % datetime.now().strftime("%d/%m/%Y %H:%M")))
        f.write(ligne("="))
    return path


def generer_fiche_collecteur(col, elevs_rows, volume_total=0, nb_collectes=0):
    """Genere un fichier texte fiche collecteur pour impression."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    code = col["code"] or str(col["id"])
    path = os.path.join(EXPORTS_DIR, "fiche_collecteur_%s.txt" % code.replace("/", "-"))
    nom_centre = get_param("nom_centre", "Centre de Collecte de Lait")
    W = 72

    def ligne(car="="):
        return car * W + "\n"

    def centre(txt):
        return txt.center(W) + "\n"

    def g(label, val, largeur=22):
        return "  %-*s : %s\n" % (largeur, label, val if val not in (None, "") else "-")

    with open(path, "w") as f:
        f.write("\n")
        f.write(ligne("="))
        f.write(centre(nom_centre))
        f.write(centre("FICHE COLLECTEUR"))
        f.write(ligne("="))
        f.write(g("Code", col["code"]))
        f.write(g("Nom", "%s %s" % (col["nom"], col["prenom"])))
        f.write(g("Telephone", col["telephone"]))
        f.write(g("Region", col["region"]))
        f.write(g("Vehicule", col["vehicule"]))
        f.write(g("Statut", col["statut"]))
        f.write(g("Notes", col["notes"]))
        f.write(ligne("-"))
        f.write(centre("RESUME"))
        f.write(ligne("-"))
        f.write(g("Nb eleveurs", len(elevs_rows)))
        f.write(g("Nb collectes", nb_collectes))
        f.write(g("Volume total", "%.1f L" % volume_total))
        f.write(ligne("-"))
        f.write(centre("ELEVEURS RATTACHES"))
        f.write(ligne("-"))
        f.write("  %-10s %-20s %-12s %s\n" % ("Code", "Nom", "Tel", "Region"))
        for e in elevs_rows:
            f.write("  %-10s %-20s %-12s %s\n" % (
                e["code_unique"] or "",
                ("%s %s" % (e["nom"], e["prenom"]))[:20],
                (e["telephone"] or "")[:12],
                e["region"] or "",
            ))
        f.write(ligne("="))
        f.write(centre("Imprime le %s" % datetime.now().strftime("%d/%m/%Y %H:%M")))
        f.write(ligne("="))
    return path
