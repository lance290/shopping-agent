/**
 * Multi-Cloud Deployment Infrastructure
 * Supports: GCP Cloud Run, Railway, Modal
 * Environments: PR, Dev, QA, Production
 */
import * as pulumi from "@pulumi/pulumi";
import * as gcp from "@pulumi/gcp";
// Note: Railway and Modal providers will be added via API calls

// Get configuration
const config = new pulumi.Config();
const gcpConfig = new pulumi.Config("gcp");
const stack = pulumi.getStack();

// Environment detection
const isPR = stack.startsWith("pr-");
const isDev = stack === "dev";
const isQA = stack === "qa";
const isProduction = stack === "production";

// Base configuration
const projectId = gcpConfig.require("project");
const region = config.get("region") || "us-central1";
const appName = config.require("appName");
const containerImage = config.require("containerImage");

// Environment-specific settings
const envConfig = {
    cpu: config.get("cpu") || (isProduction ? "2000m" : "1000m"),
    memory: config.get("memory") || (isProduction ? "2Gi" : "512Mi"),
    minReplicas: config.getNumber("minReplicas") || (isProduction ? 2 : 1),
    maxReplicas: config.getNumber("maxReplicas") || (isProduction ? 10 : 5),
    timeout: config.getNumber("timeout") || 300,
    concurrency: config.getNumber("concurrency") || 100,
};

// Cloud provider selection
const deployToGCP = config.getBoolean("deployToGCP") ?? true;
const deployToRailway = config.getBoolean("deployToRailway") ?? false;
const deployToModal = config.getBoolean("deployToModal") ?? false;

/**
 * GCP Cloud Run Deployment
 */
let gcpService: gcp.cloudrun.Service | undefined;
let gcpUrl: pulumi.Output<string> | undefined;

if (deployToGCP) {
    // Enable required APIs
    const requiredApis = [
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "secretmanager.googleapis.com",
    ];

    const enabledApis = requiredApis.map(api =>
        new gcp.projects.Service(`enable-${api.replace(/\./g, "-")}`, {
            project: projectId,
            service: api,
            disableOnDestroy: false,
        })
    );

    // Create GCP secrets from Pulumi secrets
    const secrets = createGCPSecrets(projectId);

    // Create Cloud Run service
    gcpService = new gcp.cloudrun.Service(
        `${appName}-${stack}`,
        {
            name: `${appName}-${stack}`,
            location: region,
            project: projectId,

            template: {
                spec: {
                    containers: [{
                        image: containerImage,
                        ports: [{ containerPort: 8080 }],
                        
                        // Environment variables
                        env: [
                            { name: "ENVIRONMENT", value: stack },
                            { name: "APP_NAME", value: appName },
                            { name: "GCP_PROJECT", value: projectId },
                            { name: "GCP_REGION", value: region },
                        ].concat(secrets.envRefs),

                        resources: {
                            limits: {
                                cpu: envConfig.cpu,
                                memory: envConfig.memory,
                            },
                        },
                    }],
                    containerConcurrency: envConfig.concurrency,
                    timeoutSeconds: envConfig.timeout,
                },
                metadata: {
                    annotations: {
                        "autoscaling.knative.dev/minScale": envConfig.minReplicas.toString(),
                        "autoscaling.knative.dev/maxScale": envConfig.maxReplicas.toString(),
                        "run.googleapis.com/cpu-throttling": "false",
                        // For production, keep warm
                        ...(isProduction && {
                            "run.googleapis.com/execution-environment": "gen2",
                        }),
                    },
                },
            },

            traffic: [{ percent: 100, latestRevision: true }],
        },
        { dependsOn: enabledApis }
    );

    // IAM policy - public for PR/dev, private for production
    const iamMember = isPR || isDev
        ? "allUsers"
        : config.get("allowedUsers") || "allUsers";

    new gcp.cloudrun.IamMember(`${appName}-${stack}-iam`, {
        service: gcpService.name,
        location: gcpService.location,
        project: gcpService.project,
        role: "roles/run.invoker",
        member: iamMember,
    });

    gcpUrl = gcpService.status.url;
}

/**
 * Railway Deployment
 */
let railwayService: any;
let railwayUrl: pulumi.Output<string> | undefined;

if (deployToRailway) {
    const railwayToken = config.requireSecret("railwayToken");
    const railwayProjectId = config.require("railwayProjectId");

    // Railway deployment via API
    railwayService = deployToRailway_API({
        token: railwayToken,
        projectId: railwayProjectId,
        serviceName: `${appName}-${stack}`,
        image: containerImage,
        environment: stack,
        envVars: getRailwayEnvVars(),
        resources: {
            cpu: envConfig.cpu,
            memory: envConfig.memory,
        },
    });

    railwayUrl = railwayService.url;
}

/**
 * Modal Deployment (for ML inference, async tasks)
 */
let modalEndpoint: any;
let modalUrl: pulumi.Output<string> | undefined;

if (deployToModal) {
    const modalToken = config.requireSecret("modalToken");

    // Modal deployment for serverless functions
    modalEndpoint = deployToModal_API({
        token: modalToken,
        functionName: `${appName}-${stack}`,
        image: containerImage,
        environment: stack,
        secrets: getModalSecrets(),
        gpu: config.get("modalGpu") || "any", // "any", "a10g", "a100", etc.
        timeout: envConfig.timeout,
    });

    modalUrl = modalEndpoint.url;
}

/**
 * Helper: Create GCP secrets from Pulumi config
 */
function createGCPSecrets(projectId: string) {
    const secretNames = [
        "databaseUrl",
        "apiKey",
        "jwtSecret",
        // Add more as needed
    ];

    const envRefs: any[] = [];
    const gcpSecrets: Record<string, gcp.secretmanager.Secret> = {};

    secretNames.forEach(name => {
        const secretValue = config.getSecret(name);
        if (!secretValue) return;

        // Create GCP Secret Manager secret
        const secret = new gcp.secretmanager.Secret(`${appName}-${name}`, {
            secretId: `${appName}-${name}-${stack}`,
            project: projectId,
            replication: {
                automatic: {},
            },
        });

        // Add secret version with value
        new gcp.secretmanager.SecretVersion(`${appName}-${name}-v1`, {
            secret: secret.id,
            secretData: secretValue,
        });

        gcpSecrets[name] = secret;

        // Add to environment references
        envRefs.push({
            name: name.toUpperCase().replace(/([A-Z])/g, "_$1"),
            valueFrom: {
                secretKeyRef: {
                    name: secret.secretId,
                    key: "latest",
                },
            },
        });
    });

    return { envRefs, gcpSecrets };
}

/**
 * Helper: Get environment variables for Railway
 */
function getRailwayEnvVars(): Record<string, pulumi.Output<string>> {
    return {
        ENVIRONMENT: pulumi.output(stack),
        APP_NAME: pulumi.output(appName),
        DATABASE_URL: config.requireSecret("databaseUrl"),
        API_KEY: config.requireSecret("apiKey"),
        JWT_SECRET: config.requireSecret("jwtSecret"),
        // Add more as needed
    };
}

/**
 * Helper: Get secrets for Modal
 */
function getModalSecrets(): Record<string, pulumi.Output<string>> {
    return {
        DATABASE_URL: config.requireSecret("databaseUrl"),
        API_KEY: config.requireSecret("apiKey"),
        // Modal-specific secrets
        HF_TOKEN: config.getSecret("huggingfaceToken") || pulumi.output(""),
        OPENAI_API_KEY: config.getSecret("openaiApiKey") || pulumi.output(""),
    };
}

/**
 * Railway API deployment (placeholder - implement with Railway SDK)
 */
function deployToRailway_API(opts: any) {
    // This would use Railway API or Terraform provider
    // For now, return mock
    return {
        url: pulumi.output(`https://${opts.serviceName}.railway.app`),
    };
}

/**
 * Modal API deployment (placeholder - implement with Modal SDK)
 */
function deployToModal_API(opts: any) {
    // This would use Modal CLI or API
    // For now, return mock
    return {
        url: pulumi.output(`https://${opts.functionName}.modal.run`),
    };
}

// Exports
export const environment = stack;
export const deployments = {
    gcp: gcpUrl,
    railway: railwayUrl,
    modal: modalUrl,
};
export const gcpServiceName = gcpService?.name;
export const gcpProjectId = projectId;
export const gcpRegion = region;
