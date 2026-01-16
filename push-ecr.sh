#!/bin/bash
set -e

ENV=$1

# Validate environment argument
if [ -z "$ENV" ]; then
    echo "Usage: ./push-ecr.sh <native|portable>"
    echo "Error: No environment specified."
    exit 1
fi

if [ ! -d "terraform/environments/$ENV" ]; then
    echo "Error: Directory 'terraform/environments/$ENV' not found."
    exit 1
fi

echo "========================================================"
echo "   Deploying Pixel Canvas -- using $ENV environment"
echo "========================================================"

# Fetch Terraform outputs
echo "Reading Terraform outputs..."
cd terraform/environments/$ENV
TF_OUT=$(terraform output -json)
cd ../../..

REGION=$(echo $TF_OUT | jq -r '.aws_region.value // "us-east-1"')
CLUSTER=$(echo $TF_OUT | jq -r '.ecs_cluster_name.value')

if [ "$CLUSTER" == "null" ]; then
    echo "Error: Could not get 'ecs_cluster_name' from Terraform outputs."
    exit 1
fi

echo "  Region:  $REGION"
echo "  Cluster: $CLUSTER"

push_image() {
    NAME=$1
    DIR=$2
    REPO_URL=$3

    if [ -z "$REPO_URL" ] || [ "$REPO_URL" == "null" ]; then
        echo "Skipping $NAME: No repository URL found in Terraform outputs."
        return
    fi

    echo ""
    echo "[Build & Push] $NAME"
    echo "  Context: $DIR"
    echo "  Repo:    $REPO_URL"

    docker build -t $NAME:latest $DIR --platform linux/amd64

    docker tag $NAME:latest $REPO_URL:latest
    docker push $REPO_URL:latest
}

# Login to ECR
SAMPLE_REPO=$(echo $TF_OUT | jq -r '.. | .repository_url? // empty' | head -n 1)
if [ -z "$SAMPLE_REPO" ]; then
    if [ "$ENV" == "native" ]; then
        SAMPLE_REPO=$(echo $TF_OUT | jq -r '.backend_ecr_repository_url.value')
    else
        SAMPLE_REPO=$(echo $TF_OUT | jq -r '.backend_repo.value')
    fi
fi

if [ -n "$SAMPLE_REPO" ] && [ "$SAMPLE_REPO" != "null" ]; then
    echo ""
    echo "Logging in to ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $SAMPLE_REPO
else
    echo "Error: Could not find any ECR repositories to log in to."
    exit 1
fi

# Build, tag and push images, then update services
if [ "$ENV" == "native" ]; then
    BE_REPO=$(echo $TF_OUT | jq -r '.backend_ecr_repository_url.value')
    FE_REPO=$(echo $TF_OUT | jq -r '.frontend_ecr_repository_url.value')
    BE_SVC=$(echo $TF_OUT | jq -r '.backend_service_name.value')
    FE_SVC=$(echo $TF_OUT | jq -r '.frontend_service_name.value')

    push_image "backend"  "./backend"  $BE_REPO
    push_image "frontend" "./frontend" $FE_REPO

    echo ""
    echo "Updating ECS Services..."
    aws ecs update-service --cluster $CLUSTER --service $BE_SVC --force-new-deployment --region $REGION > /dev/null
    echo "  - Updated: $BE_SVC"
    aws ecs update-service --cluster $CLUSTER --service $FE_SVC --force-new-deployment --region $REGION > /dev/null
    echo "  - Updated: $FE_SVC"

elif [ "$ENV" == "portable" ]; then
    BE_REPO=$(echo $TF_OUT | jq -r '.backend_repo.value')
    FE_REPO=$(echo $TF_OUT | jq -r '.frontend_repo.value')
    PROM_REPO=$(echo $TF_OUT | jq -r '.prometheus_repo.value')
    GRAF_REPO=$(echo $TF_OUT | jq -r '.grafana_repo.value')
    KC_REPO=$(echo $TF_OUT | jq -r '.keycloak_repo.value')
    KC_SETUP_REPO=$(echo $TF_OUT | jq -r '.keycloak_setup_repo.value')

    push_image "backend"        "./backend"        $BE_REPO
    push_image "frontend"       "./frontend"       $FE_REPO
    push_image "prometheus"     "./prometheus"     $PROM_REPO
    push_image "grafana"        "./grafana"        $GRAF_REPO
    push_image "keycloak"       "./keycloak"       $KC_REPO
    push_image "keycloak-setup" "./keycloak/setup" $KC_SETUP_REPO

    echo ""
    echo "Force updating services..."
    SERVICES="backend frontend prometheus grafana keycloak"
    
    for SVC in $SERVICES; do
        echo "   - Updating $SVC"
        aws ecs update-service \
            --cluster $CLUSTER \
            --service $SVC \
            --force-new-deployment \
            --region $REGION > /dev/null
    done

    SUBNETS=$(echo $TF_OUT | jq -r '.private_subnets.value | join(",")')
    SG=$(echo $TF_OUT | jq -r '.ecs_sg_id.value')
    ALB_URL=$(echo $TF_OUT | jq -r '.alb_dns_name.value')

    echo ""
    echo "Waiting for Keycloak to be healthy..."
    echo "  Target: http://$ALB_URL:8080/health/ready"

    # Loop until Keycloak returns HTTP 200
    count=0
    while true; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$ALB_URL:8080/health/ready || echo "000")
        
        if [ "$STATUS" == "200" ]; then
            echo "Keycloak is up (Status: $STATUS)"
            break
        fi

        echo "  [$count] Waiting for Keycloak... (Status: $STATUS)"
        sleep 5
        count=$((count+1))
        
        # Timeout after 10 minutes (60 * 5s)
        if [ $count -ge 120 ]; then
            echo "Timeout waiting for Keycloak."
            exit 1
        fi
    done

    echo "Running Keycloak setup task..."
    ./run-keycloak-setup.sh $ENV
fi

echo ""
echo "Deployment complete!"
