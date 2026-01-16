variable "project_name" { type = string }
variable "app_name" { type = string }
variable "image" { type = string }
variable "cpu" { default = 256 }
variable "memory" { default = 512 }
variable "region" { type = string }
variable "role_arn" { type = string }
variable "vpc_id" { type = string }
variable "subnets" { type = list(string) }
variable "security_groups" { type = list(string) }

variable "container_port" {
  description = "Primary port the container exposes"
  type        = number
  default     = 0
}

variable "extra_ports" {
  description = "Additional ports to expose"
  type        = list(number)
  default     = []
}

variable "command" {
  type    = list(string)
  default = []
}

variable "container_user" {
  description = "The user to run the container as"
  type        = string
  default     = null
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "efs_config" {
  type = object({
    file_system_id  = string
    access_point_id = string
    container_path  = string
  })
  default = null
}

variable "lb_targets" {
  description = "List of Load Balancer Targets"
  type = list(object({
    target_group_arn = string
    container_port   = number
  }))
  default = []
}

variable "health_check_grace_period_seconds" {
  description = "Seconds to ignore failing load balancer health checks on startup"
  type        = number
  default     = 0
}

variable "deployment_minimum_healthy_percent" {
  type    = number
  default = 100
}

variable "deployment_maximum_percent" {
  type    = number
  default = 200
}
