# =============================================================================
# MH3: EFS File Storage Layer
# =============================================================================

resource "aws_efs_file_system" "app" {
  creation_token   = "53e94124-f81e-417a-bd1a-35f66ed1a00a"
  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  tags = {
    Name        = "${var.project_name}-efs"
    Environment = var.environment
  }
}

resource "aws_security_group" "efs_sg" {
  name        = "${var.project_name}-efs-sg-appvpc"
  description = "EFS mount in App VPC - NFS from ECS tasks"
  vpc_id      = aws_vpc.app.id

  ingress {
    description = "NFS from ECS tasks in private subnets"
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = ["10.0.11.0/24", "10.0.12.0/24"]
  }

  tags = { Name = "${var.project_name}-efs-sg" }
}

resource "aws_efs_mount_target" "app" {
  file_system_id  = aws_efs_file_system.app.id
  subnet_id       = aws_subnet.app_private.id
  security_groups = [aws_security_group.efs_sg.id]
}

resource "aws_efs_mount_target" "app_b" {
  file_system_id  = aws_efs_file_system.app.id
  subnet_id       = aws_subnet.app_private_b.id
  security_groups = [aws_security_group.efs_sg.id]
}

# Access Point for SQLite database (isolated from knowledge_base)
resource "aws_efs_access_point" "database" {
  file_system_id = aws_efs_file_system.app.id

  posix_user {
    uid = 1000
    gid = 1000
  }

  root_directory {
    path = "/database"
    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name = "${var.project_name}-efs-ap-database"
  }
}
