# Provider AWS
provider "aws" {
  region = var.aws_region
}

# Módulo de S3 seguro
module "secure_s3_bucket" {
  source = "./modules/s3"
  
  bucket_name = "mlops-sensitive-data-${var.environment}"
  environment = var.environment
  
  # Configuración de seguridad
  block_public_access = true
  enable_encryption   = true
  encryption_type     = "AES256"  # SSE-S3
  # Para mayor seguridad: encryption_type = "aws:kms"
  
  # Etiquetas para compliance
  tags = {
    Compliance  = "HIPAA"
    DataType    = "PII"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Módulo de EKS básico
module "mlops_eks_cluster" {
  source = "./modules/eks"
  
  cluster_name    = "mlops-cluster-${var.environment}"
  cluster_version = "1.27"
  
  # Configuración de red
  vpc_id          = var.vpc_id
  private_subnets = var.private_subnets
  
  # Configuración del nodo
  node_group_name = "mlops-nodes"
  instance_types  = ["m5.large"]
  min_size        = 2
  max_size        = 5
  desired_size    = 3
  
  # IAM para nodos
  node_iam_policies = [
    "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
    "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  ]
  
  tags = {
    Environment = var.environment
    Purpose     = "ML-Training"
  }
}

# Outputs para integración
output "s3_bucket_name" {
  value       = module.secure_s3_bucket.bucket_name
  description = "Nombre del bucket S3 seguro"
}

output "eks_cluster_endpoint" {
  value       = module.mlops_eks_cluster.cluster_endpoint
  description = "Endpoint del cluster EKS"
}

output "eks_cluster_id" {
  value       = module.mlops_eks_cluster.cluster_id
  description = "ID del cluster EKS"
}