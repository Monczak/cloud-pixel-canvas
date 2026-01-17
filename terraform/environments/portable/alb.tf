resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets
}

# --- Frontend & Backend (Port 80) ---
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-fe-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path = "/"
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-be-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path = "/api/"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}

# --- Keycloak (Port 8080) ---
resource "aws_lb_target_group" "keycloak" {
  name        = "${var.project_name}-kc-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  
  health_check {
    path = "/health/ready"
  }
}

resource "aws_lb_listener" "keycloak" {
  load_balancer_arn = aws_lb.main.arn
  port              = "8080"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak.arn
  }
}

# --- Grafana (Port 3000) ---
resource "aws_lb_target_group" "grafana" {
  name        = "${var.project_name}-gf-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path = "/api/health"
  }
}

resource "aws_lb_listener" "grafana" {
  load_balancer_arn = aws_lb.main.arn
  port              = "3000"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }
}

resource "aws_lb_target_group" "minio_api_public" {
  name        = "${var.project_name}-minio-pub-tg"
  port        = 9000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path = "/minio/health/live"
  }
}

# --- MinIO Console (Port 9001) ---
resource "aws_lb_target_group" "minio" {
  name        = "${var.project_name}-minio-tg"
  port        = 9001
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check {
    path = "/minio/health/live"
  }
}

resource "aws_lb_listener" "minio" {
  load_balancer_arn = aws_lb.main.arn
  port              = "9001"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.minio.arn
  }
}

# --- MinIO API Public (Port 9000) ---
resource "aws_lb_listener" "minio_api" {
  load_balancer_arn = aws_lb.main.arn
  port              = "9000"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.minio_api_public.arn
  }
}

resource "aws_lb_listener_rule" "minio_public" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 110 # Slightly lower priority than API (100)
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.minio_api_public.arn
  }
  
  condition {
    path_pattern {
      values = ["/pixel-canvas-snapshots/*"]
    }
  }
}
