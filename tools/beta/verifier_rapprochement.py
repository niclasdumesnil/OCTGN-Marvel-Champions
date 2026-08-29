#!/usr/bin/env python3
"""Contrôles de cohérence données/moteur, à lancer après chaque rapprochement upstream.

Contexte : Ourob09 réorganise les cartes de mise en place officielles — il les
sort des packs pour les ranger dans les pseudo-sets agrégateurs (Hero_Setup,
Villain_Setup, Encounter_Setup), avec de NOUVEAUX identifiants. Ce déplacement
ne produit aucun conflit git : les trois casses possibles sont sémantiques et
silencieuses. Ce script les rend bruyantes.

Contrôles :

1. DOUBLONS — aucune paire (Type, Name) ni (Type, Owner) dupliquée parmi les
   cartes de mise en place. C'est le piège du merge : l'amont AJOUTE une carte
   à l'agrégateur pendant que notre branche garde (ou régénère) la même dans le
   pack ; pas de conflit textuel, mais le héros apparaît deux fois dans la
   fenêtre de sélection.

2. DISPATCH PAR NOM — chaque libellé comparé en dur par le moteur
   (`vName == '...'` dans setup.py, `villainName == '...'` dans loadModular.py)
   doit exister comme Name d'une carte de mise en place. Un renommage côté
   données fait sinon retomber le scénario sur la mise en place générique,
   sans message (couplage payé au lot « libellé des sets », 2026-08-28).

3. DISPATCH PAR SLUG — chaque slug comparé à `heroPlayed` (loadHero.py) doit
   exister comme Owner d'une carte. Même mécanique de casse silencieuse.

4. PROPRIÉTÉ nbUnderling — les scénarios de Fear No Evil qui se jouent contre
   un sous-fifre doivent garder leur propriété : sans elle, le choix du
   sous-fifre disparaît et le scénario charge sans vilain.

Sortie : rapport lisible, code retour 0 si tout est vert, 1 sinon.

Usage :
    python tools/beta/verifier_rapprochement.py
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

TOOLS_BETA_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_BETA_DIR.parent.parent
GAME_DIR = REPO_ROOT / "055c536f-adba-4bc2-acbf-9aefb9756046"
SETS_DIR = GAME_DIR / "Sets"
SCRIPTS_DIR = GAME_DIR / "scripts"

# Les scénarios dont la mise en place repose sur nbUnderling (Fear No Evil :
# le scénario est séparé de son vilain, choisi ensuite parmi les sous-fifres).
# Liste figée volontairement : c'est exactement ce qui doit SURVIVRE au
# déplacement des setups vers les agrégateurs. Un nouveau scénario à sous-fifre
# s'ajoute ici en même temps que sa donnée.
SETUPS_A_SOUS_FIFRE = [
    "Protection Racket",
    "Stop The Presses!",
    "Art Museum Heist",
    "The Getaway",
    "The Raft Breakout",
]


def collecter_setups() -> list[dict]:
    """Toutes les cartes de mise en place du dépôt (Type se terminant par 'setup')."""
    setups = []
    for set_xml in sorted(SETS_DIR.glob("*/set.xml")):
        try:
            racine = ET.parse(set_xml).getroot()
        except ET.ParseError as e:
            print(f"  !! {set_xml.parent.name} : XML invalide ({e})")
            continue
        for carte in racine.iter("card"):
            props = {p.get("name"): (p.get("value") if p.get("value") is not None else (p.text or ""))
                     for p in carte.findall("property")}
            type_ = props.get("Type", "")
            if type_.endswith("setup"):
                setups.append({
                    "set": set_xml.parent.name,
                    "nom": carte.get("name") or "",
                    "type": type_,
                    "owner": props.get("Owner", ""),
                    "props": props,
                })
    return setups


def owners_et_noms_connus() -> tuple[set, set]:
    """Tous les Owners et tous les Names de cartes du dépôt (setup ou non)."""
    owners, noms = set(), set()
    for set_xml in SETS_DIR.glob("*/set.xml"):
        try:
            racine = ET.parse(set_xml).getroot()
        except ET.ParseError:
            continue
        for carte in racine.iter("card"):
            noms.add(carte.get("name") or "")
            for p in carte.findall("property"):
                if p.get("name") == "Owner":
                    owners.add(p.get("value") or "")
            for alt in carte.findall("alternate"):
                noms.add(alt.get("name") or "")
    return owners, noms


def litteraux_compares(fichier: Path, variable: str) -> set:
    """Chaînes comparées à `variable` par == dans un script du moteur."""
    texte = fichier.read_text(encoding="utf-8", errors="replace")
    litteraux = set()
    for m in re.finditer(rf"{variable}\s*==\s*(['\"])(.+?)\1", texte):
        litteraux.add(m.group(2))
    return litteraux


def main() -> int:
    erreurs = 0

    setups = collecter_setups()
    print(f"{len(setups)} cartes de mise en place dans {len(set(s['set'] for s in setups))} sets.")

    # ── 1. Doublons ──────────────────────────────────────────────────────────
    print("\n[1/4] doublons de mise en place")
    for cle in ("nom", "owner"):
        vus = defaultdict(list)
        for s in setups:
            if s[cle]:
                vus[(s["type"], s[cle])].append(s["set"])
        doublons = {k: v for k, v in vus.items() if len(v) > 1}
        if doublons:
            erreurs += len(doublons)
            for (type_, valeur), ou in sorted(doublons.items()):
                print(f"  !! ({type_}, {cle}={valeur!r}) present dans : {', '.join(ou)}")
        else:
            print(f"      aucun doublon (Type, {cle.capitalize()})")

    # ── 2. Dispatch par nom ──────────────────────────────────────────────────
    print("\n[2/4] libellés du dispatch moteur -> cartes de mise en place")
    noms_setup = {s["nom"] for s in setups}
    attendus = set()
    attendus |= litteraux_compares(SCRIPTS_DIR / "setup.py", "vName")
    attendus |= litteraux_compares(SCRIPTS_DIR / "loadModular.py", "villainName")
    attendus |= litteraux_compares(SCRIPTS_DIR / "loadVillain.py", "villainName")
    manquants = sorted(n for n in attendus if n not in noms_setup)
    if manquants:
        erreurs += len(manquants)
        for n in manquants:
            print(f"  !! le moteur dispatche sur {n!r}, aucune carte de mise en place ne porte ce nom")
    else:
        print(f"      {len(attendus)} libellés dispatchés, tous portés par une carte de mise en place")

    # ── 3. Dispatch par slug (heroPlayed) ───────────────────────────────────
    print("\n[3/4] slugs du dispatch héros -> Owners connus")
    owners, _ = owners_et_noms_connus()
    slugs = litteraux_compares(SCRIPTS_DIR / "loadHero.py", "heroPlayed")
    slugs_manquants = sorted(s for s in slugs if s not in owners)
    if slugs_manquants:
        erreurs += len(slugs_manquants)
        for s in slugs_manquants:
            print(f"  !! heroSetup() dispatche sur {s!r}, aucun Owner de carte ne correspond")
    else:
        print(f"      {len(slugs)} slugs dispatchés, tous présents comme Owner")

    # ── 4. nbUnderling ───────────────────────────────────────────────────────
    print("\n[4/4] propriété nbUnderling des scénarios à sous-fifre")
    par_nom = {s["nom"]: s for s in setups if s["type"] == "villain_setup"}
    for nom in SETUPS_A_SOUS_FIFRE:
        carte = par_nom.get(nom)
        if carte is None:
            erreurs += 1
            print(f"  !! {nom!r} : aucune carte villain_setup ne porte ce nom")
        elif not carte["props"].get("nbUnderling", "").strip():
            erreurs += 1
            print(f"  !! {nom!r} ({carte['set']}) : propriété nbUnderling absente ou vide")
    if erreurs == 0:
        print(f"      {len(SETUPS_A_SOUS_FIFRE)} scénarios contrôlés, nbUnderling présent partout")

    print("\n" + ("TOUT EST VERT" if erreurs == 0 else f"{erreurs} PROBLEME(S) - rapprochement à corriger avant build"))
    return 0 if erreurs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
