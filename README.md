# Hypertube - banche `main`

⚠️ Ceci est la branche de **développement**. Le code ici peut être temporairement
instable pendant l'intégration de nouvelles fonctionnalités.
 
## Rôle de cette branche
 
- Toutes les fonctionnalités validées sont intégrées ici en premier
- C'est la branche de référence pour démarrer tout nouveau travail
- Elle n'est jamais déployée directement en production

## Règles
 
- ❌ Ne jamais commit directement sur `main`
- ✅ Toujours passer par une branche `feature/xxx`
- ✅ Toute Pull Request vers `main` nécessite au moins 1 review avant merge
- ✅ Une fois le scope d'une version validé, une branche `release/x.y.z` est créée pour préparer le passage en production

## Démarrer une nouvelle fonctionnalité
 
```bash
git checkout main
git pull
git checkout -b feature/nom-explicite
```
 
## Voir aussi
 
- [CONTRIBUTING.md](./CONTRIBUTING.md) pour le workflow complet et les conventions de commit
- Branche `prod` pour la version stable actuellement en production
 