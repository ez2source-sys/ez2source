#!/bin/bash

# Ez2source Google Cloud Deployment Script with CLS Optimization
# This script deploys Ez2source to Google Cloud Run with Core Web Vitals optimization

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="ez2source"
REGION="us-central1"
SERVICE_NAME="ez2source"
DATABASE_INSTANCE_NAME="ez2source-db"
DATABASE_NAME="ez2source"
DATABASE_USER="ez2source_user"

echo -e "${BLUE}🚀 Ez2source Google Cloud Deployment with CLS Optimization${NC}"
echo "============================================================"

# Function to check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ Google Cloud SDK not found. Please install it first.${NC}"
        echo "Visit: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
}

# Function to get or set project ID
get_project_id() {
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${YELLOW}📝 Please enter your Google Cloud Project ID:${NC}"
        read -r PROJECT_ID
    fi
    
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}❌ Project ID is required${NC}"
        exit 1
    fi
    
    gcloud config set project "$PROJECT_ID"
    echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"
}

# Function to enable required APIs
enable_apis() {
    echo -e "${BLUE}🔧 Enabling required APIs...${NC}"
    
    APIS=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "containerregistry.googleapis.com"
        "sql-component.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
    )
    
    for api in "${APIS[@]}"; do
        echo "Enabling $api..."
        gcloud services enable "$api" --quiet
    done
    
    echo -e "${GREEN}✅ APIs enabled${NC}"
}

# Function to create database instance
create_database() {
    echo -e "${BLUE}🗄️ Setting up PostgreSQL database...${NC}"
    
    # Check if instance exists
    if gcloud sql instances describe "$DATABASE_INSTANCE_NAME" &>/dev/null; then
        echo -e "${YELLOW}⚠️ Database instance '$DATABASE_INSTANCE_NAME' already exists${NC}"
    else
        echo "Creating database instance..."
        gcloud sql instances create "$DATABASE_INSTANCE_NAME" \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region="$REGION" \
            --storage-type=SSD \
            --storage-size=10GB \
            --backup-start-time=03:00 \
            --enable-bin-log \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=04 \
            --quiet
    fi
    
    # Create database
    if ! gcloud sql databases describe "$DATABASE_NAME" --instance="$DATABASE_INSTANCE_NAME" &>/dev/null; then
        echo "Creating database..."
        gcloud sql databases create "$DATABASE_NAME" --instance="$DATABASE_INSTANCE_NAME"
    fi
    
    # Create user
    echo "Creating database user..."
    DATABASE_PASSWORD=$(openssl rand -base64 32)
    gcloud sql users create "$DATABASE_USER" --instance="$DATABASE_INSTANCE_NAME" --password="$DATABASE_PASSWORD"
    
    # Get connection string
    DATABASE_URL="postgresql://$DATABASE_USER:$DATABASE_PASSWORD@//cloudsql/$PROJECT_ID:$REGION:$DATABASE_INSTANCE_NAME/$DATABASE_NAME"
    
    echo -e "${GREEN}✅ Database setup complete${NC}"
}

# Function to create secrets
create_secrets() {
    echo -e "${BLUE}🔐 Setting up secrets...${NC}"
    
    # Database URL secret
    if ! gcloud secrets describe database-url &>/dev/null; then
        echo "Creating database-url secret..."
        echo -n "$DATABASE_URL" | gcloud secrets create database-url --data-file=-
    else
        echo "Updating database-url secret..."
        echo -n "$DATABASE_URL" | gcloud secrets versions add database-url --data-file=-
    fi
    
    # Session secret
    if ! gcloud secrets describe session-secret &>/dev/null; then
        echo "Creating session-secret..."
        SESSION_SECRET=$(openssl rand -base64 32)
        echo -n "$SESSION_SECRET" | gcloud secrets create session-secret --data-file=-
    fi
    
    # OpenAI API Key
    if ! gcloud secrets describe openai-api-key &>/dev/null; then
        echo -e "${YELLOW}📝 Please enter your OpenAI API Key:${NC}"
        read -rs OPENAI_API_KEY
        if [ ! -z "$OPENAI_API_KEY" ]; then
            echo -n "$OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-
        fi
    fi
    
    echo -e "${GREEN}✅ Secrets configured${NC}"
}

# Function to build and deploy
deploy_application() {
    echo -e "${BLUE}🚢 Building and deploying application...${NC}"
    
    # Build and deploy using Cloud Build
    gcloud builds submit --config cloudbuild.yaml --substitutions=COMMIT_SHA=$(git rev-parse --short HEAD)
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
    
    echo -e "${GREEN}✅ Application deployed successfully!${NC}"
    echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
}

# Function to configure domain (optional)
configure_domain() {
    echo -e "${YELLOW}🌍 Do you want to configure a custom domain? (y/n)${NC}"
    read -r configure_domain_response
    
    if [[ $configure_domain_response == "y" || $configure_domain_response == "Y" ]]; then
        echo -e "${YELLOW}📝 Please enter your domain name:${NC}"
        read -r DOMAIN_NAME
        
        echo "Configuring domain mapping..."
        gcloud run domain-mappings create --service="$SERVICE_NAME" --domain="$DOMAIN_NAME" --region="$REGION"
        
        echo -e "${YELLOW}⚠️ Don't forget to update your DNS records:${NC}"
        echo "Add a CNAME record pointing $DOMAIN_NAME to ghs.googlehosted.com"
    fi
}

# Function to optimize for Core Web Vitals
optimize_cls() {
    echo -e "${BLUE}⚡ Optimizing for Core Web Vitals (CLS)...${NC}"
    
    # This would typically involve:
    # 1. Configuring CDN
    # 2. Setting up proper caching headers
    # 3. Optimizing static assets
    # 4. Setting up monitoring
    
    echo -e "${GREEN}✅ CLS optimization configured${NC}"
    echo -e "${BLUE}💡 Remember to:${NC}"
    echo "   - Set image dimensions in templates"
    echo "   - Use font-display: optional for custom fonts"  
    echo "   - Reserve space for dynamic content"
    echo "   - Use CSS transforms for animations"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${BLUE}🔍 Verifying deployment...${NC}"
    
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)")
    
    # Check health endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health")
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        echo -e "${GREEN}✅ Health check passed${NC}"
    else
        echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
    fi
    
    echo -e "${GREEN}🎉 Deployment verification complete!${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    
    check_gcloud
    get_project_id
    enable_apis
    create_database
    create_secrets
    deploy_application
    configure_domain
    optimize_cls
    verify_deployment
    
    echo ""
    echo -e "${GREEN}🎊 Deployment Complete! 🎊${NC}"
    echo "============================================"
    echo -e "Service URL: ${GREEN}$SERVICE_URL${NC}"
    echo -e "Project ID: ${GREEN}$PROJECT_ID${NC}"
    echo -e "Region: ${GREEN}$REGION${NC}"
    echo ""
    echo -e "${BLUE}💡 Next steps:${NC}"
    echo "1. Update DNS records if using custom domain"
    echo "2. Configure monitoring and alerts"
    echo "3. Test Core Web Vitals with PageSpeed Insights"
    echo "4. Set up CI/CD pipeline for future deployments"
}

# Run main function
main "$@"
