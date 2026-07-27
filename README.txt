CENTRE DE COLLECTE DE LAIT - Version LITE (modulaire)
======================================================
Monnaie : Dinar Algerien (DA)
Compatible Python 3.6 / Windows 7 32 bits
AUCUNE bibliotheque externe requise

INSTALLATION
------------
1. Decompresser le ZIP
2. Ouvrir une invite de commandes dans le dossier milk_lite
3. Lancer :

   python main.py

Compte demo : admin / admin123

STRUCTURE DES FICHIERS
----------------------
milk_lite/
  main.py                 <- point d'entree
  README.txt
  data/                   <- base SQLite
  exports/                <- factures et CSV
  src/
    config.py             <- configuration (monnaie, chemins)
    database.py           <- SQLite, init, parametres
    utils.py              <- impression, generation facture A4
    ui/
      login.py            <- fenetre de connexion
      window.py           <- fenetre principale + menu
      modules_eleveurs.py <- eleveurs + fiche
      modules_ventes.py   <- ventes + stock aliments
      modules_autres.py   <- collectes, avances, factures,
                             agrements, expeditions, clients,
                             parametres, compte, rapports

FONCTIONNALITES
---------------
- Eleveurs (code auto, region, fiche detaillee)
- Collectes (acidite, densite, filtre region)
- Ventes / Stock aliments (validation robuste)
- Avances (deduction auto sur facture)
- Facturation (dates debut/fin, impression Windows)
- Agrements + alertes tableau de bord
- Expeditions vers laiteries
- Laiteries / Clients
- Parametres centre (en-tete facture)
- Mon Compte (changer user / mot de passe)
- Exports CSV

COMPILATION EN .EXE (Windows 7+)
--------------------------------
Voir le fichier COMPILER.txt

Resume :
  1. Installer Python 3.6/3.7/3.8 32 bits
  2. Lancer build.bat
  3. Distributer le dossier dist\CentreCollecteLait\

COMPILATION GITHUB (exe automatique)
------------------------------------
Voir GITHUB.txt
Resume : pousser ce projet sur GitHub -> Actions -> telecharger l'artefact.
