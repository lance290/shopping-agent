const pulumi = require("@pulumi/pulumi");
const gcp = require("@pulumi/gcp");

// Get configuration
const config = new pulumi.Config();
const projectId = gcp.config.project || "your-gcp-project";
const region = config.get("region") || "us-central1";
const branchName = config.get("branch") || "main";
const appName = config.get("appName") || "tech-stack-app";

// Technology stack configuration
const frontendTech = config.get("frontendTech") || "none";
const backendTech = config.get("backendTech") || "none";

// Database configuration
const databases = {
  postgres: config.getBoolean("postgres") ?? false,
  redis: config.getBoolean("redis") ?? false,
  mongodb: config.getBoolean("mongodb") ?? false,
  neo4j: config.getBoolean("neo4j") ?? false,
};

// Technology-specific configurations
const techConfig = {
  nextjs: {
    port: config.getNumber("frontendPort") || 3000,
    cpu: config.get("frontendCpu") || "1000m",
    memory: config.get("frontendMemory") || "512Mi",
    maxInstances: config.getNumber("frontendMaxInstances") || 10,
    image: `gcr.io/${projectId}/nextjs:latest`,
  },
  svelte: {
    port: config.getNumber("frontendPort") || 3000,
    cpu: config.get("frontendCpu") || "1000m",
    memory: config.get("frontendMemory") || "512Mi",
    maxInstances: config.getNumber("frontendMaxInstances") || 10,
    image: `gcr.io/${projectId}/svelte:latest`,
  },
  'react-vite': {
    port: config.getNumber("frontendPort") || 3000,
    cpu: config.get("frontendCpu") || "1000m",
    memory: config.get("frontendMemory") || "512Mi",
    maxInstances: config.getNumber("frontendMaxInstances") || 10,
    image: `gcr.io/${projectId}/react:latest`,
  },
  nestjs: {
    port: config.getNumber("backendPort") || 8080,
    cpu: config.get("backendCpu") || "1000m",
    memory: config.get("backendMemory") || "512Mi",
    maxInstances: config.getNumber("backendMaxInstances") || 10,
    image: `gcr.io/${projectId}/nestjs:latest`,
  },
  fastify: {
    port: config.getNumber("backendPort") || 8080,
    cpu: config.get("backendCpu") || "1000m",
    memory: config.get("backendMemory") || "512Mi",
    maxInstances: config.getNumber("backendMaxInstances") || 10,
    image: `gcr.io/${projectId}/fastify:latest`,
  },
  nodejs: {
    port: config.getNumber("backendPort") || 8080,
    cpu: config.get("backendCpu") || "1000m",
    memory: config.get("backendMemory") || "512Mi",
    maxInstances: config.getNumber("backendMaxInstances") || 10,
    image: `gcr.io/${projectId}/nodejs:latest`,
  },
};

// Sanitize branch name for GCP resource naming
const sanitizedBranch = branchName
  .toLowerCase()
  .replace(/[^a-z0-9-]/g, "-")
  .substring(0, 30);

// Enable required APIs
const enabledApis = [
  "run.googleapis.com",
  "cloudbuild.googleapis.com",
  "containerregistry.googleapis.com",
];

// Add database APIs based on configuration
if (databases.postgres) enabledApis.push("sqladmin.googleapis.com");
if (databases.redis) enabledApis.push("redis.googleapis.com");

// Enable APIs
const enabledApiServices = enabledApis.map((api) =>
  new gcp.projects.Service(`enable-${api.replace(/\./g, "-")}`, {
    project: projectId,
    service: api,
    disableOnDestroy: false,
  }),
);

// Helper function to create Cloud Run service
function createCloudRunService(serviceName, tech, envVars = [], dependsOn = []) {
  const serviceConfig = techConfig[tech];
  
  return new gcp.cloudrun.Service(serviceName, {
    name: serviceName,
    location: region,
    project: projectId,
    template: {
      spec: {
        containers: [{
          image: serviceConfig.image,
          ports: [{
            containerPort: serviceConfig.port,
          }],
          env: [
            {
              name: "BRANCH_NAME",
              value: branchName,
            },
            {
              name: "ENVIRONMENT",
              value: "production",
            },
            {
              name: "TECH_STACK",
              value: tech,
            },
            ...envVars,
          ],
          resources: {
            limits: {
              cpu: serviceConfig.cpu,
              memory: serviceConfig.memory,
            },
          },
        }],
        containerConcurrency: 100,
        timeoutSeconds: 300,
      },
      metadata: {
        annotations: {
          "autoscaling.knative.dev/maxScale": serviceConfig.maxInstances.toString(),
          "run.googleapis.com/cpu-throttling": "false",
        },
      },
    },
    traffic: [{
      percent: 100,
      latestRevision: true,
    }],
  }, {
    dependsOn: [...enabledApiServices, ...dependsOn],
  });
}

// Helper function to make service publicly accessible
function makeServicePublic(serviceName, cloudRunService) {
  return new gcp.cloudrun.IamMember(`${serviceName}-public`, {
    service: cloudRunService.name,
    location: cloudRunService.location,
    project: cloudRunService.project,
    role: "roles/run.invoker",
    member: "allUsers",
  });
}

// Create databases
const createdDatabases = {};

if (databases.postgres) {
  const postgresTier = config.get("postgresTier") || "db-f1-micro";
  const postgresDiskSize = config.getNumber("postgresDiskSize") || 10;
  const postgresVersion = config.get("postgresVersion") || "POSTGRES_15";

  const postgresInstance = new gcp.sql.DatabaseInstance(`${appName}-postgres`, {
    name: `${appName}-postgres-${sanitizedBranch}`,
    project: projectId,
    region: region,
    databaseVersion: postgresVersion,
    settings: {
      tier: postgresTier,
      diskSize: postgresDiskSize,
      ipConfiguration: {
        ipv4Enabled: true,
        authorizedNetworks: [{
          name: "all",
          value: "0.0.0.0/0",
        }],
      },
    },
    deletionProtection: false,
  }, {
    dependsOn: enabledApiServices,
  });

  const postgresDatabase = new gcp.sql.Database(`${appName}-postgres-db`, {
    name: "myapp",
    project: projectId,
    instance: postgresInstance.name,
  });

  createdDatabases.postgres = {
    instance: postgresInstance,
    database: postgresDatabase,
    connectionName: postgresInstance.connectionName,
    ipAddress: postgresInstance.publicIpAddress,
  };
}

if (databases.redis) {
  const redisTier = config.get("redisTier") || "BASIC";
  const redisMemorySize = config.getNumber("redisMemorySize") || 1;
  const redisVersion = config.get("redisVersion") || "REDIS_7_0";

  const redisInstance = new gcp.redis.Instance(`${appName}-redis`, {
    name: `${appName}-redis-${sanitizedBranch}`,
    project: projectId,
    region: region,
    tier: redisTier,
    memorySizeGb: redisMemorySize,
    authorizedNetwork: "default",
    redisVersion: redisVersion,
    displayName: `${appName} Redis (${sanitizedBranch})`,
  }, {
    dependsOn: enabledApiServices,
  });

  createdDatabases.redis = {
    instance: redisInstance,
    host: redisInstance.host,
    port: redisInstance.port,
  };
}

// Create services
const createdServices = {};
const serviceUrls = {};

// Deploy frontend if configured
if (frontendTech !== 'none' && techConfig[frontendTech]) {
  const frontendEnvVars = [];
  
  // Add backend URL if backend exists
  if (backendTech !== 'none') {
    frontendEnvVars.push({
      name: "NEXT_PUBLIC_API_URL",
      value: pulumi.interpolate`https://${appName}-backend-${sanitizedBranch}.a.run.app`,
    });
  }

  const frontendService = createCloudRunService(
    `${appName}-frontend-${sanitizedBranch}`,
    frontendTech,
    frontendEnvVars
  );
  
  makeServicePublic(`${appName}-frontend-${sanitizedBranch}`, frontendService);
  
  createdServices.frontend = frontendService;
  serviceUrls.frontend = frontendService.status.url;
}

// Deploy backend if configured
if (backendTech !== 'none' && techConfig[backendTech]) {
  const backendEnvVars = [];
  
  // Add database connection strings
  if (databases.postgres) {
    backendEnvVars.push({
      name: "DATABASE_URL",
      value: pulumi.interpolate`postgresql://postgres@${createdDatabases.postgres.ipAddress}/myapp`,
    });
  }
  
  if (databases.redis) {
    backendEnvVars.push({
      name: "REDIS_URL",
      value: pulumi.interpolate`redis://${createdDatabases.redis.host}:${createdDatabases.redis.port}`,
    });
  }

  const backendService = createCloudRunService(
    `${appName}-backend-${sanitizedBranch}`,
    backendTech,
    backendEnvVars,
    Object.values(createdDatabases).map(db => db.instance || db)
  );
  
  makeServicePublic(`${appName}-backend-${sanitizedBranch}`, backendService);
  
  createdServices.backend = backendService;
  serviceUrls.backend = backendService.status.url;
}

// Export outputs
exports.techStack = {
  frontend: frontendTech,
  backend: backendTech,
  databases: Object.keys(databases).filter(db => databases[db]),
};
exports.serviceUrls = serviceUrls;
exports.services = createdServices;
exports.databases = createdDatabases;
exports.projectId = projectId;
exports.region = region;
exports.branchName = branchName;
exports.appName = appName;
