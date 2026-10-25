# Trois identités à distinguer

| Identité | Responsabilité | Autorisation dans la reproduction |
|---|---|---|
| Service agent Pub/Sub géré par Google | Transférer les échecs et signer le token de push | Subscriber sur la source ; Publisher sur la DLQ ; permission de génération de token sur le compte de push |
| Compte de push dédié | Identité OIDC présentée à la fonction | `roles/run.invoker` sur le service Cloud Run Gen2 |
| Compte d'exécution de la fonction | Écrire dans BigQuery | `roles/bigquery.dataEditor` limité à la table du labo |

Le compte humain qui configure le labo doit posséder séparément les droits de création, de déploiement, de modification IAM et `iam.serviceAccounts.actAs` sur les comptes utilisés. Ces droits d'administration ne sont pas les droits d'exécution de la fonction.

## Correction au cœur de l'étude

Après création du topic DLQ et des abonnements, les deux attributions nécessaires sont :

```bash
gcloud pubsub subscriptions add-iam-policy-binding price-change-sub \
  --project="$PROJECT_ID" \
  --member="serviceAccount:$PUBSUB_AGENT" \
  --role=roles/pubsub.subscriber

gcloud pubsub topics add-iam-policy-binding prices-dlq \
  --project="$PROJECT_ID" \
  --member="serviceAccount:$PUBSUB_AGENT" \
  --role=roles/pubsub.publisher
```

`PUBSUB_AGENT` a la forme `service-PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com`. Il utilise le numéro du projet, pas son identifiant textuel. [Permissions de la DLQ](https://docs.cloud.google.com/pubsub/docs/dead-letter-topics).

Pour une fonction Gen2 authentifiée, le rôle d'invocation est `roles/run.invoker` sur le service Cloud Run sous-jacent. Le rôle de première génération montré dans le support historique n'est pas repris. [Authentification des fonctions](https://docs.cloud.google.com/functions/docs/securing/authenticating).

Le service agent doit aussi pouvoir générer le token OIDC du compte de push. Le guide donne une attribution Token Creator sur ce seul compte ; une permission équivalente peut déjà exister. [Push authentifié](https://docs.cloud.google.com/pubsub/docs/authenticate-push-subscriptions).

Le rôle BigQuery Data Editor est un rôle prédéfini contenant plus que la seule insertion. Sa portée est limitée à la table ici ; ce choix n'est pas présenté comme une permission personnalisée minimale. [Gestion IAM d'une table](https://docs.cloud.google.com/bigquery/docs/reference/bq-cli-reference#bq_add-iam-policy-binding).
