#!/bin/bash
# This script sets up Docker on a fresh GCE Ubuntu instance
set -e

echo "🚀 Setting up GCE instance for Docker deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group
echo "👤 Adding user to docker group..."
sudo usermod -aG docker $USER

# Install Docker Compose standalone (for compatibility)
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install git
echo "📦 Installing Git..."
sudo apt-get install -y git

# Install other useful tools
echo "📦 Installing useful tools..."
sudo apt-get install -y htop nano vim curl wget

# Enable Docker service
echo "🔧 Enabling Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

# Create app directory
echo "📁 Creating app directory..."
mkdir -p ~/app
cd ~/app

echo "✅ Setup complete!"
echo ""
echo "⚠️  IMPORTANT: You need to log out and log back in for docker group changes to take effect!"
echo ""
echo "📋 Next steps:"
echo "1. Log out and log back in: exit"
echo "2. Clone your repository: git clone <your-repo-url> ~/app"
echo "3. Create .env.prod file with your production settings"
echo "4. Run: cd ~/app && bash deploy.sh"
echo ""
echo "🔥 Firewall rules needed (run these in GCloud Console or CLI):"
echo "   gcloud compute firewall-rules create allow-http --allow tcp:80"
echo "   gcloud compute firewall-rules create allow-https --allow tcp:443"

