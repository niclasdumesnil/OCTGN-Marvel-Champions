# Environnement bêta OCTGN Marvel Champions — Lot 1 (pipeline de build)

Pipeline reproductible qui construit une définition de jeu OCTGN **bêta**,
isolée du jeu **officiel** (GUID `055c536f-adba-4bc2-acbf-9aefb9756046`),
à partir de l'arbre de travail courant du fork.

## Principe

- `master` reste un miroir fidèle d'upstream : aucun fichier existant du repo
  n'est modifié par ce lot.
- Le GUID bêta ne vit **que** dans `tools/beta/config.json`. Le pipeline copie
  le dossier de définition officiel dans un répertoire de staging jetable
  (`tools/beta/dist/staging/`) et réécrit *cette copie* : GUID, nom, version.
- Le staging et les `.o8g` produits vont dans `tools/beta/dist/` (ignoré par
  git, voir `.gitignore`).

## Décisions de cadrage (rappel)

- **GUID bêta immuable** : `ecaf8a86-b551-4740-9fce-14d1e0899f72` (fourni par
  l'architecte, ne pas changer sans revalidation).
- **Nom bêta** : « Marvel Champions (BETA) », configurable dans `config.json`
  (deviendra peut-être « Merlin » plus tard).
- **Versionnage** : OCTGN exige 4 segments numériques. Schéma bêta = version
  officielle avec un offset sur le dernier segment (`offset_version_dernier_segment`
  dans `config.json`, actuellement 1000) pour ne jamais collisionner avec une
  version officielle future (ex. `0.0.3.96` → `0.0.3.1096`).

## Usage

```
python tools/beta/build.py                    # build dans dist/ uniquement (comportement par défaut)
python tools/beta/build.py --dry-run           # identique, explicite
python tools/beta/build.py --install --yes-install
                                                # build + copie vers le GameDatabase local OCTGN
python tools/beta/verify.py                    # vérifie le .o8g le plus récent de dist/
python tools/beta/verify.py --o8g chemin.o8g   # vérifie un .o8g précis
```

`--install` seul (sans `--yes-install`) est **refusé** : le spike Lot 0
n'a pas encore validé l'installation locale (voir Limites ci-dessous).

## Ce que fait `build.py`

1. Copie `055c536f-adba-4bc2-acbf-9aefb9756046/` (dossier de définition
   officiel, chemin configurable via `dossier_definition_source`) vers
   `tools/beta/dist/staging/`.
2. Copie les éventuels sets fanmade additionnels listés dans
   `sets_fanmade_additionnels` (vide pour l'instant — Lot 2).
3. Recherche **exhaustive** du GUID officiel dans tous les fichiers du
   staging (texte et, par prudence, binaire) et remplacement par le GUID
   bêta partout où il apparaît — pas seulement dans `definition.xml` et les
   `set.xml` (ex. `scripts/plugin.py`, `FanMade/OCTGN-Pack-Installer_V0.7.ps1`
   référencent aussi le GUID en dur). Chaque fichier touché est loggé avec
   son nombre d'occurrences.
4. Patch `name=` et `version=` sur la balise `<game>` de `definition.xml`
   (l'`id=` est déjà traité par l'étape 3, sa valeur étant identique au GUID
   officiel remplacé).
5. Compte et vérifie que le nombre de `Sets/*/set.xml` patchés (`gameId=`)
   correspond au nombre de dossiers de sets sources. L'attribut `id=` de
   chaque set n'est **pas** touché (ce sont des GUID de set, distincts du
   GUID de jeu).
6. Empaquette le staging en `.o8g` (zip standard, racine = contenu direct du
   staging, pas de dossier englobant) dans `tools/beta/dist/`, nommé
   `<nom_beta_slugifié>-<version_beta>.o8g`.

## Ce que fait `verify.py`

Ouvre le `.o8g` produit et vérifie : absence totale du GUID officiel dans
l'archive, conformité de `definition.xml` (id/name/version bêta), nombre de
`set.xml` patchés = nombre de sets sources, intégrité de l'archive zip.
Rapport lisible + code retour (0 = vert, 1 = échec).

## Limites de ce lot (Lot 1)

- **Pas de jonction `ImageDatabase`.** Le jeu bêta installé n'a donc pas
  d'images tant qu'elles ne sont pas copiées explicitement. Une jonction
  vers `ImageDatabase\<guid_officiel>` économiserait ~2 Go, mais le risque
  qu'une désinstallation du jeu bêta (ou un nettoyage OCTGN) suive la
  jonction et détruise les images officielles n'est **pas dérisqué**. Voir
  le TODO dans `build.py` (`installer_localement`).
- **Installation locale non validée.** `--install` est implémenté mais
  refuse de s'exécuter sans `--yes-install` : le spike Lot 0 (jonction,
  comportement d'OCTGN à la désinstallation) n'a pas encore eu lieu.

## Prochaines étapes

- **Lot 0** : spike dérisquage de la jonction `ImageDatabase` (comportement
  à la désinstallation, alternative hardlinks, etc.).
- **Lot 2** : sets fanmade additionnels (remplir
  `sets_fanmade_additionnels` dans `config.json`).
