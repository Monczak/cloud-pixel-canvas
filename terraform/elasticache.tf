resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-valkey-subnet-group"
  subnet_ids = [aws_subnet.public_1.id, aws_subnet.public_2.id]
}

resource "aws_security_group" "valkey" {
  name        = "${var.project_name}-valkey-sg"
  description = "Valkey Security Group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Allow Valkey access from ECS tasks"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
}

resource "aws_elasticache_serverless_cache" "main" {
  engine = "valkey"
  name   = "${var.project_name}-valkey"

  cache_usage_limits {
    data_storage {
      maximum = 10
      unit    = "GB"
    }
    ecpu_per_second {
      maximum = 1000
    }
  }

  description          = "Pixel Canvas Valkey"
  major_engine_version = 7

  security_group_ids = [aws_security_group.valkey.id]
  subnet_ids         = [aws_subnet.public_1.id, aws_subnet.public_2.id]
}
