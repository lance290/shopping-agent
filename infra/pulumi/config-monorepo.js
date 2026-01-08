#!/usr/bin/env node

/**
 * Monorepo Pulumi Configuration Helper
 * 
 * This script helps generate and manage Pulumi configurations
 * for different monorepo deployment scenarios.
 */

const fs = require('fs');
const path = require('path');

// Configuration presets for common scenarios
const presets = {
  'fullstack': {
    description: 'Full-stack application with frontend, backend, and PostgreSQL',
    config: {
      frontend: true,
      backend: true,
      admin: false,
      worker: false,
      postgres: true,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
  'fullstack-cache': {
    description: 'Full-stack application with Redis caching',
    config: {
      frontend: true,
      backend: true,
      admin: false,
      worker: false,
      postgres: true,
      redis: true,
      mongodb: false,
      neo4j: false,
    }
  },
  'microservices': {
    description: 'Microservices architecture with all services',
    config: {
      frontend: true,
      backend: true,
      admin: true,
      worker: true,
      postgres: true,
      redis: true,
      mongodb: false,
      neo4j: false,
    }
  },
  'data-heavy': {
    description: 'Data-heavy application with multiple databases',
    config: {
      frontend: true,
      backend: true,
      admin: false,
      worker: true,
      postgres: true,
      redis: true,
      mongodb: true,
      neo4j: true,
    }
  },
  'api-only': {
    description: 'API-only backend service',
    config: {
      frontend: false,
      backend: true,
      admin: false,
      worker: false,
      postgres: true,
      redis: true,
      mongodb: false,
      neo4j: false,
    }
  },
  'frontend-only': {
    description: 'Frontend-only application',
    config: {
      frontend: true,
      backend: false,
      admin: false,
      worker: false,
      postgres: false,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  }
};

function showUsage() {
  console.log(`
Usage: node config-monorepo.js <command> [options]

Commands:
  list-presets                    List available configuration presets
  generate <preset> <stack>       Generate Pulumi stack config from preset
  set-config <stack> <key> <val>  Set a specific configuration value
  get-config <stack> [key]        Get configuration value(s)
  validate <stack>                Validate stack configuration
  estimate-cost <stack>           Estimate monthly costs (rough estimate)

Examples:
  node config-monorepo.js list-presets
  node config-monorepo.js generate fullstack dev
  node config-monorepo.js set-config dev postgresTier db-g1-small
  node config-monorepo.js get-config dev postgresTier
  node config-monorepo.js validate dev
  `);
}

function listPresets() {
  console.log('\nAvailable Configuration Presets:');
  console.log('==================================');
  
  Object.entries(presets).forEach(([name, preset]) => {
    console.log(`\n${name}:`);
    console.log(`  ${preset.description}`);
    console.log('  Services:');
    
    const services = Object.entries(preset.config)
      .filter(([key]) => ['frontend', 'backend', 'admin', 'worker'].includes(key))
      .filter(([, enabled]) => enabled)
      .map(([key]) => `    - ${key}`);
    
    const databases = Object.entries(preset.config)
      .filter(([key]) => ['postgres', 'redis', 'mongodb', 'neo4j'].includes(key))
      .filter(([, enabled]) => enabled)
      .map(([key]) => `    - ${key}`);
    
    if (services.length > 0) {
      console.log(services.join('\n'));
    }
    
    if (databases.length > 0) {
      console.log('  Databases:');
      console.log(databases.join('\n'));
    }
  });
}

function generateConfig(presetName, stackName) {
  const preset = presets[presetName];
  if (!preset) {
    console.error(`Error: Unknown preset '${presetName}'`);
    console.log('Use "list-presets" to see available presets');
    process.exit(1);
  }

  const configPath = path.join(__dirname, `Pulumi.${stackName}.yaml`);
  
  console.log(`Generating configuration for stack '${stackName}' using preset '${presetName}'`);
  console.log(`Configuration will be saved to: ${configPath}`);
  
  // Start with base configuration
  let config = `# Pulumi Stack Configuration: ${stackName}
# Generated from preset: ${presetName}
# Description: ${preset.description}
# Generated on: ${new Date().toISOString()}

name: monorepo-deployment
runtime: nodejs
description: "Monorepo infrastructure for ${stackName}"

config:
  # GCP Configuration
  region:
    type: string
    default: "us-central1"
  
  # Application Configuration
  appName:
    type: string
    default: "${stackName}"
  
  # Branch Configuration (set during deployment)
  branch:
    type: string
    default: "main"
`;

  // Add service and database configuration from preset
  Object.entries(preset.config).forEach(([key, value]) => {
    config += `  ${key}:\n    type: boolean\n    default: ${value}\n`;
  });

  // Add default service configurations
  config += `
  # Frontend Configuration
  frontendPort:
    type: integer
    default: 3000
  
  frontendCpu:
    type: string
    default: "1000m"
  
  frontendMemory:
    type: string
    default: "512Mi"
  
  frontendMaxInstances:
    type: integer
    default: 10
  
  frontendConcurrency:
    type: integer
    default: 100
  
  # Backend Configuration
  backendPort:
    type: integer
    default: 8080
  
  backendCpu:
    type: string
    default: "1000m"
  
  backendMemory:
    type: string
    default: "512Mi"
  
  backendMaxInstances:
    type: integer
    default: 10
  
  backendConcurrency:
    type: integer
    default: 100
  
  # Worker Configuration
  workerCpu:
    type: string
    default: "500m"
  
  workerMemory:
    type: string
    default: "256Mi"
  
  workerMaxInstances:
    type: integer
    default: 3
  
  workerConcurrency:
    type: integer
    default: 1
  
  # PostgreSQL Configuration
  postgresTier:
    type: string
    default: "db-f1-micro"
  
  postgresDiskSize:
    type: integer
    default: 10
  
  postgresVersion:
    type: string
    default: "POSTGRES_15"
  
  # Redis Configuration
  redisTier:
    type: string
    default: "BASIC"
  
  redisMemorySize:
    type: integer
    default: 1
  
  redisVersion:
    type: string
    default: "REDIS_7_0"
  
  # MongoDB Configuration
  mongodbTier:
    type: string
    default: "M0"
  
  # Neo4j Configuration
  neo4jTier:
    type: string
    default: "db-n1-standard-1"
  
  neo4jDiskSize:
    type: integer
    default: 10
`;

  fs.writeFileSync(configPath, config);
  console.log(`✅ Configuration saved to ${configPath}`);
  
  // Show what will be deployed
  console.log('\nThis configuration will deploy:');
  const enabledServices = Object.entries(preset.config)
    .filter(([, enabled]) => enabled)
    .map(([key]) => `  - ${key}`);
  console.log(enabledServices.join('\n'));
}

function setConfig(stackName, key, value) {
  const configPath = path.join(__dirname, `Pulumi.${stackName}.yaml`);
  
  if (!fs.existsSync(configPath)) {
    console.error(`Error: Stack configuration '${stackName}' not found`);
    console.log('Use "generate <preset> <stack>" to create a new stack configuration');
    process.exit(1);
  }
  
  console.log(`Setting ${key} = ${value} for stack '${stackName}'`);
  
  // Read existing config
  let config = fs.readFileSync(configPath, 'utf8');
  
  // Simple regex replacement (works for basic cases)
  const regex = new RegExp(`(\\s+${key}:\\s+default:\\s+)[^\\s]+`, 'i');
  const match = config.match(regex);
  
  if (match) {
    config = config.replace(regex, `$1${value}`);
    fs.writeFileSync(configPath, config);
    console.log(`✅ Updated ${key} = ${value}`);
  } else {
    console.error(`Error: Could not find configuration key '${key}'`);
  }
}

function getConfig(stackName, key = null) {
  const configPath = path.join(__dirname, `Pulumi.${stackName}.yaml`);
  
  if (!fs.existsSync(configPath)) {
    console.error(`Error: Stack configuration '${stackName}' not found`);
    process.exit(1);
  }
  
  const config = fs.readFileSync(configPath, 'utf8');
  
  if (key) {
    // Get specific key
    const regex = new RegExp(`\\s+${key}:\\s+default:\\s+([^\\s]+)`, 'i');
    const match = config.match(regex);
    
    if (match) {
      console.log(`${key}: ${match[1]}`);
    } else {
      console.error(`Error: Configuration key '${key}' not found`);
    }
  } else {
    // Show all configuration
    console.log(`\nConfiguration for stack '${stackName}':`);
    console.log('==========================================');
    console.log(config);
  }
}

function validateConfig(stackName) {
  const configPath = path.join(__dirname, `Pulumi.${stackName}.yaml`);
  
  if (!fs.existsSync(configPath)) {
    console.error(`Error: Stack configuration '${stackName}' not found`);
    process.exit(1);
  }
  
  console.log(`Validating configuration for stack '${stackName}'...`);
  
  const config = fs.readFileSync(configPath, 'utf8');
  
  // Basic validation checks
  const checks = [
    {
      name: 'Has region configuration',
      test: /region:/i.test(config),
    },
    {
      name: 'Has appName configuration',
      test: /appName:/i.test(config),
    },
    {
      name: 'Has at least one service enabled',
      test: /(frontend|backend|admin|worker):\s+default:\s+true/i.test(config),
    },
    {
      name: 'Has valid service configuration',
      test: /frontend:\s+type:\s+boolean/i.test(config),
    },
  ];
  
  let passed = 0;
  let total = checks.length;
  
  checks.forEach(check => {
    if (check.test) {
      console.log(`✅ ${check.name}`);
      passed++;
    } else {
      console.log(`❌ ${check.name}`);
    }
  });
  
  console.log(`\nValidation: ${passed}/${total} checks passed`);
  
  if (passed === total) {
    console.log('✅ Configuration is valid!');
  } else {
    console.log('❌ Configuration has issues that need to be fixed');
    process.exit(1);
  }
}

function estimateCost(stackName) {
  const configPath = path.join(__dirname, `Pulumi.${stackName}.yaml`);
  
  if (!fs.existsSync(configPath)) {
    console.error(`Error: Stack configuration '${stackName}' not found`);
    process.exit(1);
  }
  
  const config = fs.readFileSync(configPath, 'utf8');
  
  console.log(`\nCost Estimate for stack '${stackName}':`);
  console.log('=====================================');
  console.log('⚠️  These are rough estimates. Actual costs may vary.');
  
  // Parse enabled services
  const enabledServices = [];
  const enabledDatabases = [];
  
  if (/frontend:\s+default:\s+true/i.test(config)) enabledServices.push('Frontend');
  if (/backend:\s+default:\s+true/i.test(config)) enabledServices.push('Backend');
  if (/admin:\s+default:\s+true/i.test(config)) enabledServices.push('Admin');
  if (/worker:\s+default:\s+true/i.test(config)) enabledServices.push('Worker');
  
  if (/postgres:\s+default:\s+true/i.test(config)) enabledDatabases.push('PostgreSQL');
  if (/redis:\s+default:\s+true/i.test(config)) enabledDatabases.push('Redis');
  if (/mongodb:\s+default:\s+true/i.test(config)) enabledDatabases.push('MongoDB');
  if (/neo4j:\s+default:\s+true/i.test(config)) enabledDatabases.push('Neo4j');
  
  // Rough cost estimates (per month)
  const costs = {
    'Frontend': { min: 0, max: 50 },      // Cloud Run
    'Backend': { min: 0, max: 100 },      // Cloud Run
    'Admin': { min: 0, max: 30 },         // Cloud Run
    'Worker': { min: 0, max: 40 },        // Cloud Run
    'PostgreSQL': { min: 10, max: 200 },  // Cloud SQL
    'Redis': { min: 7, max: 50 },         // Memorystore
    'MongoDB': { min: 9, max: 25 },       // MongoDB Atlas
    'Neo4j': { min: 50, max: 500 },       // Neo4j Aura
  };
  
  let totalMin = 0;
  let totalMax = 0;
  
  console.log('\nServices:');
  enabledServices.forEach(service => {
    const cost = costs[service];
    console.log(`  ${service}: $${cost.min} - $${cost.max}/month`);
    totalMin += cost.min;
    totalMax += cost.max;
  });
  
  console.log('\nDatabases:');
  enabledDatabases.forEach(database => {
    const cost = costs[database];
    console.log(`  ${database}: $${cost.min} - $${cost.max}/month`);
    totalMin += cost.min;
    totalMax += cost.max;
  });
  
  console.log(`\nTotal Estimated Cost: $${totalMin} - $${totalMax}/month`);
  console.log('\nNote: These estimates assume moderate usage.');
  console.log('Actual costs depend on traffic, storage, and compute usage.');
}

// Main execution
const command = process.argv[2];

switch (command) {
  case 'list-presets':
    listPresets();
    break;
  case 'generate':
    if (process.argv.length !== 5) {
      console.error('Usage: generate <preset> <stack>');
      process.exit(1);
    }
    generateConfig(process.argv[3], process.argv[4]);
    break;
  case 'set-config':
    if (process.argv.length !== 6) {
      console.error('Usage: set-config <stack> <key> <value>');
      process.exit(1);
    }
    setConfig(process.argv[3], process.argv[4], process.argv[5]);
    break;
  case 'get-config':
    if (process.argv.length < 4) {
      console.error('Usage: get-config <stack> [key]');
      process.exit(1);
    }
    getConfig(process.argv[3], process.argv[4]);
    break;
  case 'validate':
    if (process.argv.length !== 4) {
      console.error('Usage: validate <stack>');
      process.exit(1);
    }
    validateConfig(process.argv[3]);
    break;
  case 'estimate-cost':
    if (process.argv.length !== 4) {
      console.error('Usage: estimate-cost <stack>');
      process.exit(1);
    }
    estimateCost(process.argv[3]);
    break;
  default:
    showUsage();
    process.exit(1);
}
