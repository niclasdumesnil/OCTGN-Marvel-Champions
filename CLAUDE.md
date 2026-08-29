# OCTGN Marvel Champions — fork du mod communautaire

Module de jeu OCTGN pour Marvel Champions. **Ce dépôt n'est pas le nôtre** : c'est le mod
de la communauté, maintenu par **Ourob09** (`Ouroboros009/OCTGN-Marvel-Champions`), auquel
Merlin contribue. Tout ce qui suit découle de ce fait.

---

## 🎯 Domaine & rôle OS
- **Domaine OS** : `marvel-champions`
- **Id projet** (`config/projects.json`) : `OCTGN-Marvel-Champions`
- **Fork** : `https://github.com/niclasdumesnil/OCTGN-Marvel-Champions.git`
- **Amont** : `https://github.com/Ouroboros009/OCTGN-Marvel-Champions.git`

---

## 🔴 Règle non négociable avant toute modification du moteur

**Charger le skill `octgn-mod-conventions`** (vault, exposé à Claude Code et à Gemini). Il
impose deux gestes qui ne sont pas optionnels, parce qu'un mainteneur tiers doit pouvoir
relire le diff :

1. **Commenter chaque bloc modifié dans le code**, avec l'intention *et* la ligne
   `Origine : Merlin — <contexte>` — même pour une modification d'une seule ligne.
2. **Écrire une fiche de traçabilité** dans
   `C:\OS-Merlin\memoire\projets\OCTGN-Marvel-Champions\modifications\<slug>.md`.

Le moteur est en **Python 2 / IronPython** : rester dans le style du fichier (indentation
4 espaces, docstrings triple-quotes), ne pas moderniser la syntaxe au passage.

⚠️ **ASCII pur obligatoire dans `scripts\*.py`**, commentaire d'Origine compris — même un
seul accent (`é`, `à`, `ç`...) fait échouer `o8build` (absence de déclaration d'encodage,
PEP 263), avec un message qui ne pointe que le numéro de ligne. Écrire les commentaires
d'origine et explications en anglais ASCII, comme le reste du fichier — la fiche de
traçabilité, elle, reste en français dans le vault. Après toute modification, vérifier
avant de considérer le lot terminé :
```python
import io
lines = io.open('<fichier.py>', encoding='utf-8').readlines()
bad = [i for i, l in enumerate(lines, 1) for ch in l if ord(ch) > 127]
```
Un résultat non vide = le build va échouer sur ces lignes. Payé deux fois
(`loadHero.py` puis `setup.py`), voir la mémoire `octgn-engine-ascii-comments`.

---

## 🆕 Au démarrage d'une nouvelle session

1. **Lire `_cadrage.md`** (vault, `C:\OS-Merlin\memoire\projets\OCTGN-Marvel-Champions\_cadrage.md`),
   section « Journal des lots » — les dernières entrées disent l'état réel : ce qui vient
   d'être livré, ce qui est encore « en test » (pas validé en jeu), et les chantiers
   explicitement différés (ex. Kingpin/Typhoid Mary dans
   `modifications/fear-no-evil-mise-en-place.md` au 2026-08-24). Sans cette lecture, le
   risque est de refaire un travail déjà fait, ou de proposer un correctif déjà écarté.
2. **`git status`** — l'arbre de travail accumule du code non commité d'une session à
   l'autre, c'est normal sur ce chantier (commit seulement sur validation explicite en jeu,
   jamais poussé sans demande). Ne pas s'alarmer d'un statut chargé, ne rien committer/
   pousser sans instruction.
   ➡️ Pour **récupérer les commits d'Ourob09** (ou vérifier si nos PR ont été mergées —
   il merge sans prévenir), charger le skill **`octgn-sync-upstream`** : il porte la
   procédure, les contrôles `tools\beta\verifier_rapprochement.py` et les pièges. Un merge
   propre ne prouve rien ici : les casses de rapprochement sont silencieuses.
3. **Avant tout `build.py --install`**, vérifier `tools\beta\config.json` →
   `revision_beta` : le build refuse une révision déjà installée dans OCTGN (message
   d'erreur explicite) — l'incrémenter d'abord si nécessaire.

---

## 📁 Structure du dépôt
- `055c536f-adba-4bc2-acbf-9aefb9756046\` — **le mod lui-même** (le dossier porte le GUID
  du jeu) : `definition.xml`, `scripts\` (moteur), `Sets\`, `cards\`, `FanMade\`,
  `Fonts\`, `Markers\`, `proxy\`, `symbols\`.
- `tools\beta\` — pipeline de l'**environnement bêta** : `build.py`, `verify.py`,
  `config.json`, sortie `.o8g` / `.nupkg` dans `dist\`. La bêta porte un **GUID distinct**
  pour cohabiter avec le mod officiel installé.
- Scripts Python à la racine — outillage historique d'import et d'images
  (`import_pack.py`, `set_builder.py`, `set_image.py`, `image_renamer.py`,
  `add_octgnid.py`, `get_octgnids.py`, `create_image_ref.py`).

---

## ⚠️ Lancer OCTGN pour tester

Toujours démarrer l'exécutable **avec son répertoire de travail** positionné sur son
dossier d'installation. Sans cela, OCTGN affiche un « There was a problem » trompeur qui
n'a rien à voir avec la vraie cause :

```powershell
Start-Process -FilePath "<...>\OCTGN.exe" -WorkingDirectory "<...dossier d'installation>"
```

Pour une erreur de **script** (Python planté en jeu), `Logs\Octgn.log` n'aide pas : OCTGN
n'y écrit **jamais** les erreurs de script (vérifié sur 20 fichiers de log en août 2026,
cf. `modifications/instrumentation-save-load.md`) — seules les erreurs de démarrage du
module y apparaissent. Un plantage de script ne s'affiche que dans la fenêtre de jeu et
disparaît avec elle ; c'est pour ça que la bêta écrit sa propre trace (`DEBUG_SAVELOAD`,
voir la fiche ci-dessus) à côté du fichier de sauvegarde.

---

## 🔗 Amont des données

Les cartes ne se saisissent pas ici : elles viennent de `marvelsdb_fanmade_data` et sont
générées par **Nexus**. La forme attendue (où écrire `set.xml` et les images, pourquoi une
seule génération officielle) est fixée par le **contrat de génération des sets** dans le
vault — s'y conformer plutôt que d'inventer une variante. Skills utiles :
`marvel-champions-octgn-generation`, `octgn-overrides`.

---

## 📚 Documentation du projet (dans le vault, pas ici)

- **Technique** : `C:\OS-Merlin\memoire\projets\OCTGN-Marvel-Champions\doc-technique\` —
  structure du mod, scripts moteur, sets et cartes, outillage Python, installation locale.
- **Chantier bêta** : `cadrage-environnement-beta.md`, `audit-existant-2026-08-15.md`,
  `lot0-spike-resultats.md`, `contrat-generation-sets.md`.
- **Modifications du moteur** : `modifications\` — une fiche par modification (règle 2
  ci-dessus).
- **Utilisation** : `C:\OS-Merlin\memoire\projets\OCTGN-Marvel-Champions\doc-utilisation\`
  — créée pour l'environnement bêta (`environnement-beta.md`), à tenir à jour à mesure que
  la bêta se distribue à des testeurs.

**Convention impérative : à chaque lot livré, la doc est mise à jour.** Un lot livré sans
sa doc est un lot incomplet. Les gabarits, le frontmatter et les règles d'index sont portés
par le skill **`documentation-projet`**
(`C:\OS-Merlin\memoire\skills\os-merlin\documentation-projet\`) : le charger avant de
rédiger, ne jamais recopier ses règles ici.
