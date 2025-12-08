#!/bin/bash
set -e

echo "🚀 Starting deployment on GCE..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env.prod exists
if [ ! -f .env.prod ]; then
    echo -e "${YELLOW}⚠️  .env.prod not found. Creating from example...${NC}"
    cp .env.prod.example .env.prod
    echo -e "${YELLOW}⚠️  Please edit .env.prod with your production values before continuing!${NC}"
    exit 1
fi

# Pull latest code
echo -e "${GREEN}📥 Pulling latest code...${NC}"
git pull origin main || echo "Not a git repository or no changes"

# Stop existing containers
echo -e "${GREEN}🛑 Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

# Remove old images (optional, comment out if you want faster deploys)
echo -e "${GREEN}🧹 Cleaning up old images...${NC}"
docker system prune -f

# Build and start containers
echo -e "${GREEN}🔨 Building and starting containers...${NC}"
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services to be healthy
echo -e "${GREEN}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Run migrations
echo -e "${GREEN}📦 Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput

# Collect static files
echo -e "${GREEN}📦 Collecting static files...${NC}"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

# Create superuser (only if needed)
echo -e "${GREEN}👤 Creating superuser (skip if already exists)...${NC}"
docker-compose -f docker-compose.prod.yml exec -T web python manage.py createsuperuser --noinput || echo "Superuser already exists or skipped"

# Show status
echo -e "${GREEN}✅ Deployment complete! Checking status...${NC}"
docker-compose -f docker-compose.prod.yml ps

echo -e "${GREEN}✅ All done! Your app should be running on port 80${NC}"
echo -e "${YELLOW}📝 View logs: docker-compose -f docker-compose.prod.yml logs -f${NC}"

