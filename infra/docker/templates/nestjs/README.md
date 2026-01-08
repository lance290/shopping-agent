# NestJS Docker Template

Production-ready NestJS template with TypeScript, Docker optimization, and modern best practices.

## Features

- **NestJS 10** with TypeScript
- **Global validation** with class-validator
- **CORS** configuration
- **Health check** endpoint
- **Multi-stage Docker build** for minimal image size
- **Security hardening** (non-root user, dumb-init)
- **Railway & GCP Cloud Run** optimized
- **Graceful shutdown** hooks

## Project Structure

```
src/
├── health/
│   └── health.controller.ts   # Health check endpoint
├── app.controller.ts           # Main controller
├── app.service.ts              # Main service
├── app.module.ts               # Root module
└── main.ts                     # Bootstrap file
```

## Getting Started

### Local Development

```bash
npm install
npm run start:dev
```

Open [http://localhost:8080/api](http://localhost:8080/api)

### Docker Build

```bash
docker build -t nestjs-app .
docker run -p 8080:8080 nestjs-app
```

### Environment Variables

Create `.env` for development:

```env
PORT=8080
CORS_ORIGIN=http://localhost:3000
NODE_ENV=development
```

## API Endpoints

### Root
```bash
GET /api
```
Returns: `Hello from NestJS!`

### Health Check
```bash
GET /health
```
Returns:
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T00:00:00.000Z",
  "service": "nestjs-app",
  "version": "0.1.0"
}
```

## Deployment

### Railway

```bash
railway up
```

### GCP Cloud Run

```bash
gcloud run deploy nestjs-app \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Pulumi

See `infra/pulumi/README.md` for automated infrastructure deployment.

## Testing

```bash
# unit tests
npm run test

# e2e tests
npm run test:e2e

# test coverage
npm run test:cov
```

## Performance Optimizations

- ✅ Multi-stage Docker build (reduced image size)
- ✅ Production dependencies only in final image
- ✅ Validation pipe for request DTOs
- ✅ Graceful shutdown hooks
- ✅ CORS configuration

## Security Features

- ✅ Non-root user
- ✅ Dumb-init for signal handling
- ✅ Minimal Alpine base image
- ✅ Whitelist validation (forbid unknown properties)
- ✅ Global pipes for automatic validation
