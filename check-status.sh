#!/bin/bash

set -e

# Get AWS region from Terraform
cd terraform
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-1")
cd ..

echo "=== ECS Cluster Status ==="
aws ecs describe-clusters \
  --clusters pixel-canvas-cluster \
  --region $AWS_REGION \
  --query 'clusters[0].{Status:status,RunningTasks:runningTasksCount,PendingTasks:pendingTasksCount}' \
  --output table

echo ""
echo "=== Backend Service Status ==="
aws ecs describe-services \
  --cluster pixel-canvas-cluster \
  --services pixel-canvas-backend-service \
  --region $AWS_REGION \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
  --output table

echo ""
echo "=== Frontend Service Status ==="
aws ecs describe-services \
  --cluster pixel-canvas-cluster \
  --services pixel-canvas-frontend-service \
  --region $AWS_REGION \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
  --output table

echo ""
echo "=== Backend Deployments ==="
aws ecs describe-services \
  --cluster pixel-canvas-cluster \
  --services pixel-canvas-backend-service \
  --region $AWS_REGION \
  --query 'services[0].deployments[*].{Status:status,TaskDef:taskDefinition,Running:runningCount,Desired:desiredCount,Created:createdAt}' \
  --output table

echo ""
echo "=== Frontend Deployments ==="
aws ecs describe-services \
  --cluster pixel-canvas-cluster \
  --services pixel-canvas-frontend-service \
  --region $AWS_REGION \
  --query 'services[0].deployments[*].{Status:status,TaskDef:taskDefinition,Running:runningCount,Desired:desiredCount,Created:createdAt}' \
  --output table

echo ""
echo "=== ALB Target Health ==="
cd terraform
BACKEND_TG=$(terraform output -raw backend_target_group_arn 2>/dev/null || echo "")
FRONTEND_TG=$(terraform output -raw frontend_target_group_arn 2>/dev/null || echo "")
cd ..

if [ -n "$BACKEND_TG" ]; then
  echo "Backend targets:"
  aws elbv2 describe-target-health \
    --target-group-arn $BACKEND_TG \
    --region $AWS_REGION \
    --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
    --output table 2>/dev/null || echo "  (No targets or TG ARN not available)"
fi

if [ -n "$FRONTEND_TG" ]; then
  echo "Frontend targets:"
  aws elbv2 describe-target-health \
    --target-group-arn $FRONTEND_TG \
    --region $AWS_REGION \
    --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
    --output table 2>/dev/null || echo "  (No targets or TG ARN not available)"
fi

echo ""
echo "To view recent logs:"
echo "  Backend:  aws logs tail /ecs/pixel-canvas-backend --follow --region $AWS_REGION"
echo "  Frontend: aws logs tail /ecs/pixel-canvas-frontend --follow --region $AWS_REGION"
