#!/usr/bin/env node

/**
 * Tech-Stack-Aware Pulumi Configuration Helper
 *
 * Supports specific technologies (NextJS, NestJS, Fastify, Svelte, etc.)
 * instead of generic "frontend" and "backend" labels.
 */

const fs = require('fs');
const path = require('path');
// Available technology options
const techOptions = {
  frontend: {
    nextjs: { port: 3000, name: 'Next.js', template: 'nextjs' },
    svelte: { port: 3000, name: 'SvelteKit', template: 'svelte' },
    'react-vite': { port: 3000, name: 'React + Vite', template: 'react' },
  },
  backend: {
    nestjs: { port: 8080, name: 'NestJS', template: 'nestjs' },
    fastify: { port: 8080, name: 'Fastify', template: 'fastify' },
    nodejs: { port: 8080, name: 'Node.js', template: 'nodejs' },
  },
  databases: ['postgres', 'redis', 'mongodb', 'neo4j'],
};
// Tech stack presets
const presets = {
  'nextjs-nestjs': {
    description: 'Next.js frontend + NestJS backend + PostgreSQL',
    config: {
      frontendTech: 'nextjs',
      backendTech: 'nestjs',
      postgres: true,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
  'nextjs-fastify': {
    description: 'Next.js frontend + Fastify backend + PostgreSQL',
    config: {
      frontendTech: 'nextjs',
      backendTech: 'fastify',
      postgres: true,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
  'svelte-nestjs': {
    description: 'Svelte frontend + NestJS backend + PostgreSQL',
    config: {
      frontendTech: 'svelte',
      backendTech: 'nestjs',
      postgres: true,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
  'svelte-fastify': {
    description: 'Svelte frontend + Fastify backend + PostgreSQL',
    config: {
      frontendTech: 'svelte',
      backendTech: 'fastify',
      postgres: true,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
  'api-nestjs': {
    description: 'NestJS API with PostgreSQL and Redis',
    config: {
      frontendTech: null,
      backendTech: 'nestjs',
      postgres: true,
      redis: true,
      mongodb: false,
      neo4j: false,
    }
  },
  'api-fastify': {
    description: 'Fastify API with PostgreSQL and Redis',
    config: {
      frontendTech: null,
      backendTech: 'fastify',
      postgres: true,
      redis: true,
      mongodb: false,
      neo4j: false,
    }
  },
  'nextjs-only': {
    description: 'Next.js frontend only (static or SSR)',
    config: {
      frontendTech: 'nextjs',
      backendTech: null,
      postgres: false,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
  'svelte-only': {
    description: 'SvelteKit frontend only',
    config: {
      frontendTech: 'svelte',
      backendTech: null,
      postgres: false,
      redis: false,
      mongodb: false,
      neo4j: false,
    }
  },
};
function showUsage() {
  console.log(`
Usage: node config-tech-stack.js <command> [options]

Commands:
  list-presets                           List available tech stack presets
  list-tech                              List available technologies
  generate <preset> <stack>              Generate Pulumi stack config from preset
  custom <stack> [options]               Generate custom stack configuration
  set-config <stack> <key> <val>         Set a specific configuration value
  get-config <stack> [key]               Get configuration value(s)
  validate <stack>                       Validate stack configuration

Custom Options:
  --frontend=<tech>                      Frontend technology (nextjs, svelte, react-vite)
  --backend=<tech>                       Backend technology (nestjs, fastify, nodejs)
  --postgres                             Include PostgreSQL
  --redis                                Include Redis
  --mongodb                              Include MongoDB
  --neo4j                                Include Neo4j

Examples:
  node config-tech-stack.js list-presets
  node config-tech-stack.js list-tech
  node config-tech-stack.js generate nextjs-nestjs dev
  node config-tech-stack.js custom dev --frontend=nextjs --backend=fastify --postgres --redis
  node config-tech-stack.js set-config dev postgresTier db-g1-small
  `);
}

function listPresets() {
  console.log('\nAvailable Tech Stack Presets:');
  console.log('==============================');
  
  Object.entries(presets).forEach(([name, preset]) => {
    console.log(`\n${name}:`);
    console.log(`  ${preset.description}`);
    
    const frontend = preset.config.frontendTech 
      ? techOptions.frontend[preset.config.frontendTech].name
      : 'None';
    const backend = preset.config.backendTech
      ? techOptions.backend[preset.config.backendTech].name
      : 'None';
    
    console.log(`  Frontend: ${frontend}`);
    console.log(`  Backend: ${backend}`);
    
    const databases = Object.entries(preset.config)
      .filter(([key]) => techOptions.databases.includes(key))
      .filter(([, enabled]) => enabled)
      .map(([key]) => `    - ${key}`);
    
    if (databases.length > 0) {
      console.log('  Databases:');
      console.log(databases.join('\n'));
    }
  });
}

function listTech() {
  console.log('\nAvailable Technologies:');
  console.log('=======================');
  
  console.log('\nFrontend:');
  Object.entries(techOptions.frontend).forEach(([key, tech]) => {
    console.log(`  ${key.padEnd(15)} - ${tech.name} (port: ${tech.port})`);
  });
  
  console.log('\nBackend:');
  Object.entries(techOptions.backend).forEach(([key, tech]) => {
    console.log(`  ${key.padEnd(15)} - ${tech.name} (port: ${tech.port})`);
  });
  
  console.log('\nDatabases:');
  techOptions.databases.forEach(db => {
    console.log(`  - ${db}`);
  });
}

function generateConfig(presetName, stackName) {
  const preset = presets[presetName];
  if (!preset) {
    console.error(`Error: Unknown preset '${presetName}'`);
    console.log('Use "list-presets" to see available presets');
    process.exit(1);
  }

  writeStackConfig(stackName, preset.config, preset.description);
}

function generateCustomConfig(stackName, args) {
  const config = {
    frontendTech: null,
    backendTech: null,
    postgres: false,
    redis: false,
    mongodb: false,
    neo4j: false,
  };

  // Parse custom arguments
  args.forEach(arg => {
    if (arg.startsWith('--frontend=')) {
      const tech = arg.split('=')[1];
      if (!techOptions.frontend[tech]) {
        console.error(`Error: Unknown frontend technology '${tech}'`);
        process.exit(1);
      }
      config.frontendTech = tech;
    } else if (arg.startsWith('--backend=')) {
      const tech = arg.split('=')[1];
      if (!techOptions.backend[tech]) {
        console.error(`Error: Unknown backend technology '${tech}'`);
        process.exit(1);
      }
      config.backendTech = tech;
    } else if (arg === '--postgres') {
      config.postgres = true;
    } else if (arg === '--redis') {
      config.redis = true;
    } else if (arg === '--mongodb') {
      config.mongodb = true;
    } else if (arg === '--neo4j') {
      config.neo4j = true;
    }
  });

  const description = 'Custom tech stack configuration';
  writeStackConfig(stackName, config, description);
}

function writeStackConfig(stackName, config, description) {
  const configPath = path.join(__dirname, `Pulumi.${stackName}.yaml`);
  
  console.log(`Generating configuration for stack '${stackName}'`);
  console.log(`Configuration will be saved to: ${configPath}`);
  
  // Start with base configuration
  let yamlConfig = `# Pulumi Stack Configuration: ${stackName}
# Description: ${description}
# Generated on: ${new Date().toISOString()}

name: tech-stack-deployment
runtime: nodejs
description: "Tech-specific infrastructure for ${stackName}"

config:
  # GCP Configuration
  region:
    type: string
    default: "us-central1"
  
  # Application Configuration
  appName:
    type: string
    default: "${stackName}"
  
  # Branch Configuration
  branch:
    type: string
    default: "main"
  
  # Technology Stack Configuration
  frontendTech:
    type: string
    default: "${config.frontendTech || 'none'}"
  
  backendTech:
    type: string
    default: "${config.backendTech || 'none'}"
`;

  // Add database configuration
  Object.entries(config)
    .filter(([key]) => techOptions.databases.includes(key))
    .forEach(([key, value]) => {
      yamlConfig += `  ${key}:\n    type: boolean\n    default: ${value}\n`;
    });

  // Add service-specific configurations based on selected tech
  if (config.frontendTech) {
    const frontendInfo = techOptions.frontend[config.frontendTech];
    yamlConfig += `
  # Frontend (${frontendInfo.name}) Configuration
  frontendPort:
    type: integer
    default: ${frontendInfo.port}
  
  frontendCpu:
    type: string
    default: "1000m"
  
  frontendMemory:
    type: string
    default: "512Mi"
  
  frontendMaxInstances:
    type: integer
    default: 10
`;
  }

  if (config.backendTech) {
    const backendInfo = techOptions.backend[config.backendTech];
    yamlConfig += `
  # Backend (${backendInfo.name}) Configuration
  backendPort:
    type: integer
    default: ${backendInfo.port}
  
  backendCpu:
    type: string
    default: "1000m"
  
  backendMemory:
    type: string
    default: "512Mi"
  
  backendMaxInstances:
    type: integer
    default: 10
`;
  }

  // Add database-specific configurations
  if (config.postgres) {
    yamlConfig += `
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
`;
  }

  if (config.redis) {
    yamlConfig += `
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
`;
  }

  if (config.mongodb) {
    yamlConfig += `
  # MongoDB Configuration
  mongodbTier:
    type: string
    default: "M0"
`;
  }

  if (config.neo4j) {
    yamlConfig += `
  # Neo4j Configuration
  neo4jTier:
    type: string
    default: "db-n1-standard-1"
  
  neo4jDiskSize:
    type: integer
    default: 10
`;
  }

  fs.writeFileSync(configPath, yamlConfig);
  console.log(`✅ Configuration saved to ${configPath}`);
  
  // Show what will be deployed
  console.log('\nThis configuration will deploy:');
  if (config.frontendTech) {
    console.log(`  ✓ Frontend: ${techOptions.frontend[config.frontendTech].name}`);
  }
  if (config.backendTech) {
    console.log(`  ✓ Backend: ${techOptions.backend[config.backendTech].name}`);
  }
  
  const databases = Object.entries(config)
    .filter(([key]) => techOptions.databases.includes(key))
    .filter(([, enabled]) => enabled)
    .map(([key]) => key);
  
  if (databases.length > 0) {
    console.log(`  ✓ Databases: ${databases.join(', ')}`);
  }
}

// Main execution
const command = process.argv[2];

switch (command) {
  case 'list-presets':
    listPresets();
    break;
  case 'list-tech':
    listTech();
    break;
  case 'generate':
    if (process.argv.length !== 5) {
      console.error('Usage: generate <preset> <stack>');
      process.exit(1);
    }
    generateConfig(process.argv[3], process.argv[4]);
    break;
  case 'custom':
    if (process.argv.length < 4) {
      console.error('Usage: custom <stack> [options]');
      process.exit(1);
    }
    generateCustomConfig(process.argv[3], process.argv.slice(4));
    break;
  default:
    showUsage();
    process.exit(1);
}
