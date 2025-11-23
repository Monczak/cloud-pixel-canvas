variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "pixel-canvas"
}

variable "lab_role_arn" {
  description = "AWS Academy LabRole ARN"
  type        = string
}

variable "canvas_width" {
  description = "Canvas width in pixels"
  type        = number
  default     = 100
}

variable "canvas_height" {
  description = "Canvas height in pixels"
  type        = number
  default     = 100
}

variable "max_snapshots" {
  description = "Maximum number of snapshots to keep"
  type        = number
  default     = 50
}

variable "heartbeat_interval" {
  description = "Heartbeat interval in seconds"
  type        = number
  default     = 20
}

variable "snapshot_schedule_expression" {
  description = "CloudWatch Events schedule expression for snapshots"
  type        = string
  default     = "rate(1 hour)"
}
