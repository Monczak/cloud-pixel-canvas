resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# --- Mongo (Runs as 999) ---
module "mongo" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "mongo"
  image           = "mongo:latest"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 27017

  # Run directly as mongo user to skip entrypoint chown
  container_user = "999"

  lb_targets = [{
    target_group_arn = aws_lb_target_group.mongo.arn
    container_port   = 27017
  }]

  env_vars = {
    MONGO_INITDB_ROOT_USERNAME = "root"
    MONGO_INITDB_ROOT_PASSWORD = random_password.mongo_root.result
  }

  efs_config = {
    file_system_id  = aws_efs_file_system.main.id
    access_point_id = aws_efs_access_point.mongo.id
    container_path  = "/data/db"
  }

  # Ensure old task stops before new one starts
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  depends_on = [aws_lb_listener.mongo]
}

# --- Valkey ---
module "valkey" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "valkey"
  image           = "valkey/valkey:8-alpine"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 6379

  lb_targets = [{
    target_group_arn = aws_lb_target_group.valkey.arn
    container_port   = 6379
  }]

  depends_on = [aws_lb_listener.valkey]
}

# --- MinIO ---
module "minio" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "minio"
  image           = "minio/minio"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  cpu             = 512
  memory          = 1024
  container_port  = 9000
  extra_ports     = [9001]

  command = ["server", "/data", "--console-address", ":9001"]

  env_vars = {
    MINIO_ROOT_USER     = random_password.minio_access_key.result
    MINIO_ROOT_PASSWORD = random_password.minio_secret_key.result
  }

  efs_config = {
    file_system_id  = aws_efs_file_system.main.id
    access_point_id = aws_efs_access_point.minio.id
    container_path  = "/data"
  }

  lb_targets = [
    { target_group_arn = aws_lb_target_group.minio.arn, container_port = 9001 },
    { target_group_arn = aws_lb_target_group.minio_api_public.arn, container_port = 9000 },
    { target_group_arn = aws_lb_target_group.minio_internal.arn, container_port = 9000 }
  ]

  # Ensure old task stops before new one starts
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  depends_on = [
    aws_lb_listener.minio,
    aws_lb_listener.minio_api,
    aws_lb_listener.minio_internal
  ]
}

# --- Keycloak DB (Runs as 70) ---
module "keycloak_db" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "keycloak-db"
  image           = "postgres:18-alpine"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 5432

  # Run as postgres user to avoid chown issues
  container_user = "70"

  lb_targets = [{
    target_group_arn = aws_lb_target_group.postgres.arn
    container_port   = 5432
  }]

  env_vars = {
    POSTGRES_DB       = "keycloak"
    POSTGRES_USER     = "keycloak"
    POSTGRES_PASSWORD = random_password.postgres_password.result
  }

  efs_config = {
    file_system_id  = aws_efs_file_system.main.id
    access_point_id = aws_efs_access_point.postgres.id
    container_path  = "/var/lib/postgresql/data"
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  depends_on = [aws_lb_listener.postgres]
}

# --- Keycloak ---
module "keycloak" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "keycloak"
  image           = "${aws_ecr_repository.keycloak.repository_url}:latest"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  cpu             = 512
  memory          = 1024
  container_port  = 8080

  command = ["start-dev", "--import-realm"]

  env_vars = {
    KC_DB                             = "postgres"
    KC_DB_URL                         = "jdbc:postgresql://${aws_lb.internal.dns_name}:5432/keycloak"
    KC_DB_USERNAME                    = "keycloak"
    KC_DB_PASSWORD                    = random_password.postgres_password.result
    KC_BOOTSTRAP_ADMIN_USERNAME       = "admin"
    KC_BOOTSTRAP_ADMIN_PASSWORD       = random_password.keycloak_admin_password.result
    KC_HTTP_ENABLED                   = "true"
    KC_HOSTNAME_STRICT                = "false"
    KC_PROXY_HEADERS                  = "xforwarded"
    KC_HEALTH_ENABLED                 = "true"
    KC_HTTP_MANAGEMENT_HEALTH_ENABLED = "false" # Move health checks back to port 8080
  }

  lb_targets = [
    {
      target_group_arn = aws_lb_target_group.keycloak.arn
      container_port   = 8080
    },
    {
      target_group_arn = aws_lb_target_group.keycloak_internal.arn
      container_port   = 8080
    }
  ]

  health_check_grace_period_seconds = 300

  depends_on = [
    aws_lb_listener.keycloak
  ]
}

# --- Prometheus ---
module "prometheus" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "prometheus"
  image           = "${aws_ecr_repository.prometheus.repository_url}:latest"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 9090

  env_vars = {
    BACKEND_HOST = "${aws_lb.internal.dns_name}:8000"
  }

  lb_targets = [{
    target_group_arn = aws_lb_target_group.prometheus_internal.arn
    container_port   = 9090
  }]
  
  depends_on = [aws_lb_listener.prometheus_internal]
}

# --- Grafana (Runs as 472) ---
module "grafana" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "grafana"
  image           = "${aws_ecr_repository.grafana.repository_url}:latest"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 3000

  # Ensure grafana runs as correct user for EFS
  container_user = "472"

  env_vars = {
    GF_SECURITY_ADMIN_USER     = "admin"
    GF_SECURITY_ADMIN_PASSWORD = random_password.grafana_admin_password.result
    PROMETHEUS_URL             = "http://${aws_lb.internal.dns_name}:9090"
  }

  efs_config = {
    file_system_id  = aws_efs_file_system.main.id
    access_point_id = aws_efs_access_point.grafana.id
    container_path  = "/var/lib/grafana"
  }

  lb_targets = [{
    target_group_arn = aws_lb_target_group.grafana.arn
    container_port   = 3000
  }]

  depends_on = [aws_lb_listener.grafana]
}

# --- Backend ---
module "backend" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "backend"
  image           = "${aws_ecr_repository.backend.repository_url}:latest"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 8000

  env_vars = {
    ENVIRONMENT  = "portable"
    CORS_ORIGINS = "http://${aws_lb.main.dns_name},http://localhost:3000"

    MONGO_URI = "mongodb://root:${random_password.mongo_root.result}@${aws_lb.internal.dns_name}:27017"
    MONGO_DB  = "pixel_canvas"

    VALKEY_HOST = aws_lb.internal.dns_name
    VALKEY_PORT = "6379"

    KEYCLOAK_URL                   = "http://${aws_lb.internal.dns_name}:8080"
    KEYCLOAK_REALM                 = "pixel-canvas"
    KEYCLOAK_CLIENT_ID             = "pixel-canvas-client"
    KEYCLOAK_BACKEND_CLIENT_ID     = "pixel-canvas-backend"
    KEYCLOAK_BACKEND_CLIENT_SECRET = random_password.keycloak_client_secret.result

    S3_ENDPOINT_URL  = "http://${aws_lb.internal.dns_name}:9000"
    S3_PUBLIC_DOMAIN = "http://${aws_lb.main.dns_name}"
    S3_BUCKET_NAME   = "pixel-canvas-snapshots"
    MINIO_ACCESS_KEY = random_password.minio_access_key.result
    MINIO_SECRET_KEY = random_password.minio_secret_key.result
    AWS_REGION       = "us-east-1"

    SYSTEM_KEY = random_password.system_key.result
  }

  lb_targets = [
    {
      target_group_arn = aws_lb_target_group.backend.arn
      container_port   = 8000
    },
    {
      target_group_arn = aws_lb_target_group.backend_internal.arn
      container_port   = 8000
    }
  ]
  
  depends_on = [
    aws_lb_listener_rule.api,
    aws_lb_listener.backend_internal
  ]
}

# --- Frontend ---
module "frontend" {
  source          = "../../modules/fargate-service"
  project_name    = var.project_name
  app_name        = "frontend"
  image           = "${aws_ecr_repository.frontend.repository_url}:latest"
  region          = var.aws_region
  role_arn        = var.lab_role_arn
  vpc_id          = module.vpc.vpc_id
  subnets         = module.vpc.private_subnets
  security_groups = [aws_security_group.ecs_tasks.id]
  container_port  = 3000

  env_vars = {
    ORIGIN = "http://${aws_lb.main.dns_name}"
  }

  lb_targets = [{
    target_group_arn = aws_lb_target_group.frontend.arn
    container_port   = 3000
  }]

  depends_on = [aws_lb_listener.http]
}

# --- Keycloak Setup Task ---
resource "aws_ecs_task_definition" "keycloak_setup" {
  family                   = "keycloak-setup"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.lab_role_arn
  task_role_arn            = var.lab_role_arn

  container_definitions = jsonencode([{
    name  = "setup"
    image = "${aws_ecr_repository.keycloak_setup.repository_url}:latest"
    environment = [
      { name = "KC_HEALTH_URL", value = "http://${aws_lb.internal.dns_name}:8080" },
      { name = "KC_URL", value = "http://${aws_lb.internal.dns_name}:8080" },
      { name = "REALM", value = "pixel-canvas" },
      { name = "BOOTSTRAP_USER", value = "admin" },
      { name = "BOOTSTRAP_PASS", value = random_password.keycloak_admin_password.result },
      { name = "BACKEND_CLIENT_ID", value = "pixel-canvas-backend" },
      { name = "BACKEND_CLIENT_SECRET", value = random_password.keycloak_client_secret.result }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}/setup"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "setup"
      }
    }
  }])
}

# --- Keycloak Setup Log Group ---
resource "aws_cloudwatch_log_group" "setup" {
  name              = "/ecs/${var.project_name}/setup"
  retention_in_days = 1
}
