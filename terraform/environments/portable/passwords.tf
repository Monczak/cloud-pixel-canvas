resource "random_password" "mongo_root" {
  length  = 16
  special = false
}

resource "random_password" "postgres_password" {
  length  = 16
  special = false
}

resource "random_password" "minio_access_key" {
  length  = 16
  special = false
  upper   = true
}

resource "random_password" "minio_secret_key" {
  length  = 24
  special = false
}

resource "random_password" "keycloak_admin_password" {
  length  = 16
  special = false
}

resource "random_password" "keycloak_client_secret" {
  length  = 32
  special = false
}

resource "random_password" "grafana_admin_password" {
  length  = 16
  special = false
}

resource "random_password" "system_key" {
  length  = 32
  special = false
}
