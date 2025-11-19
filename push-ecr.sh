#!/bin/bash

set -e

# Load AWS credentials and configuration
if [ ! -f terraform/terraform.tfvars ]; then
    echo "Error: terraform/terraform.tfvars not found"
    echo "Please create it with your AWS credentials and configuration"
    exit 1
fi

# Extract ECR repository URLs from terraform output
echo "Getting ECR repository URLs..."
cd terraform
BACKEND_REPO=$(terraform output -raw backend_ecr_repository_url 2>/dev/null || echo "")
FRONTEND_REPO=$(terraform output -raw frontend_ecr_repository_url 2>/dev/null || echo "")
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-1")
cd ..

if [ -z "$BACKEND_REPO" ] || [ -z "$FRONTEND_REPO" ]; then
    echo "Error: Could not get ECR repository URLs from Terraform"
    echo "Please run 'terraform apply' first to create the infrastructure"
    exit 1
fi

echo "Backend ECR: $BACKEND_REPO"
echo "Frontend ECR: $FRONTEND_REPO"
echo "AWS Region: $AWS_REGION"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $BACKEND_REPO

# Build and push backend
echo "Building backend image..."
cd backend
docker build -t pixel-canvas-backend:latest .
docker tag pixel-canvas-backend:latest $BACKEND_REPO:latest
echo "Pushing backend image to ECR..."
docker push $BACKEND_REPO:latest
cd ..

# Build and push frontend
echo "Building frontend image..."
cd frontend
docker build -t pixel-canvas-frontend:latest .
docker tag pixel-canvas-frontend:latest $FRONTEND_REPO:latest
echo "Pushing frontend image to ECR..."
docker push $FRONTEND_REPO:latest
cd ..

echo "Docker images pushed successfully!"
echo ""
echo "Force updating ECS services to pull new images..."

# Get cluster and service names from Terraform
cd terraform
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "pixel-canvas-cluster")
BACKEND_SERVICE=$(terraform output -raw backend_service_name 2>/dev/null || echo "pixel-canvas-backend-service")
FRONTEND_SERVICE=$(terraform output -raw frontend_service_name 2>/dev/null || echo "pixel-canvas-frontend-service")
cd ..

# Force new deployment for backend
echo "Updating backend service..."
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $BACKEND_SERVICE \
  --force-new-deployment \
  --region $AWS_REGION > /dev/null

# Force new deployment for frontend
echo "Updating frontend service..."
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $FRONTEND_SERVICE \
  --force-new-deployment \
  --region $AWS_REGION > /dev/null

echo ""
echo "Deployment complete!"
