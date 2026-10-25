# Étude de cas et niveau de preuve

## Situation

L'exercice de bootcamp consistait à traiter des changements de prix : topic Pub/Sub, abonnement push filtré, fonction Python HTTP et table BigQuery. Une dead-letter policy devait isoler les messages non traitables. L'utilisateur a signalé des retries sans réception dans la DLQ, puis une réception de deux messages après correction IAM.

## Chronologie du 20 août 2026

Heures de Paris, UTC+2. Les identifiants de projet, de compte et de trace sont omis.

| Heure | Observation conservée | Portée |
|---|---|---|
| 20:20:18 | Réponse `UpdateSubscription` avec DLQ, seuil 5, backoff 5–240 s, filtre et push OIDC | Configuration visible ; l'opération modifiait seulement `pushConfig` |
| 20:32:16 | POST HTTP 500 et erreur `'old_price'` | Échec du traitement |
| 20:42:20 | JSON contenant uniquement `event_type` et `product_id` | Message incomplet ; pas d'identifiant permettant de le corréler au précédent |
| 20:51:49 et 20:52:19 | Retours de deux commandes `seek` | Modification de l'état d'acquittement ; aucune preuve de transfert DLQ |
| 20:57:02 | Appel BigQuery `insertAll` refusé, permission `bigquery.tables.updateData` | Un traitement atteint BigQuery ; insertion non réussie |
| 21:36:31 | `SetIamPolicy` réussi : Subscriber sur l'abonnement source | Attribution au service agent Pub/Sub confirmée |
| 21:36:46 | `SetIamPolicy` réussi : Publisher sur le topic DLQ | Attribution au même service agent confirmée |
| Ensuite | Réception de deux messages rapportée | Sortie originale et identifiants non retrouvés |

Une capture montre également la création réussie du topic DLQ et de son abonnement, suivie d'une mise à jour CLI en échec. Le chemin saisi contenait une référence de variable incorrecte (`$...`). La configuration effective observée ultérieurement dans l'audit est plus probante que cette tentative échouée.

Le 20 septembre, des événements `InternalExpireInactiveSubscription` expliquent la disparition des abonnements. La configuration examinée indiquait une expiration après 31 jours d'inactivité. Cette disparition n'est pas attribuée à la fin de l'essai gratuit.

## Méthode de diagnostic

1. Examiner le contenu reçu : les prix et le timestamp étaient absents d'un message journalisé.
2. Relier cette structure au code : l'accès direct à `parsed["old_price"]` peut lever `KeyError`, capturé puis transformé en HTTP 500.
3. Distinguer le refus d'insertion BigQuery du problème de transfert Pub/Sub.
4. Examiner les permissions du service agent Pub/Sub sur les deux ressources concernées par la DLQ.
5. Consigner le résultat du test et les limites des traces conservées.

Une nouvelle livraison est attendue après HTTP 500, mais les captures sans identifiants ne permettent pas de compter les tentatives d'un message précis. Les deux attributions IAM sont prouvées ; leur nécessité effective avant correction et le résultat final reposent aussi sur le récit de l'exercice.

## Provenance

- Captures directes : création des ressources, code Python, erreurs HTTP et BigQuery, contenu incomplet, retours `seek`.
- Journaux d'audit fournis et examinés : configuration de l'abonnement, attributions IAM, expiration.
- Support pédagogique : schéma attendu, commandes de déploiement, dépendances et résultat du test valide. Ce support n'est pas une preuve d'exécution.
- Résumé d'une ancienne conversation : résultat final rapporté ; source secondaire, recoupée avec les éléments directs.

Les pièces brutes sont archivées localement et ne sont pas distribuées ici. Ce document est une synthèse anonymisée, pas un export d'audit. Les lecteurs ne peuvent donc pas vérifier toutes les observations historiques depuis ce seul dépôt.

## Ce qui n'est pas établi

La sortie du pull montrant deux messages distincts, la correction effective des droits BigQuery, une insertion réussie, une réinjection et la version exacte finalement déployée ne sont pas disponibles. Le code historique est transcrit d'une capture. Les tests de ce dépôt sont une validation ultérieure du code reconstruit.
