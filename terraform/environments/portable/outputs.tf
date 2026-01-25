output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "backend_repo" {
  value = aws_ecr_repository.backend.repository_url
}

output "frontend_repo" {
  value = aws_ecr_repository.frontend.repository_url
}

output "prometheus_repo" {
  value = aws_ecr_repository.prometheus.repository_url
}

output "grafana_repo" {
  value = aws_ecr_repository.grafana.repository_url
}

output "keycloak_repo" {
  value = aws_ecr_repository.keycloak.repository_url
}

output "keycloak_setup_repo" {
  value = aws_ecr_repository.keycloak_setup.repository_url
}

output "minio_setup_repo" {
  value = aws_ecr_repository.minio_setup.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "private_subnets" {
  value = module.vpc.private_subnets
}

output "ecs_sg_id" {
  value = aws_security_group.ecs_tasks.id
}

output "credentials" {
  sensitive = true
  value = {
    mongo_root          = random_password.mongo_root.result
    minio_perm_admin    = random_password.minio_console_admin_password.result
    keycloak_admin      = random_password.keycloak_bootstrap_admin_password.result
    keycloak_perm_admin = random_password.keycloak_permanent_admin_password.result
    grafana_admin       = random_password.grafana_admin_password.result
    system_key          = random_password.system_key.result
  }
}
