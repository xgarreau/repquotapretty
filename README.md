# repquota-pretty

Transforme la sortie brute de `repquota -a` en un rapport lisible, coloré et trié.

## Exemple

```
repquota -a | repquota-pretty.py
```

```
══════════════════════════════════════════════ /dev/sda1 ══
 alice    │  12,3 Go / 20 Go  │ ████████████░░░░  61% │  45k fichiers
 bob      │   8,7 Go / 20 Go  │ ████████░░░░░░░░  43% │  12k fichiers
 charlie  │  19,1 Go / 20 Go  │ ███████████████░  95% │  80k fichiers  ⚠
```

## Installation

Le script est autonome, sans dépendance externe. Il suffit de le rendre exécutable :

```bash
chmod +x repquota-pretty.py
# Optionnel : l'ajouter au PATH
cp repquota-pretty.py /usr/local/bin/repquota-pretty
```

Prérequis : Python 3.9+.

## Utilisation

```bash
# Pipe direct
repquota -a | repquota-pretty.py

# Depuis un fichier
repquota-pretty.py repquota_output.txt

# Redirection
repquota-pretty.py < repquota_output.txt
```

## Options

| Option | Description |
|---|---|
| `-s`, `--sort` | Tri : `used` (défaut), `pct`, `name`, `files` |
| `-z`, `--show-zero` | Afficher les utilisateurs avec 0 usage |
| `--no-color` | Désactiver les couleurs ANSI |

### Exemples de tri

```bash
# Trier par pourcentage d'utilisation
repquota -a | repquota-pretty.py --sort pct

# Trier par nom d'utilisateur
repquota -a | repquota-pretty.py --sort name

# Inclure les comptes sans usage
repquota -a | repquota-pretty.py --show-zero
```

## Lecture du rapport

Pour chaque système de fichiers, le script affiche un tableau avec :

- **Utilisateur** — nom du compte
- **Espace utilisé / quota** — avec unités lisibles (Ko, Mo, Go, To)
- **Barre de progression colorée** :
  - Vert : 0–79 %
  - Jaune : 80–94 %
  - Rouge : 95 %+
- **Nombre de fichiers** — avec suffixes k/M
- **Alertes** — indicateur si le quota soft est dépassé, avec délai de grâce restant

En bas de chaque section : total de l'espace utilisé, total des fichiers, nombre d'utilisateurs actifs.
