resource "aws_ecr_repository" "backend" {
  name         = "${var.project_name}-backend"
  force_delete = true
}

resource "aws_ecr_repository" "frontend" {
  name         = "${var.project_name}-frontend"
  force_delete = true
}

resource "aws_ecr_repository" "prometheus" {
  name         = "${var.project_name}-prometheus"
  force_delete = true
}

resource "aws_ecr_repository" "grafana" {
  name         = "${var.project_name}-grafana"
  force_delete = true
}

resource "aws_ecr_repository" "keycloak" {
  name         = "${var.project_name}-keycloak"
  force_delete = true
}

resource "aws_ecr_repository" "keycloak_setup" {
  name         = "${var.project_name}-keycloak-setup"
  force_delete = true
}

resource "aws_ecr_repository" "minio_setup" {
  name         = "${var.project_name}-minio-setup"
  force_delete = true
}
