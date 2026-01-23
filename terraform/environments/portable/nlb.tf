resource "aws_lb" "internal" {
  name                             = "${var.project_name}-internal-nlb"
  internal                         = true
  load_balancer_type               = "network"
  subnets                          = module.vpc.private_subnets
  security_groups                  = [aws_security_group.ecs_tasks.id]
  enable_cross_zone_load_balancing = true
}

locals {
  nlb_services = {
    backend    = { port = 8000 }
    keycloak   = { port = 8080 }
    mongo      = { port = 27017 }
    valkey     = { port = 6379 }
    postgres   = { port = 5432 }
    minio      = { port = 9000 }
    prometheus = { port = 9090 }
  }
}

resource "aws_lb_target_group" "internal_services" {
  for_each = local.nlb_services

  name        = "${var.project_name}-${each.key}-int-tg"
  port        = each.value.port
  protocol    = "TCP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    protocol = "TCP"
  }
}

resource "aws_lb_listener" "internal_services" {
  for_each = local.nlb_services

  load_balancer_arn = aws_lb.internal.arn
  port              = each.value.port
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.internal_services[each.key].arn
  }
}
