#!/usr/bin/env node

/**
 * Railway Monorepo Configuration Helper
 * 
 * This script helps configure Railway services for monorepo deployments.
 * It generates railway.json files for different service types and manages
 * environment variables across services.
 */

const fs = require('fs');
const path = require('path');

// Service templates
const serviceTemplates = {
  'frontend': {
    description: 'React/Next.js frontend application',
    template: 'frontend.json',
    defaultPort: 3000,
    healthPath: '/',
    environments: ['production', 'staging', 'development']
  },
  'backend': {
    description: 'Node.js/Express API backend',
    template: 'backend.json',
    defaultPort: 8080,
    healthPath: '/health',
    environments: ['production', 'staging', 'development']
  },
  'admin': {
    description: 'Admin dashboard interface',
    template: 'admin.json',
    defaultPort: 3000,
    healthPath: '/',
    environments: ['production', 'staging', 'development']
  },
  'worker': {
    description: 'Background job processor',
    template: 'worker.json',
    defaultPort: null,
    healthPath: '/health',
    environments: ['production', 'staging', 'development']
  }
};

function showUsage() {
  console.log(`
Usage: node config-railway.js <command> [options]

Commands:
  list-templates                 List available service templates
  generate <service> <path>       Generate railway.json for a service
  setup-monorepo <project-path>   Set up Railway configs for entire monorepo
  validate <path>                 Validate railway.json configuration
  list-services <project-path>    List configured services in monorepo
  add-env <path> <key> <value>    Add environment variable to service

Examples:
  node config-railway.js list-templates
  node config-railway.js generate frontend ./apps/frontend
  node config-railway.js setup-monorepo ./my-mvp
  node config-railway.js validate ./apps/backend
  node config-railway.js add-env ./apps/backend API_URL https://api.example.com
  `);
}

function listTemplates() {
  console.log('\nAvailable Railway Service Templates:');
  console.log('=====================================');
  
  Object.entries(serviceTemplates).forEach(([name, template]) => {
    console.log(`\n${name}:`);
    console.log(`  ${template.description}`);
    console.log(`  Default Port: ${template.defaultPort || 'N/A'}`);
    console.log(`  Health Path: ${template.healthPath}`);
    console.log(`  Environments: ${template.environments.join(', ')}`);
  });
}

function generateServiceConfig(serviceType, targetPath) {
  const template = serviceTemplates[serviceType];
  if (!template) {
    console.error(`Error: Unknown service type '${serviceType}'`);
    console.log('Use "list-templates" to see available service types');
    process.exit(1);
  }

  const templatePath = path.join(__dirname, 'templates', template.template);
  const outputPath = path.join(targetPath, 'railway.json');

  if (!fs.existsSync(templatePath)) {
    console.error(`Error: Template file not found: ${templatePath}`);
    process.exit(1);
  }

  if (!fs.existsSync(targetPath)) {
    console.error(`Error: Target directory does not exist: ${targetPath}`);
    process.exit(1);
  }

  // Read and copy template
  const templateContent = fs.readFileSync(templatePath, 'utf8');
  fs.writeFileSync(outputPath, templateContent);

  console.log(`✅ Generated railway.json for ${serviceType} service`);
  console.log(`   Template: ${template.template}`);
  console.log(`   Output: ${outputPath}`);
  console.log(`   Description: ${template.description}`);
}

function setupMonorepo(projectPath) {
  console.log(`Setting up Railway configuration for monorepo at: ${projectPath}`);
  
  if (!fs.existsSync(projectPath)) {
    console.error(`Error: Project directory does not exist: ${projectPath}`);
    process.exit(1);
  }

  // Define expected monorepo structure
  const expectedServices = {
    'apps/frontend': 'frontend',
    'apps/backend': 'backend',
    'apps/admin': 'admin',
    'apps/worker': 'worker'
  };

  let configuredServices = [];

  Object.entries(expectedServices).forEach(([servicePath, serviceType]) => {
    const fullPath = path.join(projectPath, servicePath);
    
    if (fs.existsSync(fullPath)) {
      console.log(`\n🔧 Configuring ${serviceType} service...`);
      
      // Copy template
      const templatePath = path.join(__dirname, 'templates', `${serviceType}.json`);
      const outputPath = path.join(fullPath, 'railway.json');
      
      if (fs.existsSync(templatePath)) {
        const templateContent = fs.readFileSync(templatePath, 'utf8');
        fs.writeFileSync(outputPath, templateContent);
        console.log(`   ✅ Created: railway.json`);
        configuredServices.push(serviceType);
      } else {
        console.log(`   ⚠️  Template not found: ${serviceType}.json`);
      }
    } else {
      console.log(`⏭️  Skipping ${serviceType} (directory not found: ${servicePath})`);
    }
  });

  // Create Railway project configuration
  const railwayConfig = {
    name: path.basename(projectPath),
    services: configuredServices,
    environments: ['production', 'staging', 'development'],
    plugins: ['postgresql', 'redis'],
    created: new Date().toISOString()
  };

  const configOutputPath = path.join(projectPath, 'railway-project.json');
  fs.writeFileSync(configOutputPath, JSON.stringify(railwayConfig, null, 2));
  
  console.log(`\n✅ Railway monorepo setup complete!`);
  console.log(`   Configured services: ${configuredServices.join(', ')}`);
  console.log(`   Project config: ${configOutputPath}`);
  
  if (configuredServices.length > 0) {
    console.log(`\n📋 Next steps:`);
    console.log(`   1. cd ${projectPath}`);
    console.log(`   2. railway login`);
    console.log(`   3. railway link`);
    console.log(`   4. Deploy individual services:`);
    configuredServices.forEach(service => {
      console.log(`      railway up --service ${service}`);
    });
  }
}

function validateConfig(configPath) {
  const railwayJsonPath = path.join(configPath, 'railway.json');
  
  if (!fs.existsSync(railwayJsonPath)) {
    console.error(`Error: railway.json not found in ${configPath}`);
    process.exit(1);
  }

  console.log(`Validating Railway configuration: ${railwayJsonPath}`);
  
  try {
    const config = JSON.parse(fs.readFileSync(railwayJsonPath, 'utf8'));
    
    // Validation checks
    const checks = [
      {
        name: 'Has valid schema',
        test: config.$schema === 'https://railway.app/railway.schema.json',
      },
      {
        name: 'Has build configuration',
        test: config.build && config.build.builder && config.build.dockerfilePath,
      },
      {
        name: 'Has deploy configuration',
        test: config.deploy && config.deploy.startCommand,
      },
      {
        name: 'Has health check configuration',
        test: config.deploy.healthcheckPath || config.deploy.healthcheckPort,
      },
      {
        name: 'Has environment configurations',
        test: config.environments && Object.keys(config.environments).length > 0,
      }
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

    // Show configuration summary
    console.log(`\n📋 Configuration Summary:`);
    console.log(`   Builder: ${config.build.builder}`);
    console.log(`   Dockerfile: ${config.build.dockerfilePath}`);
    console.log(`   Start Command: ${config.deploy.startCommand}`);
    console.log(`   Health Path: ${config.deploy.healthcheckPath || 'N/A'}`);
    console.log(`   Environments: ${Object.keys(config.environments).join(', ')}`);

  } catch (error) {
    console.error(`❌ Invalid JSON in railway.json: ${error.message}`);
    process.exit(1);
  }
}

function listServices(projectPath) {
  console.log(`Scanning for Railway services in: ${projectPath}`);
  
  if (!fs.existsSync(projectPath)) {
    console.error(`Error: Project directory does not exist: ${projectPath}`);
    process.exit(1);
  }

  // Scan for railway.json files
  const services = [];
  
  function scanDirectory(dir, relativePath = '') {
    const items = fs.readdirSync(dir);
    
    items.forEach(item => {
      const fullPath = path.join(dir, item);
      const itemRelativePath = path.join(relativePath, item);
      
      if (fs.statSync(fullPath).isDirectory()) {
        // Check for railway.json
        const railwayJsonPath = path.join(fullPath, 'railway.json');
        if (fs.existsSync(railwayJsonPath)) {
          try {
            const config = JSON.parse(fs.readFileSync(railwayJsonPath, 'utf8'));
            services.push({
              path: itemRelativePath,
              fullPath: fullPath,
              config: config
            });
          } catch (error) {
            console.log(`⚠️  Invalid railway.json in ${itemRelativePath}: ${error.message}`);
          }
        } else {
          // Recursively scan subdirectories
          scanDirectory(fullPath, itemRelativePath);
        }
      }
    });
  }

  scanDirectory(projectPath);

  if (services.length === 0) {
    console.log('❌ No Railway services found');
    console.log('   Use "setup-monorepo" to configure services');
    return;
  }

  console.log(`\n🚂 Found ${services.length} Railway service(s):`);
  console.log('==========================================');
  
  services.forEach(service => {
    console.log(`\n📁 ${service.path}:`);
    console.log(`   Builder: ${service.config.build?.builder || 'N/A'}`);
    console.log(`   Dockerfile: ${service.config.build?.dockerfilePath || 'N/A'}`);
    console.log(`   Start Command: ${service.config.deploy?.startCommand || 'N/A'}`);
    console.log(`   Health Path: ${service.config.deploy?.healthcheckPath || 'N/A'}`);
    console.log(`   Environments: ${Object.keys(service.config.environments || {}).join(', ') || 'N/A'}`);
  });

  console.log(`\n📋 Deployment Commands:`);
  services.forEach(service => {
    console.log(`   cd ${service.path} && railway up`);
  });
}

function addEnvironmentVariable(configPath, key, value) {
  const railwayJsonPath = path.join(configPath, 'railway.json');
  
  if (!fs.existsSync(railwayJsonPath)) {
    console.error(`Error: railway.json not found in ${configPath}`);
    process.exit(1);
  }

  if (!key || !value) {
    console.error('Error: Both key and value are required');
    console.log('Usage: add-env <path> <key> <value>');
    process.exit(1);
  }

  try {
    const config = JSON.parse(fs.readFileSync(railwayJsonPath, 'utf8'));
    
    // Add variable to all environments
    if (!config.environments) {
      config.environments = {};
    }
    
    Object.keys(config.environments).forEach(env => {
      if (!config.environments[env].variables) {
        config.environments[env].variables = {};
      }
      config.environments[env].variables[key] = value;
    });

    // Write updated config
    fs.writeFileSync(railwayJsonPath, JSON.stringify(config, null, 2));
    
    console.log(`✅ Added environment variable:`);
    console.log(`   Key: ${key}`);
    console.log(`   Value: ${value}`);
    console.log(`   Path: ${railwayJsonPath}`);
    console.log(`   Environments: ${Object.keys(config.environments).join(', ')}`);
    
  } catch (error) {
    console.error(`❌ Error updating railway.json: ${error.message}`);
    process.exit(1);
  }
}

// Main execution
const command = process.argv[2];

switch (command) {
  case 'list-templates':
    listTemplates();
    break;
  case 'generate':
    if (process.argv.length !== 5) {
      console.error('Usage: generate <service> <path>');
      process.exit(1);
    }
    generateServiceConfig(process.argv[3], process.argv[4]);
    break;
  case 'setup-monorepo':
    if (process.argv.length !== 4) {
      console.error('Usage: setup-monorepo <project-path>');
      process.exit(1);
    }
    setupMonorepo(process.argv[3]);
    break;
  case 'validate':
    if (process.argv.length !== 4) {
      console.error('Usage: validate <path>');
      process.exit(1);
    }
    validateConfig(process.argv[3]);
    break;
  case 'list-services':
    if (process.argv.length !== 4) {
      console.error('Usage: list-services <project-path>');
      process.exit(1);
    }
    listServices(process.argv[3]);
    break;
  case 'add-env':
    if (process.argv.length !== 6) {
      console.error('Usage: add-env <path> <key> <value>');
      process.exit(1);
    }
    addEnvironmentVariable(process.argv[3], process.argv[4], process.argv[5]);
    break;
  default:
    showUsage();
    process.exit(1);
}
