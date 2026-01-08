const pulumi = require("@pulumi/pulumi");
const gcp = require("@pulumi/gcp");

// Get configuration
const config = new pulumi.Config();
const projectId = gcp.config.project || "your-gcp-project";
const region = config.get("region") || "us-central1";
const branchName = config.get("branch") || "main";
const appName = config.get("appName") || "monorepo-app";

// Service configuration - enable/disable services
const services = {
  frontend: config.getBoolean("frontend") ?? true,
  backend: config.getBoolean("backend") ?? true,
  admin: config.getBoolean("admin") ?? false,
  worker: config.getBoolean("worker") ?? false,
};

// Database configuration - enable/disable databases
const databases = {
  postgres: config.getBoolean("postgres") ?? true,
  redis: config.getBoolean("redis") ?? true,
  mongodb: config.getBoolean("mongodb") ?? false,
  neo4j: config.getBoolean("neo4j") ?? false,
};

// Service configuration
const serviceConfig = {
  frontend: {
    port: config.getNumber("frontendPort") || 3000,
    cpu: config.get("frontendCpu") || "1000m",
    memory: config.get("frontendMemory") || "512Mi",
    maxInstances: config.getNumber("frontendMaxInstances") || 10,
    containerConcurrency: config.getNumber("frontendConcurrency") || 100,
  },
  backend: {
    port: config.getNumber("backendPort") || 8080,
    cpu: config.get("backendCpu") || "1000m",
    memory: config.get("backendMemory") || "512Mi",
    maxInstances: config.getNumber("backendMaxInstances") || 10,
    containerConcurrency: config.getNumber("backendConcurrency") || 100,
  },
  admin: {
    port: config.getNumber("adminPort") || 3001,
    cpu: config.get("adminCpu") || "1000m",
    memory: config.get("adminMemory") || "512Mi",
    maxInstances: config.getNumber("adminMaxInstances") || 5,
    containerConcurrency: config.getNumber("adminConcurrency") || 50,
  },
  worker: {
    cpu: config.get("workerCpu") || "500m",
    memory: config.get("workerMemory") || "256Mi",
    maxInstances: config.getNumber("workerMaxInstances") || 3,
    containerConcurrency: config.getNumber("workerConcurrency") || 1,
  },
};

// Database configuration
const databaseConfig = {
  postgres: {
    tier: config.get("postgresTier") || "db-f1-micro",
    diskSize: config.getNumber("postgresDiskSize") || 10,
    version: config.get("postgresVersion") || "POSTGRES_15",
  },
  redis: {
    tier: config.get("redisTier") || "BASIC",
    memorySizeGb: config.getNumber("redisMemorySize") || 1,
    version: config.get("redisVersion") || "REDIS_7_0",
  },
  mongodb: {
    tier: config.get("mongodbTier") || "M0",
  },
  neo4j: {
    tier: config.get("neo4jTier") || "db-n1-standard-1",
    diskSize: config.getNumber("neo4jDiskSize") || 10,
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
if (databases.mongodb) enabledApis.push("mongodbatlas.googleapis.com");
if (databases.neo4j) enabledApis.push("servicedirectory.googleapis.com");

// Capture created Service resources
const enabledApiServices = enabledApis.map((api) =>
  new gcp.projects.Service(`enable-${api.replace(/\./g, "-")}`, {
    project: projectId,
    service: api,
    disableOnDestroy: false,
  }),
);

// Helper function to create Cloud Run service
function createCloudRunService(serviceName, config, envVars = [], dependsOn = []) {
  return new gcp.cloudrun.Service(serviceName, {
    name: serviceName,
    location: region,
    project: projectId,
    template: {
      spec: {
        containers: [{
          image: `gcr.io/${projectId}/${serviceName}:latest`,
          ports: config.port ? [{
            containerPort: config.port,
          }] : [],
          env: [
            {
              name: "BRANCH_NAME",
              value: branchName,
            },
            {
              name: "ENVIRONMENT",
              value: "ephemeral",
            },
            ...envVars,
          ],
          resources: {
            limits: {
              cpu: config.cpu,
              memory: config.memory,
            },
          },
        }],
        containerConcurrency: config.containerConcurrency,
        timeoutSeconds: 300,
      },
      metadata: {
        annotations: {
          "autoscaling.knative.dev/maxScale": config.maxInstances.toString(),
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
  const postgresInstance = new gcp.sql.DatabaseInstance(`${appName}-postgres`, {
    name: `${appName}-postgres-${sanitizedBranch}`,
    project: projectId,
    region: region,
    databaseVersion: databaseConfig.postgres.version,
    settings: {
      tier: databaseConfig.postgres.tier,
      diskSize: databaseConfig.postgres.diskSize,
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
  }, {
    dependsOn: [postgresInstance],
  });

  createdDatabases.postgres = {
    instance: postgresInstance,
    database: postgresDatabase,
    connectionName: postgresInstance.connectionName,
    ipAddress: postgresInstance.publicIpAddress,
  };
}

if (databases.redis) {
  const redisInstance = new gcp.redis.Instance(`${appName}-redis`, {
    name: `${appName}-redis-${sanitizedBranch}`,
    project: projectId,
    region: region,
    tier: databaseConfig.redis.tier,
    memorySizeGb: databaseConfig.redis.memorySizeGb,
    authorizedNetwork: "default",
    redisVersion: databaseConfig.redis.version,
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

if (services.frontend) {
  const frontendService = createCloudRunService(
    `${appName}-frontend-${sanitizedBranch}`,
    serviceConfig.frontend,
    [{
      name: "NEXT_PUBLIC_API_URL",
      value: services.backend ? pulumi.interpolate`https://${appName}-backend-${sanitizedBranch}-${randomSuffix}.a.run.app` : "",
    }]
  );
  
  const frontendPublic = makeServicePublic(`${appName}-frontend-${sanitizedBranch}`, frontendService);
  
  createdServices.frontend = frontendService;
  serviceUrls.frontend = frontendService.status.url;
}

if (services.backend) {
  const backendEnvVars = [];
  
  if (databases.postgres) {
    backendEnvVars.push({
      name: "DATABASE_URL",
      value: pulumi.interpolate`postgresql://postgres:${createdDatabases.postgres.instance.passwords.apply(p => p[0].password)}@${createdDatabases.postgres.ipAddress}/myapp`,
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
    serviceConfig.backend,
    backendEnvVars,
    Object.values(createdDatabases).map(db => db.instance || db)
  );
  
  const backendPublic = makeServicePublic(`${appName}-backend-${sanitizedBranch}`, backendService);
  
  createdServices.backend = backendService;
  serviceUrls.backend = backendService.status.url;
}

if (services.admin) {
  const adminService = createCloudRunService(
    `${appName}-admin-${sanitizedBranch}`,
    serviceConfig.admin,
    [{
      name: "NEXT_PUBLIC_API_URL",
      value: services.backend ? pulumi.interpolate`https://${appName}-backend-${sanitizedBranch}-${randomSuffix}.a.run.app` : "",
    }]
  );
  
  const adminPublic = makeServicePublic(`${appName}-admin-${sanitizedBranch}`, adminService);
  
  createdServices.admin = adminService;
  serviceUrls.admin = adminService.status.url;
}

if (services.worker) {
  const workerEnvVars = [];
  
  if (databases.postgres) {
    workerEnvVars.push({
      name: "DATABASE_URL",
      value: pulumi.interpolate`postgresql://postgres:${createdDatabases.postgres.instance.passwords.apply(p => p[0].password)}@${createdDatabases.postgres.ipAddress}/myapp`,
    });
  }
  
  if (databases.redis) {
    workerEnvVars.push({
      name: "REDIS_URL",
      value: pulumi.interpolate`redis://${createdDatabases.redis.host}:${createdDatabases.redis.port}`,
    });
  }

  const workerService = createCloudRunService(
    `${appName}-worker-${sanitizedBranch}`,
    serviceConfig.worker,
    workerEnvVars,
    Object.values(createdDatabases).map(db => db.instance || db)
  );
  
  // Worker services are typically not public
  createdServices.worker = workerService;
}

// Generate random suffix for unique URLs
const randomSuffix = new pulumi.random.RandomString("url-suffix", {
  length: 6,
  special: false,
  upper: false,
}).result;

// Export outputs
exports.serviceUrls = serviceUrls;
exports.services = createdServices;
exports.databases = createdDatabases;
exports.projectId = projectId;
exports.region = region;
exports.branchName = branchName;
exports.appName = appName;
