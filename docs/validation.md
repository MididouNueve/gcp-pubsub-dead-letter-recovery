# Validation de la version préparée

Date : 25 octobre 2026.

| Vérification | Résultat |
|---|---|
| `python3.11 -m unittest discover -s tests -v` | 13 tests réussis |
| `python3.12 -m unittest discover -s tests -v` | 13 tests réussis |
| Démo locale | Événement valide : HTTP 200 ; incomplet : HTTP 500 |
| Syntaxe Python et fichiers JSON | Valides |
| Blocs Bash du guide | Syntaxe vérifiée avec `bash -n`, sans exécution cloud |
| Liens internes Markdown | Cibles présentes |
| Recherche d'identifiants du projet historique et de marqueurs de secrets | Aucun détecté dans les fichiers destinés au dépôt |

Les tests remplacent le client BigQuery et utilisent un objet requête de test. Ils n'exécutent pas le serveur Functions Framework ni une vraie requête réseau. Les dépendances cloud n'ont pas été installées ou verrouillées pendant cette préparation.

Le workflow GitHub Actions est préparé pour Python 3.11 et 3.12. Il ne déploie aucune ressource. Aucun résultat GitHub Actions distant, test IAM, transfert DLQ ou écriture BigQuery réelle n'est revendiqué ici.
