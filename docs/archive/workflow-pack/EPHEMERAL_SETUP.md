# Ephemeral Environment Setup Guide

This guide helps you set up **automatic ephemeral environments** that spin up for every PR and get destroyed when the PR closes.

## 🚀 Quick Setup (5 minutes)

### **1. Google Cloud Project Setup**

1. **Create a GCP Project** (or use existing):

   ```bash
   gcloud projects create your-project-id
   gcloud config set project your-project-id
   ```

2. **Enable Required APIs**:

   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

3. **Create Service Account**:

   ```bash
   gcloud iam service-accounts create ephemeral-env-sa \
     --description="Service account for ephemeral environments" \
     --display-name="Ephemeral Environment SA"
   ```

4. **Grant Required Permissions**:

   ```bash
   PROJECT_ID=$(gcloud config get-value project)

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:ephemeral-env-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:ephemeral-env-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/cloudbuild.builds.editor"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:ephemeral-env-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:ephemeral-env-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```

5. **Create Service Account Key**:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=ephemeral-env-sa@$PROJECT_ID.iam.gserviceaccount.com
   ```

### **2. GitHub Repository Setup**

1. **Add GitHub Secrets**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `GCP_PROJECT_ID`: Your Google Cloud project ID
     - `GCP_SA_KEY`: Contents of the `key.json` file (entire JSON)

2. **Install Pulumi CLI** (for local testing):
   ```bash
   curl -fsSL https://get.pulumi.com | sh
   ```

### **3. Test the Setup**

1. **Create a test branch**:

   ```bash
   git checkout -b test-ephemeral-env
   git push origin test-ephemeral-env
   ```

2. **Create a PR** - The ephemeral environment will automatically deploy!

3. **Check the PR comments** - You'll see a comment with the environment URL.

---

## 🔧 How It Works

### **Automatic Process**:

1. **PR Created/Updated** → GitHub Actions triggers
2. **Infrastructure Provisioned** → Pulumi creates Cloud Run service
3. **Application Deployed** → Docker image built and deployed
4. **Tests Run** → All tests execute against the live environment
5. **PR Comment Added** → Direct link to your ephemeral environment
6. **PR Closed** → Infrastructure automatically destroyed

### **What Gets Created**:

- **Cloud Run Service** - Hosts your application
- **Container Registry** - Stores your Docker images
- **Pulumi Stack** - Manages infrastructure state
- **Unique URLs** - Each branch gets its own URL

### **Cost Optimization**:

- **Pay-per-use** - Only pay when environment is active
- **Auto-cleanup** - Resources destroyed when PR closes
- **Minimal resources** - Optimized for testing, not production load

---

## 🛠️ Customization

### **For Different Languages**:

**Python Application**:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "app.py"]
```

**Go Application**:

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["./main"]
```

**Java Application**:

```dockerfile
FROM openjdk:17-jdk-slim
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN ./mvnw package -DskipTests
EXPOSE 8080
CMD ["java", "-jar", "target/app.jar"]
```

### **Environment Variables**:

Your application automatically gets:

- `BRANCH_NAME` - The git branch name
- `ENVIRONMENT` - Always "ephemeral"
- `PORT` - Always 8080 (Cloud Run requirement)

### **Custom Configuration**:

Edit `infra/pulumi/index.js` to:

- Change resource limits
- Add environment variables
- Configure custom domains
- Add databases or other services

---

## 🔍 Troubleshooting

### **Common Issues**:

**"Repository not found" error**:

- Check that `GCP_SA_KEY` secret is properly formatted JSON
- Verify service account has correct permissions

**"Stack not found" error**:

- Pulumi state bucket might not exist
- Check that `GCP_PROJECT_ID` secret matches your actual project ID

**"Service not ready" timeout**:

- Check your application listens on port 8080
- Ensure `/health` endpoint returns 200 status
- Verify Dockerfile builds successfully

### **Debug Commands**:

```bash
# Test locally
docker build -t test-app .
docker run -p 8080:8080 test-app

# Check GCP setup
gcloud auth list
gcloud config get-value project
gcloud services list --enabled

# Test Pulumi
cd infra/pulumi
pulumi login gs://your-project-id-pulumi-state
pulumi stack ls
```

---

## 🎯 Next Steps

1. **Customize your application** - Replace `server.js` with your actual app
2. **Add databases** - Extend Pulumi config for Cloud SQL, Firestore, etc.
3. **Configure monitoring** - Add Cloud Logging and monitoring
4. **Set up custom domains** - Configure DNS for prettier URLs

Your ephemeral environments are now ready! Every PR will get its own live, testable environment automatically. 🚀
