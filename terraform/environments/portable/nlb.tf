resource "aws_lb" "internal" {
  name               = "${var.project_name}-internal-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = module.vpc.private_subnets
  security_groups    = [aws_security_group.ecs_tasks.id] 
  enable_cross_zone_load_balancing = true
}

# --- Backend Internal (TCP 8000) ---
resource "aws_lb_target_group" "backend_internal" {
  name        = "${var.project_name}-backend-int-tg"
  port        = 8000
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
}

resource "aws_lb_listener" "backend_internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 8000
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend_internal.arn
  }
}

# --- Keycloak Internal (TCP 8080) ---
resource "aws_lb_target_group" "keycloak_internal" {
  name        = "${var.project_name}-keycloak-int-tg"
  port        = 8080
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path = "/health/ready"
  }
}

resource "aws_lb_listener" "keycloak_internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 8080
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak_internal.arn
  }
}

# --- Mongo (TCP 27017) ---
resource "aws_lb_target_group" "mongo" {
  name        = "${var.project_name}-mongo-tg"
  port        = 27017
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  
  health_check {
    protocol = "TCP"
  }
}

resource "aws_lb_listener" "mongo" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 27017
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mongo.arn
  }
}

# --- Valkey (TCP 6379) ---
resource "aws_lb_target_group" "valkey" {
  name        = "${var.project_name}-valkey-tg"
  port        = 6379
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
}

resource "aws_lb_listener" "valkey" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 6379
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.valkey.arn
  }
}

# --- Postgres / Keycloak DB (TCP 5432) ---
resource "aws_lb_target_group" "postgres" {
  name        = "${var.project_name}-postgres-tg"
  port        = 5432
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
}

resource "aws_lb_listener" "postgres" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 5432
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.postgres.arn
  }
}

# --- MinIO API Internal (TCP 9000) ---
resource "aws_lb_target_group" "minio_internal" {
  name        = "${var.project_name}-minio-int-tg"
  port        = 9000
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
}

resource "aws_lb_listener" "minio_internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 9000
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.minio_internal.arn
  }
}

# --- Prometheus Internal (TCP 9090) ---
resource "aws_lb_target_group" "prometheus_internal" {
  name        = "${var.project_name}-prom-int-tg"
  port        = 9090
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
}

resource "aws_lb_listener" "prometheus_internal" {
  load_balancer_arn = aws_lb.internal.arn
  port              = 9090
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus_internal.arn
  }
}
