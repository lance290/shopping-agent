# Next.js 15 Docker Template

Production-ready Next.js 15 template with TypeScript, App Router, and Docker optimization.

## Features

- **Next.js 15** with App Router
- **TypeScript** with strict mode
- **Multi-stage Docker build** for minimal image size
- **Standalone output** for optimal Docker deployment
- **Health check endpoint** for container orchestration
- **Security hardening** (non-root user, dumb-init)
- **Railway & GCP Cloud Run** optimized

## Project Structure

```
app/
├── api/
│   └── health/
│       └── route.ts        # Health check endpoint
├── layout.tsx              # Root layout
└── page.tsx                # Home page
```

## Getting Started

### Local Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Docker Build

```bash
docker build -t nextjs-app .
docker run -p 3000:3000 nextjs-app
```

### Environment Variables

Create `.env.local` for development:

```env
NEXT_PUBLIC_API_URL=http://localhost:8080
```

## Deployment

### Railway

```bash
railway up
```

### GCP Cloud Run

```bash
gcloud run deploy nextjs-app \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Pulumi

See `infra/pulumi/README.md` for automated infrastructure deployment.

## Health Check

The app includes a health check endpoint at `/api/health`:

```bash
curl http://localhost:3000/api/health
```

Returns `{"status": "ok"}` when healthy.

## Performance Optimizations

- ✅ Standalone output (reduced bundle size)
- ✅ Image optimization (AVIF/WebP)
- ✅ Compression enabled
- ✅ Source maps disabled in production
- ✅ Telemetry disabled
- ✅ Multi-stage Docker build

## Security Features

- ✅ Non-root user
- ✅ Dumb-init for signal handling
- ✅ Minimal Alpine base image
- ✅ No poweredBy header
- ✅ Strict React mode
