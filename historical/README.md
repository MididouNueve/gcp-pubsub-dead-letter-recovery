# Code historique

`main.py` est transcrit d'une capture fournie pendant la récupération de l'exercice. Les retours à la ligne peuvent différer. Ce n'est pas le fichier source original ni une attestation de la dernière version déployée.

Le code provient du contexte pédagogique du bootcamp ; l'utilisateur a reproduit et diagnostiqué cet exercice avec assistance. L'auteur initial du support n'est pas identifié dans les éléments disponibles. Aucune licence globale n'est ajoutée pour réattribuer ce code ou le support à l'utilisateur. Les diapositives et captures ne sont pas redistribuées.

Le support mentionne `google-cloud-bigquery==3.*`, Python 3.11 et l'entry point `pubsub_to_bq`. L'environnement exact n'est pas verrouillé. Ne pas importer ce fichier pour les tests hors ligne : il initialise immédiatement un client BigQuery.

## Différences avec la reproduction actuelle

| Historique visible | Reproduction préparée pour le portfolio |
|---|---|
| Accès direct aux champs | Validation explicite du contrat |
| Client initialisé à l'import | Client créé au premier besoin et substitué en test |
| Table `dataset.table` | Variable `BQ_TABLE` avec `project.dataset.table` |
| Prix convertis par `float` | Nombres JSON finis et positifs ou nuls |
| Timestamp transmis tel quel | Format avec fuseau validé, normalisation UTC |
| Identifiants d'insertion non fournis | `messageId` stable utilisé comme `insertId` |
| Erreur imprimée en clair | Type d'erreur ou motif limité dans les logs |

Le schéma de la reproduction rend les quatre champs obligatoires ; la commande historique ne précisait pas leur mode. Ce durcissement et les autres adaptations datent de la préparation du dépôt, pas de l'exercice initial.
