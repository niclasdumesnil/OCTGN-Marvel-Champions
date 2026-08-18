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

Les vraies erreurs sont dans `Logs\Octgn.log`, pas à l'écran.

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
- ⚠️ **Il n'existe pas encore de `doc-utilisation\`** pour ce projet : à créer le jour où
  la bêta est distribuée à des testeurs, qui auront besoin d'un mode d'emploi.

**Convention impérative : à chaque lot livré, la doc est mise à jour.** Un lot livré sans
sa doc est un lot incomplet. Les gabarits, le frontmatter et les règles d'index sont portés
par le skill **`documentation-projet`**
(`C:\OS-Merlin\memoire\skills\os-merlin\documentation-projet\`) : le charger avant de
rédiger, ne jamais recopier ses règles ici.
