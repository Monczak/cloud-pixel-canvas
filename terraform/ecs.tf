resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.lab_role_arn
  task_role_arn            = var.lab_role_arn

  container_definitions = jsonencode([{
    name      = "backend"
    image     = "${aws_ecr_repository.backend.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "ENVIRONMENT"
        value = "aws"
      },
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "DYNAMODB_CANVAS_TABLE"
        value = aws_dynamodb_table.canvas_state.name
      },
      {
        name  = "DYNAMODB_SNAPSHOTS_TABLE"
        value = aws_dynamodb_table.snapshots.name
      },
      {
        name  = "DYNAMODB_SNAPSHOT_TILES_TABLE"
        value = aws_dynamodb_table.snapshot_tiles.name
      },
      {
        name  = "COGNITO_USER_POOL_ID"
        value = aws_cognito_user_pool.main.id
      },
      {
        name  = "COGNITO_CLIENT_ID"
        value = aws_cognito_user_pool_client.main.id
      },
      {
        name  = "S3_BUCKET_NAME"
        value = aws_s3_bucket.snapshots.id
      },
      {
        name  = "CANVAS_WIDTH"
        value = tostring(var.canvas_width)
      },
      {
        name  = "CANVAS_HEIGHT"
        value = tostring(var.canvas_height)
      },
      {
        name  = "MAX_SNAPSHOTS"
        value = tostring(var.max_snapshots)
      },
      {
        name  = "CORS_ORIGINS"
        value = "http://${aws_lb.main.dns_name}"
      },
      {
        name  = "SYSTEM_KEY"
        value = tostring(random_password.system_key.result)
      },
      {
        name  = "VALKEY_HOST"
        value = tostring(aws_elasticache_replication_group.main.primary_endpoint_address)
      },
      {
        name  = "VALKEY_PORT"
        value = tostring(aws_elasticache_replication_group.main.port)
      },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = {
    Name = "${var.project_name}-backend-task"
  }
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.lab_role_arn
  task_role_arn            = var.lab_role_arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:latest"
    essential = true

    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "ORIGIN"
        value = "http://${aws_lb.main.dns_name}"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = {
    Name = "${var.project_name}-frontend-task"
  }
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.main]

  tags = {
    Name = "${var.project_name}-backend-service"
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.main]

  tags = {
    Name = "${var.project_name}-frontend-service"
  }
}

