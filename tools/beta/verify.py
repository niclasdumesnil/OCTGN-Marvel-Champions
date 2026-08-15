#!/usr/bin/env python3
"""Vérification du .o8g bêta produit par build.py.

Contrôles effectués :
- l'archive .o8g s'ouvre proprement (zip valide, pas de fichier corrompu) ;
- plus AUCUNE occurrence du GUID officiel nulle part dans l'archive ;
- definition.xml porte le bon id / name / version bêta ;
- nombre de Sets/*/set.xml portant le bon gameId == nombre de sets sources
  (comptés dans le dossier de définition source, avant build).

Sortie : rapport lisible sur stdout. Code retour 0 si tout est vert, 1 sinon.

Usage :
    python tools/beta/verify.py                  # vérifie le .o8g le plus récent de dist/
    python tools/beta/verify.py --o8g chemin.o8g  # vérifie un .o8g précis
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

TOOLS_BETA_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_BETA_DIR.parent.parent
DIST_DIR = TOOLS_BETA_DIR / "dist"
CONFIG_PATH = TOOLS_BETA_DIR / "config.json"


def charger_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def trouver_o8g_le_plus_recent():
    candidats = sorted(DIST_DIR.glob("*.o8g"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidats[0] if candidats else None


def compter_sets_sources(config: dict) -> int:
    sets_dir = REPO_ROOT / config["dossier_definition_source"] / "Sets"
    if not sets_dir.is_dir():
        return 0
    return sum(1 for p in sets_dir.iterdir() if p.is_dir() and (p / "set.xml").exists())


def verifier(chemin_o8g: Path, config: dict):
    problemes: list[str] = []
    guid_officiel = config["guid_officiel"]
    guid_beta = config["guid_beta"]
    nom_beta = config["nom_beta"]

    try:
        zf = zipfile.ZipFile(chemin_o8g, "r")
    except zipfile.BadZipFile as e:
        return False, [f"archive .o8g corrompue ou invalide : {e}"]

    with zf:
        mauvais = zf.testzip()
        if mauvais is not None:
            problemes.append(f"fichier corrompu dans l'archive : {mauvais}")

        noms = zf.namelist()
        if "definition.xml" not in noms:
            problemes.append("definition.xml absent de la racine de l'archive")

        guid_officiel_b = guid_officiel.encode("ascii")
        occurrences_residuelles: list[str] = []
        set_xml_ok = 0
        set_xml_ko: list[str] = []

        for nom in noms:
            donnees = zf.read(nom)
            if guid_officiel_b in donnees:
                occurrences_residuelles.append(nom)
            if re.match(r"^Sets/[^/]+/set\.xml$", nom):
                try:
                    texte = donnees.decode("utf-8")
                except UnicodeDecodeError:
                    set_xml_ko.append(nom)
                    continue
                if f'gameId="{guid_beta}"' in texte:
                    set_xml_ok += 1
                else:
                    set_xml_ko.append(nom)

        if occurrences_residuelles:
            problemes.append(
                f"GUID officiel encore présent dans {len(occurrences_residuelles)} fichier(s) : "
                + ", ".join(occurrences_residuelles)
            )

        nb_sources = compter_sets_sources(config)
        if set_xml_ok != nb_sources:
            problemes.append(
                f"sets patchés incohérents : {set_xml_ok} set.xml corrects sur {nb_sources} sources "
                f"(en échec : {', '.join(set_xml_ko) or '-'})"
            )

        if "definition.xml" in noms:
            texte_def = zf.read("definition.xml").decode("utf-8")
            match_tag = re.search(r"<game\b.*?>", texte_def, flags=re.DOTALL)
            if not match_tag:
                problemes.append("balise <game> introuvable dans definition.xml de l'archive")
            else:
                tag = match_tag.group(0)
                if f'id="{guid_beta}"' not in tag:
                    problemes.append("definition.xml : id= ne correspond pas au GUID bêta")
                if f'name="{nom_beta}"' not in tag:
                    problemes.append("definition.xml : name= ne correspond pas au nom bêta configuré")
                match_version = re.search(r'\bversion="([^"]*)"', tag)
                if not match_version:
                    problemes.append("definition.xml : attribut version= introuvable")
                else:
                    version_archive = match_version.group(1)
                    offset = config["offset_version_dernier_segment"]
                    segments = version_archive.split(".")
                    if len(segments) != 4 or not all(s.isdigit() for s in segments):
                        problemes.append(f"definition.xml : version= mal formée : {version_archive!r}")
                    elif int(segments[-1]) < offset:
                        problemes.append(
                            f"definition.xml : dernier segment de version ({segments[-1]}) "
                            f"inférieur à l'offset bêta attendu ({offset}) — collision possible avec l'officiel"
                        )

    return (len(problemes) == 0), problemes


def analyser_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vérifie un .o8g bêta produit par build.py.")
    parser.add_argument(
        "--o8g", type=Path, default=None, help="chemin du .o8g à vérifier (défaut : le plus récent dans dist/)"
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = analyser_arguments(argv)
    config = charger_config()

    chemin_o8g = args.o8g or trouver_o8g_le_plus_recent()
    if chemin_o8g is None or not chemin_o8g.exists():
        print("ERREUR : aucun .o8g trouvé dans tools/beta/dist/ (lancez build.py d'abord).", file=sys.stderr)
        return 1

    print(f"vérification de {chemin_o8g}")
    ok, problemes = verifier(chemin_o8g, config)

    if ok:
        print("OK : GUID officiel absent, definition.xml conforme, sets patchés au complet, archive saine.")
        return 0

    print("ÉCHEC :")
    for p in problemes:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
