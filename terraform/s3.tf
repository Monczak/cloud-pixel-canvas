resource "random_id" "bucket_suffix" {
  byte_length = 8
}

resource "aws_s3_bucket" "snapshots" {
  bucket = "${var.project_name}-snapshots-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name = "${var.project_name}-snapshots"
  }
}

resource "aws_s3_bucket_public_access_block" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.snapshots.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.snapshots]
}

resource "aws_s3_bucket_cors_configuration" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
