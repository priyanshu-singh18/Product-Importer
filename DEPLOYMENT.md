# GCE Deployment Guide

Complete guide to deploy this Django application on Google Compute Engine (e2-small instance).

## Prerequisites

- Google Cloud account
- Domain name (optional, but recommended)
- Netlify account for frontend

## Step 1: Create GCE Instance

### Option A: Using GCloud CLI (Recommended)

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create e2-small instance with Ubuntu 22.04
gcloud compute instances create product-importer \
    --zone=us-central1-a \
    --machine-type=e2-small \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --tags=http-server,https-server

# Create firewall rules
gcloud compute firewall-rules create allow-http \
    --allow tcp:80 \
    --target-tags=http-server \
    --description="Allow HTTP traffic"

gcloud compute firewall-rules create allow-https \
    --allow tcp:443 \
    --target-tags=https-server \
    --description="Allow HTTPS traffic"
```

### Option B: Using GCP Console (Web UI)

1. Go to [GCP Console](https://console.cloud.google.com)
2. Navigate to **Compute Engine > VM Instances**
3. Click **Create Instance**
4. Configure:
   - **Name**: `product-importer`
   - **Region**: Choose closest to your users
   - **Machine type**: `e2-small` (2 vCPU, 2GB RAM)
   - **Boot disk**: Ubuntu 22.04 LTS, 20GB
   - **Firewall**: Check both "Allow HTTP" and "Allow HTTPS"
5. Click **Create**

## Step 2: Connect to Your Instance

```bash
gcloud compute ssh product-importer --zone=us-central1-a
```

Or use the SSH button in the GCP Console.

## Step 3: Setup Docker on GCE

Once connected to your instance, download and run the setup script:

```bash
# Download the setup script (or manually upload it)
wget https://raw.githubusercontent.com/YOUR_REPO/setup-gce.sh
chmod +x setup-gce.sh
./setup-gce.sh

# Log out and log back in for docker group to take effect
exit
```

Then reconnect:

```bash
gcloud compute ssh product-importer --zone=us-central1-a
```

## Step 4: Upload Your Code

### Option A: Using Git (Recommended)

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/Product-Importer.git app
cd app
```

### Option B: Using SCP

From your local machine:

```bash
# Get your instance's external IP
gcloud compute instances describe product-importer --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Upload files (exclude large directories)
gcloud compute scp --recurse \
    --exclude="venv/*" \
    --exclude="node_modules/*" \
    --exclude="__pycache__/*" \
    --exclude=".git/*" \
    ./* product-importer:~/app/ --zone=us-central1-a
```

## Step 5: Configure Environment Variables

On your GCE instance:

```bash
cd ~/app

# Copy example and edit
cp .env.prod.example .env.prod
nano .env.prod
```

**Important settings to change:**

```bash
# Generate a strong secret key
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Your instance IP (get it from: curl ifconfig.me)
ALLOWED_HOSTS=YOUR_GCE_IP,your-domain.com

# Strong database password
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Your Netlify frontend URL
CORS_ALLOWED_ORIGINS=https://your-app.netlify.app
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://your-app.netlify.app
```

## Step 6: Deploy!

```bash
cd ~/app
chmod +x deploy.sh
./deploy.sh
```

This will:

- Build Docker images
- Start all services (PostgreSQL, Redis, Django, Celery, Nginx)
- Run migrations
- Collect static files

## Step 7: Verify Deployment

```bash
# Check if all services are running
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f web

# Test the API
curl http://localhost/api/products/
```

Get your external IP:

```bash
curl ifconfig.me
```

Visit: `http://YOUR_IP/` in your browser.

## Step 8: Configure Frontend (Netlify)

1. Deploy your React frontend to Netlify
2. Update `VITE_API_URL` in Netlify environment variables:
   ```
   VITE_API_URL=http://YOUR_GCE_IP
   ```
3. Update `.env.prod` on GCE with your Netlify URL
4. Restart services:
   ```bash
   docker-compose -f docker-compose.prod.yml restart web
   ```

## Step 9: (Optional) Setup Custom Domain & SSL

### A. Point your domain to GCE

1. Get your static IP:

```bash
gcloud compute addresses create product-importer-ip --region=us-central1
gcloud compute addresses describe product-importer-ip --region=us-central1
```

2. Attach to instance:

```bash
gcloud compute instances delete-access-config product-importer \
    --access-config-name="external-nat" --zone=us-central1-a

gcloud compute instances add-access-config product-importer \
    --access-config-name="external-nat" \
    --address=STATIC_IP \
    --zone=us-central1-a
```

3. Add DNS A record pointing to your static IP

### B. Setup SSL with Let's Encrypt

```bash
cd ~/app

# Update nginx.conf with your domain
nano nginx.conf
# Change server_name to your domain

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx

# Get SSL certificate
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@example.com \
    --agree-tos \
    --no-eff-email \
    -d your-domain.com

# Update nginx.conf to enable HTTPS (uncomment HTTPS server block)
nano nginx.conf

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

## Monitoring & Maintenance

### View logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f worker
```

### Restart services

```bash
docker-compose -f docker-compose.prod.yml restart
```

### Update deployment

```bash
cd ~/app
git pull origin main
./deploy.sh
```

### Database backup

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres acme_importer > backup.sql

# Restore
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres acme_importer
```

### Check resource usage

```bash
htop
docker stats
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Check disk space
df -h

# Check memory
free -h
```

### Out of memory

```bash
# Reduce Celery concurrency in docker-compose.prod.yml
# Change: --concurrency=1 to --concurrency=1 --max-tasks-per-child=25
docker-compose -f docker-compose.prod.yml up -d --no-deps worker
```

### Can't connect from frontend

- Check CORS_ALLOWED_ORIGINS in .env.prod
- Check firewall rules are set
- Verify external IP is correct

### Database connection errors

- Check database is healthy: `docker-compose -f docker-compose.prod.yml ps`
- Check DATABASE_URL is correct in .env.prod
- Restart database: `docker-compose -f docker-compose.prod.yml restart db`

## Cost Estimation

- **e2-small instance**: ~$13/month
- **20GB disk**: ~$2/month
- **Static IP**: ~$3/month (if you reserve one)
- **Egress traffic**: Variable (usually minimal for low traffic)

**Total**: ~$18-20/month

## Security Checklist

- [ ] Change default passwords in .env.prod
- [ ] Set DEBUG=False
- [ ] Use strong SECRET_KEY
- [ ] Configure ALLOWED_HOSTS properly
- [ ] Setup SSL certificate
- [ ] Regular backups
- [ ] Keep system updated: `sudo apt-get update && sudo apt-get upgrade`
- [ ] Monitor logs for suspicious activity

## Need Help?

Check the logs first:

```bash
docker-compose -f docker-compose.prod.yml logs -f
```

Common issues are usually:

1. Wrong environment variables
2. Firewall blocking connections
3. Out of memory (upgrade to e2-medium if needed)
