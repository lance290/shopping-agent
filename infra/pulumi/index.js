const pulumi = require("@pulumi/pulumi");
const gcp = require("@pulumi/gcp");

// Get configuration
const config = new pulumi.Config();
const projectId = gcp.config.project || "your-gcp-project";
const region = config.get("region") || "us-central1";
const branchName = config.get("branch") || "main";
const appName = config.get("appName") || "ephemeral-app";

// Sanitize branch name for GCP resource naming
const sanitizedBranch = branchName
  .toLowerCase()
  .replace(/[^a-z0-9-]/g, "-")
  .substring(0, 30);
const serviceName = `${appName}-${sanitizedBranch}`;

// Enable required APIs (if not already enabled)
const enabledApis = [
  "run.googleapis.com",
  "cloudbuild.googleapis.com",
  "containerregistry.googleapis.com",
];

// Capture created Service resources so we can depend on them explicitly
const enabledApiServices = enabledApis.map((api) =>
  new gcp.projects.Service(`enable-${api.replace(/\./g, "-")}`, {
    project: projectId,
    service: api,
    disableOnDestroy: false,
  }),
);

// Create Cloud Run service
const service = new gcp.cloudrun.Service(
  serviceName,
  {
    name: serviceName,
    location: region,
    project: projectId,

    template: {
      spec: {
        containers: [
          {
            image: `gcr.io/${projectId}/${serviceName}:latest`,
            ports: [
              {
                containerPort: 8080,
              },
            ],
            env: [
              {
                name: "BRANCH_NAME",
                value: branchName,
              },
              {
                name: "ENVIRONMENT",
                value: "ephemeral",
              },
            ],
            resources: {
              limits: {
                cpu: "1000m",
                memory: "512Mi",
              },
            },
          },
        ],
        containerConcurrency: 100,
        timeoutSeconds: 300,
      },
      metadata: {
        annotations: {
          "autoscaling.knative.dev/maxScale": "10",
          "run.googleapis.com/cpu-throttling": "false",
        },
      },
    },

    traffic: [
      {
        percent: 100,
        latestRevision: true,
      },
    ],
  },
  {
    // Depend on the API enablement resources to ensure Cloud Run deploy succeeds
    dependsOn: enabledApiServices,
  },
);

// Make the service publicly accessible
const iamPolicy = new gcp.cloudrun.IamMember(`${serviceName}-public`, {
  service: service.name,
  location: service.location,
  project: service.project,
  role: "roles/run.invoker",
  member: "allUsers",
});

// NOTE: Cloud Build trigger is commented out because GitHub Actions handles deployment
// If you want to use Cloud Build instead of GitHub Actions:
// 1. Uncomment the code below
// 2. Set githubOwner and githubRepo in Pulumi config:
//    pulumi config set githubOwner your-username
//    pulumi config set githubRepo your-repo-name
// 3. Connect your GitHub repo to Cloud Build in GCP Console

/*
const githubOwner = config.get("githubOwner");
const githubRepo = config.get("githubRepo");

if (githubOwner && githubRepo) {
  const buildTrigger = new gcp.cloudbuild.Trigger(`${serviceName}-trigger`, {
    project: projectId,
    name: `${serviceName}-deploy`,
    description: `Deploy ${serviceName} on code changes`,

    github: {
      owner: githubOwner,
      name: githubRepo,
      push: {
        branch: branchName,
      },
    },

    build: {
      steps: [
        {
          name: "gcr.io/cloud-builders/docker",
          args: [
            "build",
            "-t",
            `gcr.io/${projectId}/${serviceName}:$SHORT_SHA`,
            "-t",
            `gcr.io/${projectId}/${serviceName}:latest`,
            ".",
          ],
        },
        {
          name: "gcr.io/cloud-builders/docker",
          args: ["push", `gcr.io/${projectId}/${serviceName}:$SHORT_SHA`],
        },
        {
          name: "gcr.io/cloud-builders/docker",
          args: ["push", `gcr.io/${projectId}/${serviceName}:latest`],
        },
        {
          name: "gcr.io/cloud-builders/gcloud",
          args: [
            "run",
            "deploy",
            serviceName,
            "--image",
            `gcr.io/${projectId}/${serviceName}:$SHORT_SHA`,
            "--region",
            region,
            "--platform",
            "managed",
            "--allow-unauthenticated",
          ],
        },
      ],
    },
  });
}
*/

// Export the service URL
exports.serviceUrl = service.status.url;
exports.serviceName = serviceName;
exports.projectId = projectId;
exports.region = region;
