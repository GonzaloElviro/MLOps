# 🚀 MLOps Technical Challenge - Solución

Esta solución implementa un pipeline completo de MLOps con foco en Python y AWS, cubriendo:
- Infraestructura como Código (Terraform)
- Automatización CI/CD con detección de modelos
- Observabilidad y métricas de ML
- Debugging y troubleshooting

## 🏗️ Arquitectura

[Data Scientist] → [S3 Bucket] → [CI/CD Pipeline] → [EKS Cluster]
↓ ↓ ↓ ↓
[Modelo .pkl] [Validación] [Build & Test] [Deployment]
↓ ↓ ↓
[Docker Image] [Métricas] [FastAPI Service]

## 📁 Estructura del Proyecto

- `ejercicio1/`: Terraform + Python para infraestructura segura
- `ejercicio2/`: Microservicio FastAPI + CI/CD pipeline
- `ejercicio3/`: Observabilidad + debugging scripts

## 🚀 Cómo ejecutar

### Prerrequisitos
- Python 3.9+
- Terraform 1.5+
- Docker 20.10+
- AWS CLI configurado
- kubectl + acceso a EKS



1. Infraestructura


```bash
cd ejercicio1/terraform
terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"


Validacion del ejecercicio

2. Validar copliance S3

python ejercicio1/scripts/compliance_checker.py --bucket mi-bucket --fix

3. Construir y desplegar el microservicio

cd ejercicio2
docker build -t mlops-service:latest -f docker/Dockerfile .
docker run -p 8080:8080 mlops-service:latest
