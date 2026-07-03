# Hypertube — branche `prod`

✅ Ceci est la branche de **production**. Chaque commit ici correspond à une
version stable, déployée, et taguée (`vX.Y.Z`).

## Rôle de cette branche

- Reflète exactement ce qui tourne en production
- Sert de point de départ pour les corrections urgentes (`hotfix/xxx`)
- N'est jamais en avance sur ce qui est réellement déployé

## Règles

- ❌ Ne jamais commit directement sur `prod`
- ✅ Seuls les merges depuis `release/x.y.z` ou `hotfix/xxx` sont autorisés
- ✅ Chaque merge doit être immédiatement suivi d'un tag de version et d'un déploiement
- ✅ Après chaque merge, répercuter les changements sur `main` (pour ne pas perdre les fixes de hotfix)

## Corriger un bug critique en production

```bash
git checkout prod
git pull
git checkout -b hotfix/nom-explicite
# ... correction ...
# Ouvrir une PR vers prod, puis une seconde vers main une fois mergé
```

## Voir aussi

- Branche `main` pour le développement en cours
- [CONTRIBUTING.md](https://raw.githubusercontent.com/.../main/CONTRIBUTING.md) sur `main` pour le workflow complet