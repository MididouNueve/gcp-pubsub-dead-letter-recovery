# Vérifier une future exécution

Les commandes supposent les variables du [guide cloud](cloud-lab.md). Elles constituent un protocole à exécuter, pas une sortie observée. Conserver les preuves dans `evidence-local/`, ignoré par Git et le déploiement.

## A. Message valide

```bash
mkdir -p evidence-local
gcloud pubsub topics publish prices-events --project="$PROJECT_ID" \
  --attribute=event_type=price_change --ordering-key=DEMO-001 \
  --message="$(cat examples/valid-event.json)" \
  --format=json > evidence-local/publish-valid.json
```

Conserver le `messageId`, rechercher `processed_price_change` avec cet identifiant dans les logs de la fonction, puis vérifier la ligne dans BigQuery :

```bash
bq --project_id="$PROJECT_ID" --location="$REGION" query --use_legacy_sql=false \
  'SELECT product_id, old_price, new_price, ts
   FROM `'"$PROJECT_ID.$DATASET.$TABLE"'`
   WHERE product_id = "DEMO-001"
   ORDER BY ts DESC LIMIT 10'
```

Dans une table préexistante, choisir un nouvel identifiant produit et un timestamp de test pour ne pas confondre une ancienne ligne avec la nouvelle. Une publication réussie seule ne prouve pas l'insertion.

## B. Message invalide et DLQ

```bash
gcloud pubsub topics publish prices-events --project="$PROJECT_ID" \
  --attribute=event_type=price_change --ordering-key=DEMO-INVALID-001 \
  --message="$(cat examples/invalid-event.json)" \
  --format=json > evidence-local/publish-invalid.json
```

Observer les réponses 500 et la livraison vers la DLQ. Utiliser une ordering key distincte évite de bloquer le test valide derrière ce message. Le délai de transfert est variable.

```bash
gcloud pubsub subscriptions pull prices-dlq-sub --project="$PROJECT_ID" \
  --limit=10 --format=json > evidence-local/dlq-pull.json
```

Ce pull n'acquitte pas automatiquement. Les messages peuvent être relivrés après le délai d'acquittement. Une réponse vide ponctuelle ne prouve pas que la file est durablement vide. Le topic DLQ reçoit un nouveau message enveloppant le message original : inspecter les données décodées et les métadonnées pour corréler l'identifiant source avec la publication.

Compter les messages sources distincts, pas le nombre de lignes provenant de pulls répétés. Conserver le JSON complet et l'heure de collecte ; `--limit=2` n'est pas une preuve de deux réceptions. Après inspection, acquitter uniquement les éléments dont on a conservé les données et dont le traitement est terminé. Aucun rejeu automatique n'est inclus.

## C. Matrice de validation

| Cas | Attendu | Validation locale disponible |
|---|---|---|
| Message valide | Insertion sans erreur puis HTTP 200 | Client substitué |
| Champs manquants, base64/JSON invalide | HTTP 500, aucune insertion | Oui |
| Prix invalide ou timestamp sans fuseau | HTTP 500, aucune insertion | Oui |
| Exception SDK ou erreurs par ligne BigQuery | HTTP 500 | Oui, erreurs injectées |
| Livraison répétée | Même identifiant d'insertion ; doublons toujours possibles | Stabilité de l'identifiant seulement |
| Authentification push et IAM | Invocation et transfert autorisés | Non |
| Retry et DLQ | Message source corrélé dans la DLQ | Non |

Ne jamais présenter une sortie du faux client local comme un résultat BigQuery. Dater séparément une future exécution cloud et les événements historiques d'août 2026.
