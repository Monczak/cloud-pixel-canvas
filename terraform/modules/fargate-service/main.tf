resource "aws_cloudwatch_log_group" "logs" {
  name              = "/ecs/${var.project_name}/${var.app_name}"
  retention_in_days = 1
}

resource "aws_ecs_task_definition" "task" {
  family                   = "${var.project_name}-${var.app_name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.role_arn
  task_role_arn            = var.role_arn

  container_definitions = jsonencode([{
    name      = var.app_name
    image     = var.image
    user      = var.container_user
    command   = length(var.command) > 0 ? var.command : null
    
    portMappings = concat(
      var.container_port > 0 ? [{ containerPort = var.container_port }] : [],
      [for p in var.extra_ports : { containerPort = p }]
    )
    
    environment = [for k, v in var.env_vars : {
      name  = k
      value = v
    }]

    mountPoints = var.efs_config != null ? [{
      sourceVolume  = "data"
      containerPath = var.efs_config.container_path
    }] : []

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.logs.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  dynamic "volume" {
    for_each = var.efs_config != null ? [1] : []
    content {
      name = "data"
      efs_volume_configuration {
        file_system_id     = var.efs_config.file_system_id
        transit_encryption = "ENABLED"
        authorization_config {
          access_point_id = var.efs_config.access_point_id
        }
      }
    }
  }
}

resource "aws_ecs_service" "svc" {
  name            = "${var.app_name}"
  cluster         = "${var.project_name}-cluster"
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.subnets
    security_groups = var.security_groups
  }

  health_check_grace_period_seconds  = var.lb_targets != [] ? var.health_check_grace_period_seconds : 0
  deployment_minimum_healthy_percent = var.deployment_minimum_healthy_percent
  deployment_maximum_percent         = var.deployment_maximum_percent

  dynamic "load_balancer" {
    for_each = var.lb_targets
    content {
      target_group_arn = load_balancer.value.target_group_arn
      container_name   = var.app_name
      container_port   = load_balancer.value.container_port
    }
  }
}

output "task_arn" {
  value = aws_ecs_task_definition.task.arn
}

output "service_name" {
  value = aws_ecs_service.svc.name
}
