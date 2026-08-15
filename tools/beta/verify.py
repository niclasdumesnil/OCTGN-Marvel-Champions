#!/usr/bin/env python3
"""Vérification des artefacts bêta produits par build.py.

Deux artefacts sont contrôlés :
- le .nupkg (produit par o8build), qui est le format réellement consommé par
  OCTGN : la définition y vit sous def/ ;
- le .o8g (archive de téléchargement direct), contenu à la racine.

Contrôles effectués sur chacun :
- l'archive s'ouvre proprement (zip valide, pas de fichier corrompu) ;
- plus AUCUNE occurrence du GUID officiel nulle part dans l'archive ;
- definition.xml porte le bon id / name / version bêta ;
- nombre de Sets/*/set.xml portant le bon gameId == nombre de sets sources
  (comptés dans le dossier de définition source, avant build).

Sortie : rapport lisible sur stdout. Code retour 0 si tout est vert, 1 sinon.

Usage :
    python tools/beta/verify.py                     # vérifie les artefacts les plus récents de dist/
    python tools/beta/verify.py --o8g chemin.o8g    # vérifie un .o8g précis
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


def trouver_le_plus_recent(motif: str):
    candidats = sorted(DIST_DIR.glob(motif), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidats[0] if candidats else None


def compter_sets_dans(racine: Path) -> int:
    if not racine.is_dir():
        return 0
    return sum(1 for p in racine.iterdir() if p.is_dir() and (p / "set.xml").exists())


def compter_sets_sources(config: dict) -> int:
    """Nombre de sets attendus dans l'archive : ceux du dossier de définition,
    plus les sets supplémentaires (dossiers Nexus + entrées explicites) que
    build.py injecte dans le staging. Sans eux, la vérification signalerait à
    tort un décompte incohérent dès qu'un set fanmade entre dans le build."""
    total = compter_sets_dans(REPO_ROOT / config["dossier_definition_source"] / "Sets")

    for dossier in config.get("dossiers_sets_supplementaires") or []:
        racine = Path(dossier)
        if not racine.is_absolute():
            racine = (REPO_ROOT / racine).resolve()
        total += compter_sets_dans(racine)

    for entree in config.get("sets_fanmade_additionnels") or []:
        chemin = Path(entree["chemin_source"])
        if not chemin.is_absolute():
            chemin = (REPO_ROOT / chemin).resolve()
        if (chemin / "set.xml").exists():
            total += 1

    return total


def verifier(chemin_archive: Path, config: dict, prefixe: str = ""):
    """Vérifie une archive bêta. `prefixe` situe la définition dans l'archive :
    "" pour un .o8g (contenu à la racine), "def/" pour un .nupkg."""
    problemes: list[str] = []
    guid_officiel = config["guid_officiel"]
    guid_beta = config["guid_beta"]
    nom_beta = config["nom_beta"]
    chemin_definition = f"{prefixe}definition.xml"
    motif_set_xml = rf"^{re.escape(prefixe)}Sets/[^/]+/set\.xml$"

    try:
        zf = zipfile.ZipFile(chemin_archive, "r")
    except zipfile.BadZipFile as e:
        return False, [f"archive corrompue ou invalide : {e}"]

    with zf:
        mauvais = zf.testzip()
        if mauvais is not None:
            problemes.append(f"fichier corrompu dans l'archive : {mauvais}")

        noms = zf.namelist()
        if chemin_definition not in noms:
            problemes.append(f"{chemin_definition} absent de l'archive")

        guid_officiel_b = guid_officiel.encode("ascii")
        occurrences_residuelles: list[str] = []
        set_xml_ok = 0
        set_xml_ko: list[str] = []

        for nom in noms:
            donnees = zf.read(nom)
            if guid_officiel_b in donnees:
                occurrences_residuelles.append(nom)
            if re.match(motif_set_xml, nom):
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

        if chemin_definition in noms:
            texte_def = zf.read(chemin_definition).decode("utf-8")
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
                    multiplicateur = config["multiplicateur_version_beta"]
                    revision = config.get("revision_beta", 0)
                    segments = version_archive.split(".")
                    if len(segments) != 4 or not all(s.isdigit() for s in segments):
                        problemes.append(f"definition.xml : version= mal formée : {version_archive!r}")
                    else:
                        dernier = int(segments[-1])
                        if dernier % multiplicateur != revision:
                            problemes.append(
                                f"definition.xml : dernier segment de version ({dernier}) incohérent "
                                f"avec revision_beta={revision} (multiplicateur {multiplicateur})"
                            )
                        if dernier // multiplicateur == 0:
                            problemes.append(
                                f"definition.xml : dernier segment de version ({dernier}) trop bas — "
                                "collision possible avec une version officielle"
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

    if args.o8g:
        cibles = [(args.o8g, "")]
    else:
        cibles = []
        nupkg = trouver_le_plus_recent("*.nupkg")
        if nupkg:
            cibles.append((nupkg, "def/"))
        o8g = trouver_le_plus_recent("*.o8g")
        if o8g:
            cibles.append((o8g, ""))

    if not cibles or not all(c.exists() for c, _ in cibles):
        print("ERREUR : aucun artefact trouvé dans tools/beta/dist/ (lancez build.py d'abord).", file=sys.stderr)
        return 1

    tout_vert = True
    for chemin, prefixe in cibles:
        print(f"vérification de {chemin.name}")
        ok, problemes = verifier(chemin, config, prefixe)
        if ok:
            print("  OK : GUID officiel absent, definition.xml conforme, sets patchés au complet, archive saine.")
        else:
            tout_vert = False
            print("  ÉCHEC :")
            for p in problemes:
                print(f"    - {p}")

    return 0 if tout_vert else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
