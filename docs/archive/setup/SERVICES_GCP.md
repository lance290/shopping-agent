# Google Cloud Setup (Pulumi + Cloud Run)

This guide walks you through the minimum configuration required for the PR
environment workflow (`.github/workflows/pr-env.yml`) to provision ephemeral
Cloud Run services with Pulumi.

---

## 1. Create / Select a Project

1. Visit <https://console.cloud.google.com/projectselector2/home/dashboard>.
2. Create a new project or select an existing one dedicated to ephemeral
   environments.
3. Record the **Project ID** — you will reference it everywhere.

---

## 2. Enable Required APIs

From the Cloud Shell or your machine:

```bash
gcloud config set project <PROJECT_ID>
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  iam.googleapis.com
```

The Pulumi program re-enables these APIs if they are accidentally disabled, but
they must exist once up front.

---

## 3. Create a Service Account for GitHub Actions

```bash
gcloud iam service-accounts create pulumi-deployer \
  --display-name "Pulumi Ephemeral Deployments"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:pulumi-deployer@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/editor"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:pulumi-deployer@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

> Tip: tighten permissions later (e.g., `roles/run.admin`, `roles/artifactregistry.admin`,
> `roles/iam.serviceAccountUser`) once the workflow is stable.

Export the key:

```bash
gcloud iam service-accounts keys create pulumi-deployer.json \
  --iam-account pulumi-deployer@<PROJECT_ID>.iam.gserviceaccount.com
```

Store the file safely — it will become the `GCP_SA_KEY` secret in GitHub.

---

## 4. Prepare a Pulumi State Bucket

Pulumi stores stack state in Google Cloud Storage.

```bash
gsutil mb gs://<PROJECT_ID>-pulumi-state
gsutil versioning set on gs://<PROJECT_ID>-pulumi-state
```

The GitHub workflow double checks and creates the bucket if missing, but performing
this once avoids race conditions.

---

## 5. Configure GitHub Secrets

In the repository settings:

| Secret              | Value                                                         |
|---------------------|---------------------------------------------------------------|
| `GCP_PROJECT_ID`    | `<PROJECT_ID>` (e.g., `my-ephemeral-env`)                     |
| `GCP_SA_KEY`        | Contents of `pulumi-deployer.json`, including braces/newlines |

Optional secrets:

- `REGION` (default `us-central1`)
- `SERVICE_IMAGE` if you want to override the image built by Cloud Build

---

## 6. Local Environment Variables

Copy `env.example` to `.env` in your application root and update:

```bash
GCP_PROJECT_ID=<PROJECT_ID>
GCP_REGION=us-central1
```

These values let your local scripts (e.g., `pulumi` CLI, seed scripts) behave the same as the CI workflow.

---

## 7. Authenticate Locally (Optional)

To run Pulumi or `gcloud` locally using the service account:

```bash
gcloud auth activate-service-account \
  pulumi-deployer@<PROJECT_ID>.iam.gserviceaccount.com \
  --key-file=pulumi-deployer.json

gcloud config set project <PROJECT_ID>
pulumi login gs://<PROJECT_ID>-pulumi-state
```

Now you can execute `pulumi up` from `infra/pulumi` exactly as CI does.

---

## Next Steps

1. Set up databases or caches with the service guides in this folder.
2. Use `/plan` → `/task` → `/implement` to ship your MVP.
3. Monitor Cloud Run in the GCP console; tweak CPU/memory in `infra/pulumi/index.js` as needed.

