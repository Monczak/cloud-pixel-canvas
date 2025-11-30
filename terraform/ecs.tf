resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
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
    name  = "backend"
    image = "${aws_ecr_repository.backend.repository_url}:latest"

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
        name  = "SYSTEM_KEY"
        value = tostring(random_password.system_key.result)
      },
      {
        name  = "VALKEY_HOST"
        value = tostring(aws_elasticache_serverless_cache.main.endpoint[0].address)
      },
      {
        name  = "VALKEY_PORT"
        value = tostring(aws_elasticache_serverless_cache.main.endpoint[0].port)
      },
      {
        name  = "VALKEY_SSL"
        value = "true"
      },
      {
        name  = "HEARTBEAT_INTERVAL"
        value = tostring(var.heartbeat_interval)
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
    name  = "frontend"
    image = "${aws_ecr_repository.frontend.repository_url}:latest"

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
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "ECS Tasks Security Group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow traffic from ALB to backend"
  }

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow traffic from ALB to frontend"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}
