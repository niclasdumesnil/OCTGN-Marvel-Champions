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
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

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


def calculer_version_beta(version_officielle: str, multiplicateur: int, revision: int) -> str:
    """OCTGN exige 4 segments numériques.

    Dernier segment bêta = officiel * multiplicateur + revision.
    Ex. 0.0.3.96, multiplicateur 1000 : révision 0 -> 0.0.3.96000,
    révision 1 -> 0.0.3.96001, et l'officiel suivant (97) -> 0.0.3.97000.

    Le multiplicateur garantit qu'aucun numéro bêta ne peut égaler un numéro
    officiel. La révision permet de publier plusieurs builds bêta sur une même
    base officielle : sans elle, deux builds porteraient le même numéro et
    OCTGN ne proposerait aucune mise à jour aux testeurs.
    """
    segments = version_officielle.split(".")
    if len(segments) != 4 or not all(s.isdigit() for s in segments):
        raise ErreurBuild(
            f"version officielle inattendue (4 segments numériques requis) : {version_officielle!r}"
        )
    if not 0 <= revision < multiplicateur:
        raise ErreurBuild(
            f"revision_beta ({revision}) doit être entre 0 et {multiplicateur - 1} "
            "(au-delà, elle empiéterait sur la version officielle suivante)"
        )
    segments[-1] = str(int(segments[-1]) * multiplicateur + revision)
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


def copier_un_set(chemin_source: Path, nom: str, staging_sets_dir: Path) -> None:
    destination = staging_sets_dir / nom
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(chemin_source, destination)


def copier_sets_fanmade_additionnels(entrees: list, staging_sets_dir: Path) -> list[str]:
    """Copie des sets déclarés un par un dans `sets_fanmade_additionnels`.

    Réservé aux cas particuliers : set hors des dossiers Nexus, ou dont on veut
    forcer le nom dans le staging. Le cas courant passe par
    `dossiers_sets_supplementaires` ci-dessous.
    """
    noms_copies: list[str] = []
    for entree in entrees:
        chemin_source = Path(entree["chemin_source"])
        if not chemin_source.is_absolute():
            chemin_source = (REPO_ROOT / chemin_source).resolve()
        nom = entree.get("nom") or chemin_source.name
        if not chemin_source.is_dir():
            raise ErreurBuild(f"set fanmade additionnel introuvable : {chemin_source}")
        copier_un_set(chemin_source, nom, staging_sets_dir)
        noms_copies.append(nom)
    return noms_copies


def copier_dossiers_sets(dossiers: list, staging_sets_dir: Path) -> list[str]:
    """Prend TOUS les sets présents dans les dossiers configurés.

    Chaque sous-dossier contenant un `set.xml` devient un set du build — ajouter
    un set à la bêta ne demande alors aucune configuration : il suffit que Nexus
    le génère au bon endroit (voir le contrat de génération, dossier
    `…\\produits\\octgn-sets\\<pack_name>\\set.xml`).

    Le nom du dossier source est repris tel quel dans le staging ; c'est sans
    conséquence sur le module produit, o8build renommant les dossiers de sets
    par leur GUID à l'empaquetage.
    """
    noms_copies: list[str] = []
    for dossier in dossiers:
        racine = Path(dossier)
        if not racine.is_absolute():
            racine = (REPO_ROOT / racine).resolve()
        if not racine.is_dir():
            raise ErreurBuild(f"dossier de sets supplémentaires introuvable : {racine}")
        for candidat in sorted(racine.iterdir()):
            if not candidat.is_dir():
                continue
            if not (candidat / "set.xml").exists():
                print(f"      /!\\ ignoré (pas de set.xml) : {candidat.name}")
                continue
            copier_un_set(candidat, candidat.name, staging_sets_dir)
            noms_copies.append(candidat.name)
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


def patcher_definition_xml(
    definition_path: Path,
    nom_beta: str,
    version_beta: str,
    attributs_supplementaires: dict | None = None,
) -> list[str]:
    """Réécrit name=, version= et les attributs configurés sur la balise <game>.

    L'attribut id= est déjà traité par remplacer_guid_partout (même valeur que
    le GUID officiel remplacé partout). `attributs_supplementaires` permet de
    surcharger tout autre attribut de <game> (authors, description, tags,
    gameurl, setsurl, iconurl…) depuis config.json ; un attribut absent de la
    balise source est ajouté. Retourne la liste des attributs surchargés.
    """
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

    surcharges: list[str] = []
    for attribut, valeur in (attributs_supplementaires or {}).items():
        if attribut in ("name", "version", "id"):
            raise ErreurBuild(
                f"attribut {attribut!r} interdit dans attributs_definition "
                "(géré par le pipeline : nom_beta, offset de version, GUID)"
            )
        echappee = escape(str(valeur), {'"': "&quot;"})
        tag, n = re.subn(rf'\b{re.escape(attribut)}="[^"]*"', lambda m: f'{attribut}="{echappee}"', tag, count=1)
        if n == 0:
            # attribut absent de la source : on l'ajoute avant le > final
            tag = tag.rstrip()[:-1].rstrip() + f'\n    {attribut}="{echappee}">'
        surcharges.append(attribut)

    texte_patche = texte[: match_tag.start()] + tag + texte[match_tag.end() :]
    definition_path.write_text(texte_patche, encoding="utf-8")
    return surcharges


def remplacer_fichiers(staging_dir: Path, remplacements: dict | None) -> list[str]:
    """Écrase des fichiers du staging par des variantes bêta versionnées.

    Sert à signer visuellement le module (dos de cartes badgés « BETA », vus en
    permanence en partie). Clés = chemins relatifs au staging, valeurs = chemins
    relatifs à tools/beta/. Le fichier cible doit exister : remplacer un chemin
    absent signalerait une source qui a bougé chez upstream.
    """
    faits: list[str] = []
    for cible_rel, source_rel in (remplacements or {}).items():
        source = TOOLS_BETA_DIR / source_rel
        cible = staging_dir / cible_rel
        if not source.exists():
            raise ErreurBuild(f"fichier de remplacement introuvable : {source}")
        if not cible.exists():
            raise ErreurBuild(
                f"cible de remplacement absente du staging : {cible_rel} "
                "(upstream a-t-il renommé ou supprimé ce fichier ?)"
            )
        shutil.copy2(source, cible)
        faits.append(cible_rel)
    return faits


def compter_sets_sources(staging_sets_dir: Path) -> int:
    if not staging_sets_dir.is_dir():
        return 0
    return sum(1 for p in staging_sets_dir.iterdir() if p.is_dir() and (p / "set.xml").exists())


def chemin_o8build() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise ErreurBuild("variable d'environnement LOCALAPPDATA introuvable")
    return Path(local_appdata) / "Programs" / "OCTGN" / "o8build.exe"


def empaqueter_nupkg(staging_dir: Path, installer_dans_le_feed: bool = False) -> Path:
    """Empaquetage par l'outil officiel OCTGN.

    o8build valide le jeu (7 tests) puis produit le .nupkg dans le staging.
    C'est le seul format que le client OCTGN sait consommer : la définition y
    est placée sous def/, avec nuspec et métadonnées NuGet — une archive zippée
    à la main, contenu à la racine, ne convient pas.
    """
    o8build = chemin_o8build()
    if not o8build.exists():
        raise ErreurBuild(
            f"o8build.exe introuvable ({o8build}). "
            "Installer OCTGN, ou ajuster le chemin."
        )

    for ancien in staging_dir.glob("*.nupkg"):
        ancien.unlink()

    commande = [str(o8build), "-d", str(staging_dir)]
    if installer_dans_le_feed:
        commande.append("-i")
    resultat = subprocess.run(commande, capture_output=True, text=True)
    if resultat.returncode != 0:
        raise ErreurBuild(
            f"o8build a échoué (code {resultat.returncode}) :\n{resultat.stdout}\n{resultat.stderr}"
        )

    produits = list(staging_dir.glob("*.nupkg"))
    if not produits:
        raise ErreurBuild("o8build n'a produit aucun .nupkg")

    destination = DIST_DIR / produits[0].name
    if destination.exists():
        destination.unlink()
    shutil.move(str(produits[0]), str(destination))
    return destination


def empaqueter_o8g(staging_dir: Path, nom_beta: str, version_beta: str) -> Path:
    """Archive .o8g pour téléchargement direct (canal de repli du feed).

    Contenu à la racine, comme le dossier de définition. Non validé comme
    format d'installation OCTGN : le canal fiable est le .nupkg ci-dessus.
    """
    nom_fichier = f"{slugifier(nom_beta)}-{version_beta}.o8g"
    chemin_o8g = DIST_DIR / nom_fichier
    if chemin_o8g.exists():
        chemin_o8g.unlink()

    with zipfile.ZipFile(chemin_o8g, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for chemin in sorted(staging_dir.rglob("*")):
            if chemin.is_file() and chemin.suffix != ".nupkg":
                zf.write(chemin, arcname=chemin.relative_to(staging_dir).as_posix())

    return chemin_o8g


def installer_localement(staging_dir: Path, guid_beta: str) -> Path:
    """Installe le paquet bêta dans le feed local d'OCTGN (o8build -i).

    Le module s'installe ensuite depuis le Games Manager. On ne copie plus
    directement dans GameDatabase : passer par le feed est le circuit natif,
    et c'est celui que les testeurs utiliseront.

    La jonction ImageDatabase n'est volontairement pas créée ici. Le spike du
    Lot 0 (2026-08-15) a montré qu'aucune API de suppression standard
    (PowerShell, cmd, .NET) ne traverse une jonction : la créer est sans danger
    pour les ~2 Go d'images officielles. Mais elle reste un geste
    d'environnement, pas de build — elle appartient à la procédure
    d'installation testeur, à terme au module lui-même à son premier lancement.
    """
    return empaqueter_nupkg(staging_dir, installer_dans_le_feed=True)


def construire(config: dict) -> dict:
    guid_officiel = config["guid_officiel"]
    guid_beta = config["guid_beta"]
    nom_beta = config["nom_beta"]
    multiplicateur = config["multiplicateur_version_beta"]
    revision = config.get("revision_beta", 0)
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
    version_beta = calculer_version_beta(version_officielle, multiplicateur, revision)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[1/6] copie {dossier_source} -> {STAGING_DIR}")
    copier_definition(dossier_source, STAGING_DIR)

    dossiers_sets = config.get("dossiers_sets_supplementaires") or []
    sets_fanmade = config.get("sets_fanmade_additionnels") or []
    noms_ajoutes: list[str] = []
    if dossiers_sets or sets_fanmade:
        print("[2/6] sets supplémentaires")
        noms_ajoutes += copier_dossiers_sets(dossiers_sets, STAGING_DIR / "Sets")
        noms_ajoutes += copier_sets_fanmade_additionnels(sets_fanmade, STAGING_DIR / "Sets")
        for nom in noms_ajoutes:
            print(f"      + {nom}")
        print(f"      {len(noms_ajoutes)} set(s) ajouté(s)")
    else:
        print("[2/6] aucun set supplémentaire configuré")

    print(f"[3/6] remplacement exhaustif du GUID officiel ({guid_officiel} -> {guid_beta})")
    fichiers_texte, fichiers_binaires = remplacer_guid_partout(STAGING_DIR, guid_officiel, guid_beta)
    for rel, nb in fichiers_texte:
        print(f"      {rel} ({nb} occurrence(s))")
    if fichiers_binaires:
        print("      /!\\ GUID trouvé dans des fichiers BINAIRES (corrigé, à vérifier) :")
        for rel in fichiers_binaires:
            print(f"      /!\\ {rel}")

    print(f"[4/6] patch definition.xml : name -> {nom_beta!r}, version -> {version_beta!r}")
    surcharges = patcher_definition_xml(
        STAGING_DIR / "definition.xml",
        nom_beta,
        version_beta,
        config.get("attributs_definition"),
    )
    if surcharges:
        print(f"      attributs surchargés : {', '.join(surcharges)}")

    remplaces = remplacer_fichiers(STAGING_DIR, config.get("fichiers_remplaces"))
    if remplaces:
        print(f"      fichiers remplacés : {', '.join(remplaces)}")

    nb_sets_sources = compter_sets_sources(STAGING_DIR / "Sets")
    set_xml_touches = [f for f, _ in fichiers_texte if re.match(r"^Sets/[^/]+/set\.xml$", f)]
    print(f"[5/6] sets patchés (gameId) : {len(set_xml_touches)}/{nb_sets_sources}")
    if len(set_xml_touches) != nb_sets_sources:
        print("      /!\\ décompte incohérent : tous les set.xml n'ont pas été patchés")

    print("[6/6] empaquetage")
    chemin_nupkg = empaqueter_nupkg(STAGING_DIR)
    print(f"      -> {chemin_nupkg.name} ({chemin_nupkg.stat().st_size / 1024:.0f} Ko, validé par o8build)")
    chemin_o8g = empaqueter_o8g(STAGING_DIR, nom_beta, version_beta)
    print(f"      -> {chemin_o8g.name} ({chemin_o8g.stat().st_size / 1024:.0f} Ko, téléchargement direct)")

    hors_set_xml = [f for f, _ in fichiers_texte if not re.match(r"^Sets/[^/]+/set\.xml$", f)]

    return {
        "version_officielle": version_officielle,
        "version_beta": version_beta,
        "chemin_nupkg": chemin_nupkg,
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
        help="installe le paquet dans le feed local d'OCTGN, d'où le Games Manager l'installe (requiert --yes-install)",
    )
    parser.add_argument(
        "--yes-install",
        action="store_true",
        help="confirme explicitement l'installation dans le feed local (sans ça, --install est refusé)",
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
                "(il écrit dans le feed local d'OCTGN, hors du repo).",
                file=sys.stderr,
            )
            return 1
        print("[install] installation dans le feed local d'OCTGN...")
        destination = installer_localement(STAGING_DIR, config["guid_beta"])
        print(f"[install] -> {destination.name} ; installer le module depuis le Games Manager.")
    else:
        print("[dry-run] build terminé dans tools/beta/dist/, aucune action hors du repo.")

    print(
        f"\nrésumé : version {resultat['version_officielle']} -> {resultat['version_beta']} | "
        f"sets patchés {resultat['nb_sets_patches']}/{resultat['nb_sets_sources']} | "
        f"fichiers hors set.xml touchés {len(resultat['fichiers_hors_set_xml'])} "
        f"({', '.join(resultat['fichiers_hors_set_xml']) or '-'}) | "
        f"nupkg : {resultat['chemin_nupkg'].name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
