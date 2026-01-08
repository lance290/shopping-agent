# Docker Templates

This directory contains Docker templates for different services and applications in the monorepo framework.

---

## 📁 Template Structure

```
infra/docker/templates/
├── nodejs/                 # Node.js applications
│   ├── Dockerfile         # Production build
│   ├── Dockerfile.dev     # Development with hot reload
│   └── README.md          # Node.js setup guide
├── react/                  # React/Next.js applications
│   ├── Dockerfile         # Production build
│   ├── Dockerfile.dev     # Development with hot reload
│   └── README.md          # React setup guide
├── postgres/               # PostgreSQL database
│   ├── docker-compose.yml # Standalone PostgreSQL
│   ├── init/              # Database initialization scripts
│   ├── backups/           # Database backup directory
│   └── README.md          # PostgreSQL setup guide
├── redis/                  # Redis cache
│   ├── docker-compose.yml # Standalone Redis
│   ├── redis.conf         # Redis configuration
│   ├── backups/           # Redis backup directory
│   └── README.md          # Redis setup guide
├── mongodb/                # MongoDB document database
│   ├── docker-compose.yml # Standalone MongoDB
│   ├── init/              # Database initialization scripts
│   ├── backups/           # MongoDB backup directory
│   └── README.md          # MongoDB setup guide
└── neo4j/                  # Neo4j graph database
    ├── docker-compose.yml # Standalone Neo4j
    ├── init/              # Database initialization scripts
    ├── backups/           # Neo4j backup directory
    └── README.md          # Neo4j setup guide
```

---

## 🚀 Quick Start

### Using Templates in Your Project

1. **Copy the template to your app directory:**
```bash
# For a React frontend
cp -r infra/docker/templates/react/* apps/frontend/

# For a Node.js backend
cp -r infra/docker/templates/nodejs/* apps/backend/

# For a standalone database
cp -r infra/docker/templates/postgres/* ./postgres/
```

2. **Customize environment variables:**
```bash
# Copy and edit the environment file
cp .env.example .env
# Edit .env with your configuration
```

3. **Start the services:**
```bash
# Start full monorepo stack
docker-compose -f docker-compose.dev.yml up -d

# Start standalone database
cd postgres/
docker-compose up -d
```

---

## 🐳 Application Templates

### React/Next.js Template

**Features:**
- Multi-stage production build
- Hot reload in development
- Optimized for Railway and GCP Cloud Run
- Health checks included
- Non-root user for security

**Usage:**
```bash
# Development
docker build -f Dockerfile.dev -t my-frontend:dev .
docker run -p 3000:3000 my-frontend:dev

# Production
docker build -t my-frontend:prod .
docker run -p 3000:3000 my-frontend:prod
```

**Environment Variables:**
- `NODE_ENV` - Environment (development/production)
- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_WS_URL` - WebSocket URL

### Node.js Template

**Features:**
- TypeScript support
- Multi-stage build
- Development with nodemon
- Production optimization
- Health checks included

**Usage:**
```bash
# Development
docker build -f Dockerfile.dev -t my-backend:dev .
docker run -p 8080:8080 my-backend:dev

# Production
docker build -t my-backend:prod .
docker run -p 8080:8080 my-backend:prod
```

**Environment Variables:**
- `NODE_ENV` - Environment (development/production)
- `PORT` - Application port
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection string

---

## 🗄️ Database Templates

### PostgreSQL Template

**Features:**
- PostgreSQL 15 Alpine
- Health checks
- Persistent data volumes
- Optional pgAdmin for management
- Optional PostgREST for REST API

**Services:**
- `postgres` - Main database service
- `pgadmin` - Database management UI (profile: admin)
- `postgrest` - REST API endpoint (profile: api)

**Environment Variables:**
```bash
POSTGRES_DB=myapp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_PORT=5432
```

**Usage:**
```bash
cd postgres/
docker-compose up -d                    # Start database only
docker-compose --profile admin up -d   # Start with pgAdmin
docker-compose --profile api up -d     # Start with PostgREST
```

### Redis Template

**Features:**
- Redis 7 Alpine
- Custom configuration support
- Health checks
- Optional Redis Commander
- Optional Redis Insight for monitoring

**Services:**
- `redis` - Main Redis service
- `redis-commander` - Web-based Redis client (profile: admin)
- `redis-insight` - Redis monitoring tool (profile: monitor)

**Environment Variables:**
```bash
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_COMMANDER_PORT=8081
REDIS_INSIGHT_PORT=8001
```

**Usage:**
```bash
cd redis/
docker-compose up -d                      # Start Redis only
docker-compose --profile admin up -d     # Start with Redis Commander
docker-compose --profile monitor up -d   # Start with Redis Insight
```

### MongoDB Template

**Features:**
- MongoDB 7
- Health checks
- Optional Mongo Express
- Authentication support
- Backup directory support

**Services:**
- `mongodb` - Main MongoDB service
- `mongo-express` - Web-based MongoDB client (profile: admin)
- `mongo-gui` - Alternative MongoDB GUI (profile: gui)

**Environment Variables:**
```bash
MONGODB_PORT=27017
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=password
MONGO_DATABASE=myapp
```

**Usage:**
```bash
cd mongodb/
docker-compose up -d                  # Start MongoDB only
docker-compose --profile admin up -d # Start with Mongo Express
docker-compose --profile gui up -d   # Start with GUI
```

### Neo4j Template

**Features:**
- Neo4j 5 Community
- APOC and Graph Data Science plugins
- Health checks
- Optional GraphQL endpoint
- Optional Bloom visualization

**Services:**
- `neo4j` - Main Neo4j service
- `graphql` - GraphQL endpoint (profile: graphql)
- `bloom` - Neo4j Bloom visualization (profile: bloom)

**Environment Variables:**
```bash
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
NEO4J_PASSWORD=password
NEO4J_HEAP_INITIAL=512m
NEO4J_HEAP_MAX=1G
NEO4J_PAGECACHE=512m
```

**Usage:**
```bash
cd neo4j/
docker-compose up -d                    # Start Neo4j only
docker-compose --profile graphql up -d # Start with GraphQL
docker-compose --profile bloom up -d   # Start with Bloom
```

---

## 🔧 Configuration

### Environment Files

Each template includes environment variable support:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

### Custom Configuration

**PostgreSQL:**
```bash
# Custom PostgreSQL configuration
cp /path/to/postgresql.conf postgres/
# Edit postgres/docker-compose.yml to mount the config
```

**Redis:**
```bash
# Custom Redis configuration
cp /path/to/redis.conf redis/
# Template automatically mounts redis.conf
```

**Neo4j:**
```bash
# Custom Neo4j configuration
cp /path/to/neo4j.conf neo4j/
# Edit neo4j/docker-compose.yml to mount the config
```

---

## 📊 Monitoring and Health Checks

All templates include health checks:

```bash
# Check service health
docker-compose ps

# View health check logs
docker-compose logs <service-name>

# Monitor resource usage
docker stats
```

**Health Check Endpoints:**
- React: `http://localhost:3000`
- Node.js: `http://localhost:8080/health`
- PostgreSQL: `pg_isready` command
- Redis: `redis-cli ping` command
- MongoDB: `mongosh --eval` command
- Neo4j: `cypher-shell` command

---

## 🔄 Backup and Restore

### PostgreSQL
```bash
# Backup
docker-compose exec postgres pg_dump -U postgres myapp > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres myapp < backup.sql
```

### Redis
```bash
# Backup
docker-compose exec redis redis-cli BGSAVE

# Restore (copy RDB file to data directory)
docker-compose cp backup.rdb redis:/data/dump.rdb
docker-compose restart redis
```

### MongoDB
```bash
# Backup
docker-compose exec mongodb mongodump --out /backups/$(date +%Y%m%d)

# Restore
docker-compose exec mongodb mongorestore /backups/20231201/myapp
```

### Neo4j
```bash
# Backup
docker-compose exec neo4j neo4j-admin database dump neo4j --to-path=/backups/

# Restore
docker-compose exec neo4j neo4j-admin database load neo4j --from-path=/backups/
```

---

## 🚀 Production Deployment

### Build Production Images
```bash
# Build all services
docker-compose -f docker-compose.prod.yml build

# Build specific service
docker-compose -f docker-compose.prod.yml build frontend
```

### Deploy to Railway
```bash
# Use Railway CLI
railway up

# Deploy specific service
railway up frontend
```

### Deploy to GCP Cloud Run
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/project-id/service-name

# Deploy to Cloud Run
gcloud run deploy service-name --image gcr.io/project-id/service-name
```

---

## 🛠️ Troubleshooting

### Common Issues

**Port Conflicts:**
```bash
# Check what's using the port
lsof -i :3000

# Change port in .env file
echo "FRONTEND_PORT=3001" >> .env
```

**Permission Issues:**
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./volumes/
```

**Memory Issues:**
```bash
# Increase Docker memory limits
# In Docker Desktop: Settings > Resources > Memory
```

### Debug Commands

```bash
# View logs
docker-compose logs <service-name>

# Execute commands in container
docker-compose exec <service-name> bash

# Inspect container
docker inspect <container-name>
```

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis)
- [MongoDB Docker Hub](https://hub.docker.com/_/mongo)
- [Neo4j Docker Hub](https://hub.docker.com/_/neo4j)

---

**Questions?** Check the individual template README files or create an issue on GitHub.
