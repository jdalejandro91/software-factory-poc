#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Starting Manual Deployment to EC2...${NC}"

# 1. Load .env
if [ -f .env ]; then
    echo -e "${GREEN}📄 Loading environment vars from .env${NC}"
    set -a
    source .env
    set +a
else
    echo -e "${YELLOW}⚠️  .env file not found. Assuming variables are exported.${NC}"
fi

# 2. Defaults & Validation
EC2_USER=${EC2_USER:-ubuntu}
REMOTE_DIR=${REMOTE_DIR:-/home/ubuntu/software-factory-poc}

if [ -z "$EC2_HOST" ]; then
    echo -e "${RED}❌ Error: EC2_HOST is not set.${NC}"
    echo "Please define it in .env or export it."
    exit 1
fi

if [ -z "$KEY_PATH" ]; then
    echo -e "${RED}❌ Error: KEY_PATH is not set.${NC}"
    echo "Please define it in .env or export it."
    exit 1
fi

if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}❌ Error: Key file not found at $KEY_PATH${NC}"
    exit 1
fi

# 3. Deployment Info
echo "---------------------------------------"
echo -e "Target:      ${GREEN}$EC2_USER@$EC2_HOST${NC}"
echo -e "Directory:   ${GREEN}$REMOTE_DIR${NC}"
echo -e "Key:         ${GREEN}$KEY_PATH${NC}"
echo "---------------------------------------"

# 4. Sync Code (Rsync)
echo -e "\n${GREEN}📦 Syncing files...${NC}"
rsync -avz --progress \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    --exclude 'tests' \
    --exclude 'docs' \
    --exclude '.idea' \
    --exclude '.vscode' \
    -e "ssh -i $KEY_PATH -o StrictHostKeyChecking=no" \
    ./ "$EC2_USER@$EC2_HOST:$REMOTE_DIR"

# 5. Remote Restart (SSH)
echo -e "\n${GREEN}🔄 Restarting services on remote...${NC}"
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << EOF
    set -e
    cd "$REMOTE_DIR"
    
    echo "🔻 Bringing down containers..."
    sudo docker compose down
    
    echo "🏗️  Rebuilding and Starting..."
    sudo docker compose up -d --build
    
    echo "📜 Logs (tailing last 20 lines)..."
    sudo docker compose logs --tail=20
EOF

echo -e "\n${GREEN}✅ Deployment Finished Successfully!${NC}"
