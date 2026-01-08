import { ApolloServer } from '@apollo/server';
import { startStandaloneServer } from '@apollo/server/standalone';
import { typeDefs } from './schema/typeDefs';
import { resolvers } from './resolvers';
import * as dotenv from 'dotenv';

dotenv.config();

const server = new ApolloServer({
  typeDefs,
  resolvers,
  introspection: process.env.NODE_ENV !== 'production', // Disable in production
  plugins: [
    {
      async requestDidStart() {
        return {
          async didEncounterErrors(ctx) {
            console.error('GraphQL Error:', ctx.errors);
          },
        };
      },
    },
  ],
});

async function startServer() {
  const { url } = await startStandaloneServer(server, {
    listen: { port: parseInt(process.env.PORT || '4000') },
    context: async ({ req }) => {
      // Add authentication, database connections, etc.
      return {
        // user: await getUserFromToken(req.headers.authorization),
        // db: database,
      };
    },
  });

  console.log(`🚀 GraphQL Server ready at ${url}`);
  console.log(`📊 Explore at ${url}graphql`);
}

startServer().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
