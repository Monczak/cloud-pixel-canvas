resource "random_password" "system_key" {
  length  = 32
  special = true
}
