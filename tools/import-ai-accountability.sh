#!/usr/bin/env bash
# Import AI Accountability Framework into Existing Project
# Usage: ./import-ai-accountability.sh /path/to/target/project

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  AI Accountability Framework Importer${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Check if target directory provided
if [ $# -eq 0 ]; then
  echo -e "${RED}❌ Error: Please provide target project directory${NC}"
  echo ""
  echo "Usage: $0 /path/to/target/project"
  echo ""
  echo "Example:"
  echo "  $0 ~/projects/my-app"
  echo "  $0 ../my-existing-project"
  exit 1
fi

TARGET_DIR="$1"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Verify source directory
if [ ! -d "$SOURCE_DIR/.windsurf/workflows" ]; then
  echo -e "${RED}❌ Error: Source directory doesn't look like the workflow pack${NC}"
  echo "Expected to find .windsurf/workflows/"
  exit 1
fi

# Verify target directory exists
if [ ! -d "$TARGET_DIR" ]; then
  echo -e "${RED}❌ Error: Target directory doesn't exist: $TARGET_DIR${NC}"
  exit 1
fi

# Verify target is a git repo (optional check)
if [ ! -d "$TARGET_DIR/.git" ]; then
  echo -e "${YELLOW}⚠️  Warning: Target directory is not a git repository${NC}"
  read -p "Continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo -e "${BLUE}Source:${NC} $SOURCE_DIR"
echo -e "${BLUE}Target:${NC} $TARGET_DIR"
echo ""

# Confirm
read -p "Import AI accountability framework to target directory? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 1
fi

echo ""
echo -e "${BLUE}📦 Importing AI Accountability Framework...${NC}"
echo ""

# Create necessary directories
echo -e "${BLUE}1/5${NC} Creating directories..."
mkdir -p "$TARGET_DIR/.windsurf/workflows"
mkdir -p "$TARGET_DIR/tools"
echo -e "${GREEN}   ✓ Directories created${NC}"

# Copy constitution
echo -e "${BLUE}2/5${NC} Copying constitution..."
if [ -f "$TARGET_DIR/.windsurf/constitution.md" ]; then
  echo -e "${YELLOW}   ⚠️  constitution.md already exists${NC}"
  read -p "   Overwrite? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    cp "$SOURCE_DIR/.windsurf/constitution.md" "$TARGET_DIR/.windsurf/constitution.md"
    echo -e "${GREEN}   ✓ Constitution overwritten${NC}"
  else
    echo -e "${YELLOW}   ⊘ Skipped constitution${NC}"
  fi
else
  cp "$SOURCE_DIR/.windsurf/constitution.md" "$TARGET_DIR/.windsurf/constitution.md"
  echo -e "${GREEN}   ✓ Constitution copied${NC}"
fi

# Copy accountability workflow
echo -e "${BLUE}3/5${NC} Copying accountability workflow..."
cp "$SOURCE_DIR/.windsurf/workflows/ai-accountability.md" "$TARGET_DIR/.windsurf/workflows/ai-accountability.md"
echo -e "${GREEN}   ✓ Workflow copied${NC}"

# Copy verification script
echo -e "${BLUE}4/5${NC} Copying verification script..."
cp "$SOURCE_DIR/tools/verify-implementation.sh" "$TARGET_DIR/tools/verify-implementation.sh"
chmod +x "$TARGET_DIR/tools/verify-implementation.sh"
echo -e "${GREEN}   ✓ Verification script copied${NC}"

# Copy checklist template
echo -e "${BLUE}5/5${NC} Copying checklist template..."
cp "$SOURCE_DIR/tools/ai-checklist-template.md" "$TARGET_DIR/tools/ai-checklist-template.md"
echo -e "${GREEN}   ✓ Checklist template copied${NC}"

echo ""
echo -e "${BLUE}📚 Copying documentation...${NC}"

# Copy guides (optional)
if [ -f "$SOURCE_DIR/KEEPING_AI_HONEST.md" ]; then
  cp "$SOURCE_DIR/KEEPING_AI_HONEST.md" "$TARGET_DIR/KEEPING_AI_HONEST.md"
  echo -e "${GREEN}   ✓ KEEPING_AI_HONEST.md copied${NC}"
fi

if [ -f "$SOURCE_DIR/ADDING_AI_ACCOUNTABILITY_TO_EXISTING_PROJECT.md" ]; then
  cp "$SOURCE_DIR/ADDING_AI_ACCOUNTABILITY_TO_EXISTING_PROJECT.md" "$TARGET_DIR/ADDING_AI_ACCOUNTABILITY_TO_EXISTING_PROJECT.md"
  echo -e "${GREEN}   ✓ Integration guide copied${NC}"
fi

echo ""
echo -e "${GREEN}✅ Import complete!${NC}"
echo ""

# Test the verification script
echo -e "${BLUE}🧪 Testing verification script...${NC}"
cd "$TARGET_DIR"
if ./tools/verify-implementation.sh > /dev/null 2>&1; then
  echo -e "${GREEN}   ✓ Verification script works!${NC}"
else
  echo -e "${YELLOW}   ⚠️  Verification script exited with error (expected if no staged files)${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✨ Setup Complete! Next Steps:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo "1. Read the guide:"
echo -e "   ${BLUE}cat KEEPING_AI_HONEST.md${NC}"
echo ""
echo "2. Test verification:"
echo -e "   ${BLUE}./tools/verify-implementation.sh${NC}"
echo ""
echo "3. Share with team:"
echo -e "   ${BLUE}# Print quick reference card from KEEPING_AI_HONEST.md${NC}"
echo ""
echo "4. Start enforcing:"
echo -e "   ${BLUE}# Run verification before every commit${NC}"
echo ""
echo -e "${YELLOW}Optional: Set up git hooks${NC}"
echo "   See ADDING_AI_ACCOUNTABILITY_TO_EXISTING_PROJECT.md"
echo "   Section: 'Detailed Setup (If You Want Git Hooks Too)'"
echo ""
echo -e "${GREEN}Happy coding with accountable AI! 🚀${NC}"
echo ""
