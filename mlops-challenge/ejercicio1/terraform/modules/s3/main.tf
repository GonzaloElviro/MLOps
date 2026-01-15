# Módulo S3 con seguridad mejorada
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.tags
}

# Bloqueo de acceso público
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Cifrado en reposo
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  count = var.enable_encryption ? 1 : 0
  
  bucket = aws_s3_bucket.this.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = var.encryption_type
    }
  }
}

# Política de bucket para negar acceso público explícito
resource "aws_s3_bucket_policy" "deny_public" {
  bucket = aws_s3_bucket.this.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyPublicAccess"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.this.arn,
          "${aws_s3_bucket.this.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}