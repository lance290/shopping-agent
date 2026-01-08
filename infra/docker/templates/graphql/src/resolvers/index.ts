// Mock data (replace with database in production)
const users = [
  { id: '1', name: 'Alice', email: 'alice@example.com', createdAt: new Date().toISOString() },
  { id: '2', name: 'Bob', email: 'bob@example.com', createdAt: new Date().toISOString() },
];

const posts = [
  {
    id: '1',
    title: 'Getting Started with GraphQL',
    content: 'GraphQL is a query language for APIs...',
    authorId: '1',
    published: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: '2',
    title: 'Apollo Server Best Practices',
    content: 'Learn how to build production-ready GraphQL APIs...',
    authorId: '1',
    published: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

export const resolvers = {
  Query: {
    users: () => users,
    
    user: (_: any, { id }: { id: string }) => 
      users.find(user => user.id === id),
    
    posts: (_: any, { published }: { published?: boolean }) => {
      if (published === undefined) return posts;
      return posts.filter(post => post.published === published);
    },
    
    post: (_: any, { id }: { id: string }) => 
      posts.find(post => post.id === id),
    
    health: () => 'OK',
  },

  Mutation: {
    createUser: (_: any, { input }: any) => {
      const newUser = {
        id: String(users.length + 1),
        ...input,
        createdAt: new Date().toISOString(),
      };
      users.push(newUser);
      return newUser;
    },

    createPost: (_: any, { input }: any) => {
      const newPost = {
        id: String(posts.length + 1),
        ...input,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      posts.push(newPost);
      return newPost;
    },

    updatePost: (_: any, { id, input }: any) => {
      const postIndex = posts.findIndex(post => post.id === id);
      if (postIndex === -1) return null;
      
      posts[postIndex] = {
        ...posts[postIndex],
        ...input,
        updatedAt: new Date().toISOString(),
      };
      return posts[postIndex];
    },

    deletePost: (_: any, { id }: { id: string }) => {
      const index = posts.findIndex(post => post.id === id);
      if (index === -1) return false;
      posts.splice(index, 1);
      return true;
    },
  },

  // Field resolvers
  User: {
    posts: (user: any) => posts.filter(post => post.authorId === user.id),
  },

  Post: {
    author: (post: any) => users.find(user => user.id === post.authorId),
  },
};
