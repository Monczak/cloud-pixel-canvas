resource "aws_efs_file_system" "main" {
  creation_token = "${var.project_name}-portable-fs"
  tags = {
    Name = "${var.project_name}-portable-efs"
  }
}

resource "aws_efs_mount_target" "main" {
  count           = 2
  file_system_id  = aws_efs_file_system.main.id
  subnet_id       = module.vpc.private_subnets[count.index]
  security_groups = [aws_security_group.efs.id]
}

# --- Mongo (UID 999) ---
resource "aws_efs_access_point" "mongo" {
  file_system_id = aws_efs_file_system.main.id
  posix_user {
    gid = 999
    uid = 999
  }
  root_directory {
    path = "/mongo"
    creation_info {
      owner_gid   = 999
      owner_uid   = 999
      permissions = "755"
    }
  }
}

# --- MinIO (UID 1000) ---
resource "aws_efs_access_point" "minio" {
  file_system_id = aws_efs_file_system.main.id
  posix_user {
    gid = 1000
    uid = 1000
  }
  root_directory {
    path = "/minio"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }
}

# --- Postgres (UID 70 for Alpine) ---
resource "aws_efs_access_point" "postgres" {
  file_system_id = aws_efs_file_system.main.id
  posix_user {
    gid = 70
    uid = 70
  }
  root_directory {
    path = "/postgres"
    creation_info {
      owner_gid   = 70
      owner_uid   = 70
      permissions = "755"
    }
  }
}

# --- Grafana (UID 472) ---
resource "aws_efs_access_point" "grafana" {
  file_system_id = aws_efs_file_system.main.id
  posix_user {
    gid = 472
    uid = 472
  }
  root_directory {
    path = "/grafana"
    creation_info {
      owner_gid   = 472
      owner_uid   = 472
      permissions = "755"
    }
  }
}
