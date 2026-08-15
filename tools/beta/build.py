#!/usr/bin/env python3
"""Pipeline de build de l'environnement bêta OCTGN Marvel Champions.

Ce script ne touche JAMAIS au dossier de définition officiel dans l'arbre de
travail : il le COPIE dans un répertoire de staging (tools/beta/dist/staging),
et c'est uniquement cette copie qui est réécrite (GUID, nom, version) puis
empaquetée en .o8g. master reste un miroir fidèle d'upstream ; le GUID bêta
ne vit que dans config.json et dans les artefacts générés sous dist/.

Usage :
    python tools/beta/build.py                  # équivalent à --dry-run
    python tools/beta/build.py --dry-run         # build complet dans dist/, rien hors du repo
    python tools/beta/build.py --install --yes-install
                                                  # build + copie vers GameDatabase local OCTGN

Stdlib uniquement (pas de dépendance externe).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

TOOLS_BETA_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_BETA_DIR.parent.parent
DIST_DIR = TOOLS_BETA_DIR / "dist"
STAGING_DIR = DIST_DIR / "staging"
CONFIG_PATH = TOOLS_BETA_DIR / "config.json"


class ErreurBuild(Exception):
    """Erreur de build attendue (message déjà clair pour l'utilisateur)."""


def charger_config() -> dict:
    if not CONFIG_PATH.exists():
        raise ErreurBuild(f"config introuvable : {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def calculer_version_beta(version_officielle: str, offset: int) -> str:
    """OCTGN exige 4 segments numériques. Schéma bêta = version officielle
    avec offset sur le dernier segment, pour ne jamais collisionner avec
    l'officiel (ex. 0.0.3.96 -> 0.0.3.1096 avec offset=1000)."""
    segments = version_officielle.split(".")
    if len(segments) != 4 or not all(s.isdigit() for s in segments):
        raise ErreurBuild(
            f"version officielle inattendue (4 segments numériques requis) : {version_officielle!r}"
        )
    segments[-1] = str(int(segments[-1]) + offset)
    return ".".join(segments)


def slugifier(nom: str) -> str:
    """Nom de fichier sûr à partir du nom bêta (ex. 'Marvel Champions (BETA)' -> 'Marvel_Champions_BETA')."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", nom).strip("_")
    return slug or "beta"


def copier_definition(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise ErreurBuild(f"dossier de définition source introuvable : {source}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def copier_sets_fanmade_additionnels(entrees: list, staging_sets_dir: Path) -> list[str]:
    """Copie des sets fanmade additionnels (hors du dossier de définition officiel)
    dans staging/Sets/. Liste vide pour l'instant (Lot 2)."""
    noms_copies: list[str] = []
    for entree in entrees:
        chemin_source = Path(entree["chemin_source"])
        if not chemin_source.is_absolute():
            chemin_source = (REPO_ROOT / chemin_source).resolve()
        nom = entree.get("nom") or chemin_source.name
        if not chemin_source.is_dir():
            raise ErreurBuild(f"set fanmade additionnel introuvable : {chemin_source}")
        destination = staging_sets_dir / nom
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(chemin_source, destination)
        noms_copies.append(nom)
    return noms_copies


def remplacer_guid_partout(racine: Path, guid_officiel: str, guid_beta: str):
    """Recherche exhaustive du GUID officiel dans tous les fichiers du staging
    (texte ET binaire, par prudence) et remplacement par le GUID bêta.

    Retourne (fichiers_texte_modifies, fichiers_binaires_touches) :
    - fichiers_texte_modifies : liste de (chemin_relatif, nb_occurrences)
    - fichiers_binaires_touches : liste de chemins relatifs (piège potentiel :
      un fichier binaire ne devrait normalement JAMAIS contenir un GUID en clair)
    """
    guid_officiel_b = guid_officiel.encode("ascii")
    guid_beta_b = guid_beta.encode("ascii")

    fichiers_texte_modifies: list[tuple[str, int]] = []
    fichiers_binaires_touches: list[str] = []

    for chemin in sorted(racine.rglob("*")):
        if not chemin.is_file():
            continue
        donnees = chemin.read_bytes()
        if guid_officiel_b not in donnees:
            continue

        rel = chemin.relative_to(racine).as_posix()
        try:
            texte = donnees.decode("utf-8")
        except UnicodeDecodeError:
            # Fichier binaire contenant quand même le GUID en clair : on le
            # corrige aussi (bytes bruts), mais ça mérite un signalement.
            chemin.write_bytes(donnees.replace(guid_officiel_b, guid_beta_b))
            fichiers_binaires_touches.append(rel)
            continue

        nb = texte.count(guid_officiel)
        texte_patche = texte.replace(guid_officiel, guid_beta)
        # Réécriture en UTF-8 sans BOM (les fichiers sources n'en ont pas).
        chemin.write_bytes(texte_patche.encode("utf-8"))
        fichiers_texte_modifies.append((rel, nb))

    return fichiers_texte_modifies, fichiers_binaires_touches


def patcher_definition_xml(definition_path: Path, nom_beta: str, version_beta: str) -> None:
    """Réécrit name= et version= sur la balise <game ...> de definition.xml.
    L'attribut id= est déjà traité par remplacer_guid_partout (même valeur
    que le GUID officiel remplacé partout)."""
    if not definition_path.exists():
        raise ErreurBuild(f"definition.xml introuvable après copie : {definition_path}")

    texte = definition_path.read_text(encoding="utf-8")
    match_tag = re.search(r"<game\b.*?>", texte, flags=re.DOTALL)
    if not match_tag:
        raise ErreurBuild("balise <game> introuvable dans definition.xml")

    tag = match_tag.group(0)

    tag, n_nom = re.subn(r'\bname="[^"]*"', lambda m: f'name="{nom_beta}"', tag, count=1)
    if n_nom != 1:
        raise ErreurBuild("attribut name= introuvable sur la balise <game>")

    tag, n_version = re.subn(r'\bversion="[^"]*"', lambda m: f'version="{version_beta}"', tag, count=1)
    if n_version != 1:
        raise ErreurBuild("attribut version= introuvable sur la balise <game>")

    texte_patche = texte[: match_tag.start()] + tag + texte[match_tag.end() :]
    definition_path.write_text(texte_patche, encoding="utf-8")


def compter_sets_sources(staging_sets_dir: Path) -> int:
    if not staging_sets_dir.is_dir():
        return 0
    return sum(1 for p in staging_sets_dir.iterdir() if p.is_dir() and (p / "set.xml").exists())


def empaqueter_o8g(staging_dir: Path, nom_beta: str, version_beta: str) -> Path:
    nom_fichier = f"{slugifier(nom_beta)}-{version_beta}.o8g"
    chemin_o8g = DIST_DIR / nom_fichier
    if chemin_o8g.exists():
        chemin_o8g.unlink()

    with zipfile.ZipFile(chemin_o8g, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for chemin in sorted(staging_dir.rglob("*")):
            if chemin.is_file():
                zf.write(chemin, arcname=chemin.relative_to(staging_dir).as_posix())

    return chemin_o8g


def installer_localement(staging_dir: Path, guid_beta: str) -> Path:
    """Copie le contenu du staging vers le GameDatabase local OCTGN.
    NE crée JAMAIS de jonction ImageDatabase ici (voir TODO ci-dessous)."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise ErreurBuild("variable d'environnement LOCALAPPDATA introuvable")

    destination = Path(local_appdata) / "Programs" / "OCTGN" / "Data" / "GameDatabase" / guid_beta
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(staging_dir, destination)

    # TODO (Lot 0 - spike jonction ImageDatabase, non fait dans ce lot) :
    # ne PAS créer de jonction/symlink vers ImageDatabase\<guid_officiel> pour
    # partager les images. Risque non dérisqué : une désinstallation du jeu
    # bêta (ou un nettoyage OCTGN) pourrait suivre la jonction et supprimer les
    # ~2 Go d'images du jeu officiel. Tant que le spike Lot 0 n'a pas validé un
    # mécanisme sûr (copie, hardlinks, jonction testée en désinstallation),
    # le jeu bêta n'aura pas d'images tant qu'on ne les copie pas explicitement.

    return destination


def construire(config: dict) -> dict:
    guid_officiel = config["guid_officiel"]
    guid_beta = config["guid_beta"]
    nom_beta = config["nom_beta"]
    offset = config["offset_version_dernier_segment"]
    dossier_source = REPO_ROOT / config["dossier_definition_source"]

    definition_source = dossier_source / "definition.xml"
    if not definition_source.exists():
        raise ErreurBuild(f"definition.xml introuvable dans la source : {definition_source}")
    texte_source = definition_source.read_text(encoding="utf-8")
    match_tag_source = re.search(r"<game\b.*?>", texte_source, flags=re.DOTALL)
    if not match_tag_source:
        raise ErreurBuild("balise <game> introuvable dans definition.xml source")
    match_version = re.search(r'\bversion="([^"]*)"', match_tag_source.group(0))
    if not match_version:
        raise ErreurBuild("impossible de lire la version officielle depuis definition.xml source")
    version_officielle = match_version.group(1)
    version_beta = calculer_version_beta(version_officielle, offset)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[1/6] copie {dossier_source} -> {STAGING_DIR}")
    copier_definition(dossier_source, STAGING_DIR)

    sets_fanmade = config.get("sets_fanmade_additionnels") or []
    if sets_fanmade:
        print(f"[2/6] copie de {len(sets_fanmade)} set(s) fanmade additionnel(s)")
        noms = copier_sets_fanmade_additionnels(sets_fanmade, STAGING_DIR / "Sets")
        for nom in noms:
            print(f"      + {nom}")
    else:
        print("[2/6] aucun set fanmade additionnel configuré")

    print(f"[3/6] remplacement exhaustif du GUID officiel ({guid_officiel} -> {guid_beta})")
    fichiers_texte, fichiers_binaires = remplacer_guid_partout(STAGING_DIR, guid_officiel, guid_beta)
    for rel, nb in fichiers_texte:
        print(f"      {rel} ({nb} occurrence(s))")
    if fichiers_binaires:
        print("      /!\\ GUID trouvé dans des fichiers BINAIRES (corrigé, à vérifier) :")
        for rel in fichiers_binaires:
            print(f"      /!\\ {rel}")

    print(f"[4/6] patch definition.xml : name -> {nom_beta!r}, version -> {version_beta!r}")
    patcher_definition_xml(STAGING_DIR / "definition.xml", nom_beta, version_beta)

    nb_sets_sources = compter_sets_sources(STAGING_DIR / "Sets")
    set_xml_touches = [f for f, _ in fichiers_texte if re.match(r"^Sets/[^/]+/set\.xml$", f)]
    print(f"[5/6] sets patchés (gameId) : {len(set_xml_touches)}/{nb_sets_sources}")
    if len(set_xml_touches) != nb_sets_sources:
        print("      /!\\ décompte incohérent : tous les set.xml n'ont pas été patchés")

    print("[6/6] empaquetage .o8g")
    chemin_o8g = empaqueter_o8g(STAGING_DIR, nom_beta, version_beta)
    taille_ko = chemin_o8g.stat().st_size / 1024
    print(f"      -> {chemin_o8g} ({taille_ko:.0f} Ko)")

    hors_set_xml = [f for f, _ in fichiers_texte if not re.match(r"^Sets/[^/]+/set\.xml$", f)]

    return {
        "version_officielle": version_officielle,
        "version_beta": version_beta,
        "chemin_o8g": chemin_o8g,
        "nb_sets_patches": len(set_xml_touches),
        "nb_sets_sources": nb_sets_sources,
        "fichiers_hors_set_xml": hors_set_xml,
        "fichiers_binaires_touches": fichiers_binaires,
    }


def analyser_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build de l'environnement bêta OCTGN Marvel Champions.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build complet dans tools/beta/dist/ uniquement (comportement par défaut, aucune action hors du repo)",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="copie le build vers %%LOCALAPPDATA%%\\Programs\\OCTGN\\Data\\GameDatabase\\<guid_beta>\\ (requiert --yes-install)",
    )
    parser.add_argument(
        "--yes-install",
        action="store_true",
        help="confirme explicitement l'installation locale (sans ça, --install est refusé)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = analyser_arguments(argv)

    try:
        config = charger_config()
        resultat = construire(config)
    except ErreurBuild as e:
        print(f"ERREUR : {e}", file=sys.stderr)
        return 1

    if args.install:
        if not args.yes_install:
            print(
                "ERREUR : --install refusé sans --yes-install explicite "
                "(le spike Lot 0 n'a pas encore validé l'installation).",
                file=sys.stderr,
            )
            return 1
        print("[install] copie vers le GameDatabase local OCTGN...")
        destination = installer_localement(STAGING_DIR, config["guid_beta"])
        print(f"[install] -> {destination}")
    else:
        print("[dry-run] build terminé dans tools/beta/dist/, aucune action hors du repo.")

    print(
        f"\nrésumé : version {resultat['version_officielle']} -> {resultat['version_beta']} | "
        f"sets patchés {resultat['nb_sets_patches']}/{resultat['nb_sets_sources']} | "
        f"fichiers hors set.xml touchés {len(resultat['fichiers_hors_set_xml'])} "
        f"({', '.join(resultat['fichiers_hors_set_xml']) or '-'}) | "
        f"o8g : {resultat['chemin_o8g'].name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
