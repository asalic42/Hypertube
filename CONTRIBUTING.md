# Contribuer au projet Hypertube

Ce document décrit le workflow Git et les conventions à suivre par toute
l'équipe pour garder le projet organisé.

## 1. Workflow Git

On suit une adaptation du Git-flow, avec deux branches persistantes :

- **`main`** : branche de développement, jamais de commit direct
- **`prod`** : branche stable/production, jamais de commit direct

Et trois types de branches temporaires :

| Branche | Part de | Merge dans | Usage |
|---|---|---|---|
| `feature/xxx` | `main` | `main` | Une nouvelle fonctionnalité |
| `release/x.y.z` | `main` | `prod` + `main` | Stabilisation avant une release |
| `hotfix/xxx` | `prod` | `prod` + `main` | Bug critique en production |

### Créer une feature

```bash
git checkout main
git pull
git checkout -b feature/nom-explicite
```

### Créer un hotfix

```bash
git checkout prod
git pull
git checkout -b hotfix/nom-explicite
```

## 2. Format des commits (Conventional Commits)

On utilise la convention [Conventional Commits](https://www.conventionalcommits.org/)
pour que l'historique soit lisible et exploitable automatiquement (changelog,
versionning).

### Format

```
<type>(<scope>): <description courte>

<corps du message (optionnel)>

<footer (optionnel)>
```

- **`type`** : la nature du changement (obligatoire, voir tableau ci-dessous)
- **`scope`** : la partie du projet concernée, entre parenthèses (optionnel mais recommandé chez nous — ex : `library`, `auth`, `api`, `streaming`)
- **`description`** : à l'impératif, courte, sans majuscule ni point final
- **`corps`** : explique le *pourquoi* du changement si nécessaire

### Types autorisés

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `docs` | Documentation uniquement |
| `style` | Formatage, indentation (aucun changement de logique) |
| `refactor` | Refonte du code sans changer le comportement |
| `perf` | Amélioration de performance |
| `test` | Ajout ou modification de tests |
| `chore` | Tâches techniques (dépendances, config...) |
| `build` | Système de build, dépendances externes |
| `ci` | Configuration CI/CD |

### Exemples

```
feat(library): ajouter la bibliotheque de films
```

```
fix(api): corriger le double appel a l'endpoint
```

```
feat(player): ajouter le support du sous-titrage automatique

Intègre l'API de transcription pour générer les sous-titres
en temps réel sur les flux live.
```

<!-- ### Vérification automatique

Un hook `commitlint` bloque les commits non conformes :

```bash
npm install --save-dev @commitlint/cli @commitlint/config-conventional husky
npx husky init
echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg
```

Fichier `commitlint.config.js` :

```js
module.exports = { extends: ['@commitlint/config-conventional'] };
``` -->

## 3. Pull Requests

- 1 review valide minimum obligatoire avant merge
- Supprimer la branche après merge

<!-- ## 4. Lancer le projet en local

```bash
npm install
npm run dev
```

## 5. Lancer les tests

```bash
npm test
``` -->