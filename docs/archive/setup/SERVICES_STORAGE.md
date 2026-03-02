# File Storage & CDN Setup

Static assets and user uploads require durable object storage. Start with a
managed bucket and layer a CDN when latency matters.

---

## 1. Choose a Storage Provider

| Provider | Best For | Quick Start |
|----------|----------|-------------|
| **Google Cloud Storage** | Tight GCP integration, Cloud Run | `gsutil mb gs://bucket-name` |
| **Amazon S3** | Industry standard, rich IAM | AWS Console or `aws s3api create-bucket` |
| **Cloudflare R2** | Low-cost egress, simple pricing | Cloudflare Dashboard → R2 |

Your `.env` should contain variables from `env.example`:

```bash
GCS_BUCKET_NAME=your-bucket
AWS_S3_BUCKET=your-bucket
AWS_S3_REGION=us-east-1
AWS_S3_ACCESS_KEY_ID=...
AWS_S3_SECRET_ACCESS_KEY=...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
CDN_URL=https://cdn.yourdomain.com
```

Only populate the keys for the provider you actually use.

---

## 2. Google Cloud Storage

```bash
gsutil mb -l us-central1 gs://<PROJECT_ID>-assets
gsutil iam ch allUsers:objectViewer gs://<PROJECT_ID>-assets   # public read
```

Use Signed URLs or Cloud CDN for private content. Link the bucket to a custom
domain with Cloud Storage Static Website Hosting or Cloud CDN.

---

## 3. Amazon S3

1. Create a bucket in the S3 console.
2. Block public access (unless serving static assets directly).
3. Create an IAM user with `AmazonS3FullAccess` (restrict later).
4. Save the access key ID and secret.
5. Configure a bucket policy or CloudFront distribution for hosting.

Install the AWS SDK:

```bash
npm install @aws-sdk/client-s3
```

---

## 4. Cloudflare R2

1. Enable R2 and create a bucket.
2. Generate an access key pair.
3. Optional: create a public bucket with a custom domain via Cloudflare Workers.

Install the S3-compatible client (same as S3) and use the R2 endpoint:

```ts
const client = new S3Client({
  region: "auto",
  endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.R2_ACCESS_KEY_ID!,
    secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
  },
});
```

---

## 5. CDN Integration

- **Cloud CDN (GCP)**: enable on a backend bucket or serverless NEG.
- **CloudFront (AWS)**: front S3 buckets or HTTP origins, configure cache policies.
- **Cloudflare**: attach Workers/R2 to serve globally cached assets.

Update `.env` with `CDN_URL` so frontend code references the cached endpoint.

---

## 6. Operational Checklist

- [ ] Version objects or enable lifecycle policies to manage costs.
- [ ] Enforce encryption at rest (default for most providers).
- [ ] Rotate credentials and store them via the process in
      [`SECRETS_MANAGEMENT.md`](./SECRETS_MANAGEMENT.md).
- [ ] Document storage decisions in `.cfoi/branches/<branch>/DECISIONS.md`.

