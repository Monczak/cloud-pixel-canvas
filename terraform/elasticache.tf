resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-valkey-subnet-group"
  subnet_ids = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  tags = {
    Name = "${var.project_name}-valkey-subnet-group"
  }
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

  tags = {
    Name = "${var.project_name}-valkey-sg"
  }
}

resource "random_password" "valkey_auth" {
  length  = 32
  special = false
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-valkey"
  description                = "Pixel Canvas Valkey"
  node_type                  = "cache.t3.micro"
  num_cache_clusters         = 1
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.valkey.id]

  engine         = "valkey"
  engine_version = 8.2

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.valkey_auth.result

  tags = {
    Name = "${var.project_name}-valkey"
  }
}
