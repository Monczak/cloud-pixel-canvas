resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets
}

locals {
  alb_targets = {
    frontend = { port = 3000, path = "/", priority = 10 }
    backend  = { port = 8000, path = "/api/*", priority = 20, health = "/api/" }
    
    keycloak = { port = 8080, path = "/auth/*", priority = 30, health = "/auth/health/ready" }
    grafana  = { port = 3000, path = "/grafana/*", priority = 40, health = "/grafana/api/health" }
    
    # MinIO Console: Rewrite /minio/foo -> /foo because MinIO's console can't serve static files properly from a subpath
    minio = { 
      port = 9001, 
      path = "/minio/*", 
      priority = 50, 
      health = "/minio/health/live",
      rewrite = {
        regex   = "^/minio/(.*)$"
        replace = "/$1"
      }
    }
    
    minio-api = { port = 9000, path = "/pixel-canvas-snapshots/*", priority = 60, health = "/minio/health/live" }
  }
}

resource "aws_lb_target_group" "services" {
  for_each = local.alb_targets

  name        = "${var.project_name}-${each.key}-tg"
  port        = each.value.port
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path    = try(each.value.health, "/")
    matcher = "200-399"
  }
}

# --- Port 80 Listener (Main) ---
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.services["frontend"].arn
  }
}

# --- Routing Rules (Port 80) ---
resource "aws_lb_listener_rule" "services" {
  for_each = { for k, v in local.alb_targets : k => v if k != "frontend" }

  listener_arn = aws_lb_listener.http.arn
  priority     = each.value.priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.services[each.key].arn
  }

  condition {
    path_pattern {
      values = [each.value.path]
    }
  }

  dynamic "transform" {
    for_each = try(each.value.rewrite, null) != null ? [each.value.rewrite] : []
    content {
      type = "url-rewrite"
      
      url_rewrite_config {
        rewrite {
          regex   = transform.value.regex
          replace = transform.value.replace
        }
      }
    }
  }
}

# --- Redirect Rules (Slash Handling) ---
resource "aws_lb_listener_rule" "redirect_slash" {
  for_each = { for k, v in local.alb_targets : k => v if k != "frontend" && endswith(v.path, "/*") }

  listener_arn = aws_lb_listener.http.arn
  priority     = each.value.priority + 500

  action {
    type = "redirect"
    redirect {
      path        = "${trimsuffix(each.value.path, "/*")}/"
      status_code = "HTTP_301"
    }
  }

  condition {
    path_pattern {
      values = [trimsuffix(each.value.path, "/*")]
    }
  }
}
