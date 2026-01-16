resource "aws_ecr_repository" "backend" {
  name         = "pixel-canvas-backend"
  force_delete = true
}

resource "aws_ecr_repository" "frontend" {
  name         = "pixel-canvas-frontend"
  force_delete = true
}

resource "aws_ecr_repository" "prometheus" {
  name         = "pixel-canvas-prometheus"
  force_delete = true
}

resource "aws_ecr_repository" "grafana" {
  name         = "pixel-canvas-grafana"
  force_delete = true
}

resource "aws_ecr_repository" "keycloak" {
  name         = "pixel-canvas-keycloak"
  force_delete = true
}

resource "aws_ecr_repository" "keycloak_setup" {
  name         = "pixel-canvas-keycloak-setup"
  force_delete = true
}
