import gql from 'graphql-tag';

export const typeDefs = gql`
  """
  A user in the system
  """
  type User {
    id: ID!
    name: String!
    email: String!
    posts: [Post!]!
    createdAt: String!
  }

  """
  A blog post
  """
  type Post {
    id: ID!
    title: String!
    content: String!
    author: User!
    published: Boolean!
    createdAt: String!
    updatedAt: String!
  }

  """
  Input for creating a new user
  """
  input CreateUserInput {
    name: String!
    email: String!
  }

  """
  Input for creating a new post
  """
  input CreatePostInput {
    title: String!
    content: String!
    authorId: ID!
    published: Boolean = false
  }

  """
  Input for updating a post
  """
  input UpdatePostInput {
    title: String
    content: String
    published: Boolean
  }

  """
  Query operations
  """
  type Query {
    """
    Get all users
    """
    users: [User!]!
    
    """
    Get a single user by ID
    """
    user(id: ID!): User
    
    """
    Get all posts, optionally filtered by published status
    """
    posts(published: Boolean): [Post!]!
    
    """
    Get a single post by ID
    """
    post(id: ID!): Post
    
    """
    Health check endpoint
    """
    health: String!
  }

  """
  Mutation operations
  """
  type Mutation {
    """
    Create a new user
    """
    createUser(input: CreateUserInput!): User!
    
    """
    Create a new post
    """
    createPost(input: CreatePostInput!): Post!
    
    """
    Update an existing post
    """
    updatePost(id: ID!, input: UpdatePostInput!): Post
    
    """
    Delete a post
    """
    deletePost(id: ID!): Boolean!
  }

  """
  Subscription operations (real-time updates)
  """
  type Subscription {
    """
    Subscribe to new posts
    """
    postCreated: Post!
  }
`;
