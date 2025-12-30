#!/bin/bash

# CF-X Supabase Auto-Setup Script
# This script helps automate Supabase schema deployment
# Usage: ./scripts/setup-supabase.sh

set -e

echo "🚀 CF-X Supabase Auto-Setup"
echo "============================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo -e "${YELLOW}⚠️  Supabase CLI not found. Installing...${NC}"
    echo ""
    echo "Please install Supabase CLI:"
    echo "  npm install -g supabase"
    echo "  or"
    echo "  brew install supabase/tap/supabase"
    echo ""
    echo "Alternatively, you can run the SQL manually:"
    echo "  1. Go to Supabase Dashboard → SQL Editor"
    echo "  2. Copy contents of infra/supabase/schema.sql"
    echo "  3. Paste and run"
    exit 1
fi

echo -e "${GREEN}✓ Supabase CLI found${NC}"
echo ""

# Check if user is logged in
if ! supabase projects list &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Supabase${NC}"
    echo "Please login:"
    echo "  supabase login"
    exit 1
fi

echo -e "${GREEN}✓ Logged in to Supabase${NC}"
echo ""

# Ask for project reference
echo "Enter your Supabase project reference ID:"
echo "(Find it in Supabase Dashboard → Settings → General → Reference ID)"
read -p "Project Reference ID: " PROJECT_REF

if [ -z "$PROJECT_REF" ]; then
    echo -e "${RED}✗ Project Reference ID is required${NC}"
    exit 1
fi

echo ""
echo "Deploying schema to project: $PROJECT_REF"
echo ""

# Link to project
supabase link --project-ref "$PROJECT_REF"

# Deploy schema
echo "Deploying schema..."
supabase db push --db-url "postgresql://postgres:[YOUR-PASSWORD]@db.$PROJECT_REF.supabase.co:5432/postgres" || {
    echo -e "${YELLOW}⚠️  Direct DB push failed. Using SQL file instead...${NC}"
    echo ""
    echo "Please run the SQL manually:"
    echo "  1. Go to Supabase Dashboard → SQL Editor"
    echo "  2. Copy contents of infra/supabase/schema.sql"
    echo "  3. Paste and run"
    exit 1
}

echo ""
echo -e "${GREEN}✓ Schema deployed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify tables in Supabase Dashboard → Table Editor"
echo "  2. Check RLS policies in Supabase Dashboard → Authentication → Policies"
echo "  3. Test RPC function: increment_usage_counter"
echo ""

