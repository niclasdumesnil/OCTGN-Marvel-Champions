# -*- coding: utf-8 -*-
"""Vignettes orphelines : PNG de Sets\\*\\Cards\\ ne correspondant a aucune carte.

Cas d'usage : apres un rapprochement avec l'amont, une carte deplacee vers un
set agregateur change d'identifiant ; les PNG restes dans le pack (nommes par
identifiant) ne servent plus rien et doivent etre retires.

Lecons payees (2026-08-30, faux positifs Captain Britain) :
- extraire les ids avec un VRAI parseur XML, jamais une regex sur la ligne
  <card ...> (l'ordre des attributs varie d'un set a l'autre) ;
- retirer tout suffixe de face (.b a .j, faces alternates) du nom de fichier
  avant comparaison ;
- lancer le scan dans le checkout de la branche d'integration beta, pas dans
  un worktree base sur master : les dossiers Cards\\ fanmade n'existent que sur
  feature/lot1-pipeline-beta.

Code retour : 0 si aucune orpheline, 1 sinon (liste sur stdout).
Origine : Merlin - controle humain de l'etape 3 du rapprochement, outille.
"""
import os
import sys
import glob
import xml.etree.ElementTree as ET

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                      "055c536f-adba-4bc2-acbf-9aefb9756046", "Sets")


def ids_des_cartes(racine):
    ids = set()
    for chemin in glob.glob(os.path.join(racine, "*", "set.xml")):
        try:
            arbre = ET.parse(chemin)
        except ET.ParseError as exc:
            print("ERREUR de parsing XML : {} ({})".format(chemin, exc))
            sys.exit(2)
        for carte in arbre.getroot().iter("card"):
            cid = carte.get("id")
            if cid:
                ids.add(cid.lower())
    return ids


def vignettes_orphelines(racine, ids):
    orphelines = []
    for png in glob.glob(os.path.join(racine, "*", "Cards", "*.png")):
        guid = os.path.basename(png).lower().split(".")[0]
        if guid not in ids:
            orphelines.append(os.path.relpath(png, racine))
    return orphelines


def main():
    racine = os.path.normpath(RACINE)
    if not os.path.isdir(racine):
        print("Dossier Sets introuvable : {}".format(racine))
        return 2
    ids = ids_des_cartes(racine)
    orphelines = vignettes_orphelines(racine, ids)
    print("{} ids de cartes, {} vignette(s) orpheline(s)".format(len(ids), len(orphelines)))
    for o in orphelines:
        print("  {}".format(o))
    return 1 if orphelines else 0


if __name__ == "__main__":
    sys.exit(main())
