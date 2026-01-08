# GraphQL API Server (Apollo Server)

Production-ready GraphQL API with **Apollo Server 4**, TypeScript, and modern best practices.

---

## Why GraphQL?

**vs REST API:**

```
REST:
GET /users          → All users
GET /users/1        → User #1
GET /users/1/posts  → User's posts
= 3 separate requests

GraphQL:
POST /graphql
{
  user(id: 1) {
    name
    posts { title }
  }
}
= 1 request, exact data needed
```

**Benefits:**
- ✅ Single endpoint
- ✅ Request only what you need
- ✅ Strongly typed
- ✅ Self-documenting
- ✅ Real-time with subscriptions

---

## Quick Start

```bash
# Install dependencies
npm install

# Development
npm run dev

# Build
npm run build

# Production
npm start

# Docker
docker build -t graphql-api .
docker run -p 4000:4000 graphql-api
```

**Access GraphQL Playground**: http://localhost:4000/graphql

---

## Example Queries

### Get All Users
```graphql
query {
  users {
    id
    name
    email
  }
}
```

### Get User with Posts
```graphql
query {
  user(id: "1") {
    name
    email
    posts {
      title
      published
    }
  }
}
```

### Get Published Posts Only
```graphql
query {
  posts(published: true) {
    id
    title
    author {
      name
    }
  }
}
```

---

## Example Mutations

### Create User
```graphql
mutation {
  createUser(input: {
    name: "Charlie"
    email: "charlie@example.com"
  }) {
    id
    name
    email
  }
}
```

### Create Post
```graphql
mutation {
  createPost(input: {
    title: "My First Post"
    content: "This is the content..."
    authorId: "1"
    published: true
  }) {
    id
    title
    published
  }
}
```

### Update Post
```graphql
mutation {
  updatePost(
    id: "1"
    input: { published: true }
  ) {
    id
    title
    published
  }
}
```

---

## Schema Structure

### Types
- **User** - User accounts
- **Post** - Blog posts

### Queries
- `users` - Get all users
- `user(id)` - Get single user
- `posts(published)` - Get posts (optionally filtered)
- `post(id)` - Get single post
- `health` - Health check

### Mutations
- `createUser` - Create new user
- `createPost` - Create new post
- `updatePost` - Update existing post
- `deletePost` - Delete post

---

## Adding Database

### With Prisma (PostgreSQL)

```bash
# Install
npm install @prisma/client
npm install -D prisma

# Initialize
npx prisma init

# Define schema in prisma/schema.prisma
model User {
  id    String @id @default(cuid())
  name  String
  email String @unique
  posts Post[]
}

# Generate client
npx prisma generate

# Use in resolvers
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const resolvers = {
  Query: {
    users: () => prisma.user.findMany(),
    user: (_, { id }) => prisma.user.findUnique({ where: { id } }),
  },
};
```

### With MongoDB

```bash
# Install
npm install mongodb

# Connect
import { MongoClient } from 'mongodb';

const client = new MongoClient(process.env.DATABASE_URL);
await client.connect();

const db = client.db('myapp');

const resolvers = {
  Query: {
    users: () => db.collection('users').find().toArray(),
  },
};
```

---

## Authentication

### JWT Authentication

```typescript
// src/auth.ts
import jwt from 'jsonwebtoken';

export function getUserFromToken(token?: string) {
  if (!token) return null;
  try {
    return jwt.verify(token.replace('Bearer ', ''), process.env.JWT_SECRET);
  } catch {
    return null;
  }
}

// src/index.ts
context: async ({ req }) => ({
  user: await getUserFromToken(req.headers.authorization),
}),

// In resolver
Query: {
  me: (_, __, { user }) => {
    if (!user) throw new Error('Not authenticated');
    return user;
  },
},
```

---

## Error Handling

### Custom Errors

```typescript
import { GraphQLError } from 'graphql';

const resolvers = {
  Query: {
    user: (_, { id }) => {
      const user = users.find(u => u.id === id);
      if (!user) {
        throw new GraphQLError('User not found', {
          extensions: {
            code: 'USER_NOT_FOUND',
            http: { status: 404 },
          },
        });
      }
      return user;
    },
  },
};
```

---

## Real-Time with Subscriptions

```typescript
// Install
npm install graphql-subscriptions

// Setup
import { PubSub } from 'graphql-subscriptions';

const pubsub = new PubSub();

const resolvers = {
  Mutation: {
    createPost: async (_, { input }) => {
      const post = { /* ... */ };
      
      // Publish event
      await pubsub.publish('POST_CREATED', { postCreated: post });
      
      return post;
    },
  },
  
  Subscription: {
    postCreated: {
      subscribe: () => pubsub.asyncIterator(['POST_CREATED']),
    },
  },
};
```

**Client (subscribe to new posts):**
```graphql
subscription {
  postCreated {
    id
    title
    author { name }
  }
}
```

---

## Performance Optimization

### DataLoader (N+1 Problem)

```bash
npm install dataloader
```

```typescript
import DataLoader from 'dataloader';

const userLoader = new DataLoader(async (userIds) => {
  const users = await db.user.findMany({
    where: { id: { in: userIds } }
  });
  return userIds.map(id => users.find(u => u.id === id));
});

const resolvers = {
  Post: {
    author: (post) => userLoader.load(post.authorId), // Batched!
  },
};
```

### Query Complexity Limits

```typescript
import { createComplexityLimitRule } from 'graphql-validation-complexity';

const server = new ApolloServer({
  validationRules: [createComplexityLimitRule(1000)],
});
```

---

## Production Best Practices

### 1. **Disable Introspection**
```typescript
introspection: process.env.NODE_ENV !== 'production'
```

### 2. **Add Rate Limiting**
```bash
npm install graphql-rate-limit
```

### 3. **Enable CORS**
```typescript
cors: {
  origin: process.env.ALLOWED_ORIGINS.split(','),
  credentials: true,
}
```

### 4. **Add Logging**
```typescript
plugins: [
  {
    async requestDidStart() {
      return {
        async didResolveOperation(ctx) {
          console.log('Operation:', ctx.operationName);
        },
      };
    },
  },
],
```

### 5. **Monitoring**
See `infra/docker/templates/observability` for Prometheus + Grafana setup.

---

## Testing

### Unit Tests

```typescript
// user.test.ts
import { resolvers } from './resolvers';

describe('User Queries', () => {
  it('should return all users', () => {
    const result = resolvers.Query.users();
    expect(result).toHaveLength(2);
  });
  
  it('should return user by id', () => {
    const result = resolvers.Query.user(null, { id: '1' });
    expect(result.name).toBe('Alice');
  });
});
```

### Integration Tests

```typescript
import { ApolloServer } from '@apollo/server';

const testServer = new ApolloServer({ typeDefs, resolvers });

const response = await testServer.executeOperation({
  query: 'query { users { id name } }',
});

expect(response.body.kind).toBe('single');
expect(response.body.singleResult.data.users).toBeDefined();
```

---

## Deployment

### Railway
```bash
railway up
# Auto-detects Node.js, runs npm start
```

### GCP Cloud Run
```bash
gcloud run deploy graphql-api \
  --source . \
  --platform managed \
  --region us-central1
```

### Docker Compose

```yaml
services:
  graphql-api:
    build: .
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=postgresql://...
      - JWT_SECRET=...
```

---

## GraphQL vs REST

| Feature | GraphQL | REST |
|---------|---------|------|
| **Endpoints** | 1 (`/graphql`) | Many (`/users`, `/posts`) |
| **Data Fetching** | Exact data needed | Fixed responses |
| **Over-fetching** | ❌ Never | ✅ Common |
| **Under-fetching** | ❌ Never | ✅ Common (N+1) |
| **Versioning** | ✅ Not needed | ⚠️ Required |
| **Documentation** | ✅ Auto-generated | ⚠️ Manual |
| **Real-time** | ✅ Subscriptions | ⚠️ WebSockets |
| **Caching** | ⚠️ Complex | ✅ HTTP caching |
| **Learning Curve** | Medium | Low |

---

## When to Use GraphQL

### ✅ Use GraphQL when:
- Mobile apps (save bandwidth)
- Complex data requirements
- Multiple clients (web, mobile, etc.)
- Rapid frontend iteration
- Real-time features

### ❌ Maybe not when:
- Simple CRUD API
- File uploads/downloads
- Caching is critical
- Team unfamiliar with GraphQL

---

## Common Patterns

### Pagination
```graphql
type Query {
  posts(offset: Int, limit: Int): PostConnection!
}

type PostConnection {
  edges: [Post!]!
  pageInfo: PageInfo!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
}
```

### Filtering
```graphql
input PostFilter {
  title_contains: String
  published: Boolean
  author_id: ID
}

type Query {
  posts(filter: PostFilter): [Post!]!
}
```

### Sorting
```graphql
enum SortOrder {
  ASC
  DESC
}

input PostSort {
  field: String!
  order: SortOrder!
}

type Query {
  posts(sort: PostSort): [Post!]!
}
```

---

## Resources

- **Apollo Server**: https://www.apollographql.com/docs/apollo-server/
- **GraphQL Spec**: https://spec.graphql.org/
- **GraphQL Playground**: https://github.com/graphql/graphql-playground
- **Best Practices**: https://graphql.org/learn/best-practices/

---

**Created:** November 16, 2025  
**Status:** Production-Ready  
**Framework:** Apollo Server 4 + TypeScript
