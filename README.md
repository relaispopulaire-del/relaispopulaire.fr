# relaispopulaire.fr

Site de Relais Populaire Média, publié sur GitHub Pages.

## Comment ça marche

- Les pages sont générées à partir des sources du dossier `src/` :
  - `src/templates/` : les gabarits des pages ;
  - `src/static/` : styles, scripts, polices et images ;
  - `src/data/site.json` : informations générales, chiffres des réseaux, mentions légales ;
  - `src/data/videos.json` : sélection de vidéos, titres retravaillés ;
  - `src/data/latest.json` : derniers Shorts et vidéos longues (mis à jour automatiquement).
- Le fichier `.github/workflows/site.yml` reconstruit et republie le site :
  - à chaque modification du dépôt ;
  - toutes les heures, en allant chercher les nouveaux Shorts et vidéos de la chaîne
    YouTube @Relaispopulaire (flux publics, aucune clé nécessaire). Le site n'est
    republié que s'il y a du nouveau.

## Modifier quelque chose

- Les chiffres (abonnés, vues) : `src/data/site.json`, rubrique `audience`.
- Les mentions légales : `src/data/site.json`, rubrique `legal`, puis `"declared": true`
  une fois l'association déclarée.
- Le titre d'une vidéo sur le site : `src/data/videos.json`, rubrique `titles`.

## Construire en local

```
pip install -r requirements.txt
npm ci
python3 youtube.py      # facultatif : récupère les dernières vidéos
python3 build.py        # génère dist/
python3 flat.py _site   # version publiée sur GitHub Pages
```
