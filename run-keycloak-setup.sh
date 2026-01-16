#!/bin/bash
set -e

ENV=$1

# Validate environment argument
if [ -z "$ENV" ]; then
    echo "Usage: ./run-keycloak-setup.sh <portable>"
    echo "Error: No environment specified."
    exit 1
fi

if [ "$ENV" != "portable" ]; then
    echo "Error: Keycloak setup is currently only supported for the 'portable' environment."
    exit 1
fi

if [ ! -d "terraform/environments/$ENV" ]; then
    echo "Error: Directory 'terraform/environments/$ENV' not found."
    exit 1
fi

echo "========================================================"
echo "   Running Keycloak Setup Task -- $ENV"
echo "========================================================"

# Fetch Terraform outputs
echo "Reading Terraform outputs..."
cd terraform/environments/$ENV
TF_OUT=$(terraform output -json)
cd ../../..

# Extract required variables
REGION=$(echo $TF_OUT | jq -r '.aws_region.value // "us-east-1"')
CLUSTER=$(echo $TF_OUT | jq -r '.ecs_cluster_name.value')
SUBNETS=$(echo $TF_OUT | jq -r '.private_subnets.value | join(",")')
SG=$(echo $TF_OUT | jq -r '.ecs_sg_id.value')

if [ "$CLUSTER" == "null" ]; then
    echo "Error: Could not get 'ecs_cluster_name' from Terraform outputs."
    exit 1
fi

echo "  Region:  $REGION"
echo "  Cluster: $CLUSTER"
echo "  Subnets: $SUBNETS"
echo "  Security Group: $SG"

echo ""
echo "Launching Keycloak setup task..."

TASK_ARN=$(aws ecs run-task \
    --cluster $CLUSTER \
    --task-definition keycloak-setup \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=DISABLED}" \
    --region $REGION \
    --query "tasks[0].taskArn" --output text)

echo "Setup task launched successfully: $TASK_ARN"
echo "Check the ECS console or CloudWatch logs (/ecs/pixel-canvas/setup) for progress."
