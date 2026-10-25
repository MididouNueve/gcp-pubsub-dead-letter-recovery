# Reproduction cloud optionnelle

Guide préparé le 25 octobre 2026 ; **non exécuté pour ce dépôt**. Les tests locaux du README fonctionnent sans GCP. Les étapes suivantes créent des ressources et peuvent engendrer des coûts : elles sont destinées à un projet de test distinct, avec facturation et droits de déploiement déjà configurés.

Exécuter depuis la racine du dépôt, dans un shell Bash avec `gcloud` et `bq`. Le projet doit permettre Cloud Build, Artifact Registry et les fonctions Gen2 ; les comptes de build et le déployeur doivent avoir les permissions requises par sa politique. Ce guide ne modifie pas automatiquement leurs rôles. Les noms ci-dessous doivent être libres ; en cas d'erreur, arrêter et examiner le résultat avant l'étape suivante.

## 1. Paramètres et services

```bash
export PROJECT_ID="your-test-project-id"
export REGION="europe-west9"
export FUNCTION_NAME="price-change-consumer"
export DATASET="realtime_demo"
export TABLE="price_changes"

gcloud services enable pubsub.googleapis.com cloudfunctions.googleapis.com \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  bigquery.googleapis.com iamcredentials.googleapis.com --project="$PROJECT_ID"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
export PUBSUB_AGENT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
export PUSH_SA="price-push@${PROJECT_ID}.iam.gserviceaccount.com"
export RUNTIME_SA="price-consumer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud beta services identity create --service=pubsub.googleapis.com --project="$PROJECT_ID"
gcloud iam service-accounts create price-push --project="$PROJECT_ID"
gcloud iam service-accounts create price-consumer --project="$PROJECT_ID"
```

## 2. BigQuery et compte d'exécution

```bash
bq --project_id="$PROJECT_ID" --location="$REGION" mk --dataset "$PROJECT_ID:$DATASET"
bq --project_id="$PROJECT_ID" mk --table \
  "$PROJECT_ID:$DATASET.$TABLE" config/bigquery-schema.json
bq add-iam-policy-binding \
  --member="serviceAccount:$RUNTIME_SA" \
  --role=roles/bigquery.dataEditor \
  --table=true "$PROJECT_ID:$DATASET.$TABLE"
```

## 3. Fonction et push authentifié

```bash
gcloud functions deploy "$FUNCTION_NAME" --project="$PROJECT_ID" \
  --gen2 --region="$REGION" --runtime=python311 --source=. \
  --entry-point=pubsub_to_bq --trigger-http --no-allow-unauthenticated \
  --service-account="$RUNTIME_SA" --timeout=60s --max-instances=2 \
  --set-env-vars="BQ_TABLE=$PROJECT_ID.$DATASET.$TABLE"

SERVICE_RESOURCE=$(gcloud functions describe "$FUNCTION_NAME" \
  --project="$PROJECT_ID" --gen2 --region="$REGION" --format='value(serviceConfig.service)')
SERVICE_NAME=${SERVICE_RESOURCE##*/}
export ENDPOINT=$(gcloud functions describe "$FUNCTION_NAME" \
  --project="$PROJECT_ID" --gen2 --region="$REGION" --format='value(serviceConfig.uri)')

gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
  --project="$PROJECT_ID" --region="$REGION" \
  --member="serviceAccount:$PUSH_SA" --role=roles/run.invoker

gcloud iam service-accounts add-iam-policy-binding "$PUSH_SA" \
  --project="$PROJECT_ID" --member="serviceAccount:$PUBSUB_AGENT" \
  --role=roles/iam.serviceAccountTokenCreator
```

L'URL Cloud Run retournée est utilisée à la fois pour l'endpoint et l'audience OIDC. Le contrôle IAM du service authentifie l'appel avant le handler Python. Le handler local n'est pas un validateur JWT autonome.

## 4. Topics, abonnements et permissions DLQ

```bash
gcloud pubsub topics create prices-events prices-dlq --project="$PROJECT_ID"
gcloud pubsub subscriptions create prices-dlq-sub \
  --project="$PROJECT_ID" --topic=prices-dlq

gcloud pubsub subscriptions create price-change-sub \
  --project="$PROJECT_ID" --topic=prices-events \
  --push-endpoint="$ENDPOINT" --push-auth-service-account="$PUSH_SA" \
  --push-auth-token-audience="$ENDPOINT" \
  --message-filter='attributes.event_type="price_change"' \
  --enable-message-ordering --ack-deadline=60 \
  --message-retention-duration=7d --expiration-period=31d \
  --dead-letter-topic="projects/$PROJECT_ID/topics/prices-dlq" \
  --max-delivery-attempts=5 --min-retry-delay=5s --max-retry-delay=240s

gcloud pubsub subscriptions add-iam-policy-binding price-change-sub \
  --project="$PROJECT_ID" --member="serviceAccount:$PUBSUB_AGENT" \
  --role=roles/pubsub.subscriber
gcloud pubsub topics add-iam-policy-binding prices-dlq \
  --project="$PROJECT_ID" --member="serviceAccount:$PUBSUB_AGENT" \
  --role=roles/pubsub.publisher
```

Cette reproduction choisit un délai d'acquittement de 60 s ; la configuration historique indiquait 10 s. Le seuil DLQ et le backoff ne constituent pas une échéance exacte. Attendre la propagation IAM avant de publier. Les paramètres sont décrits dans la [référence de création d'abonnement](https://docs.cloud.google.com/sdk/gcloud/reference/pubsub/subscriptions/create).

## 5. Vérifier avant de publier

```bash
gcloud pubsub subscriptions describe price-change-sub --project="$PROJECT_ID" --format=json
gcloud pubsub subscriptions get-iam-policy price-change-sub --project="$PROJECT_ID"
gcloud pubsub topics get-iam-policy prices-dlq --project="$PROJECT_ID"
gcloud run services get-iam-policy "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION"
bq get-iam-policy "$PROJECT_ID:$DATASET.$TABLE"
```

Vérifier les noms de destination et les identités. Le service de test ne doit pas avoir de binding `allUsers` ou `allAuthenticatedUsers`. Passer ensuite au [plan de vérification](verification.md).

## Fin du labo

Conserver les observations avant le nettoyage. Dans le projet de test, inventorier puis supprimer les ressources créées pour ce labo : les deux abonnements, les deux topics, la fonction, la table puis le dataset s'il est vide, les comptes dédiés et les éventuels artefacts de build devenus inutiles. Ne pas appliquer ce nettoyage aux ressources historiques ou partagées. Aucun script de suppression ou de `seek` n'est exécuté par les tests de ce dépôt.
