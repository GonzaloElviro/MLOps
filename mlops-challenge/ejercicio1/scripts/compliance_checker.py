#!/usr/bin/env python3
"""
Script de validación de compliance para buckets S3
Verifica cifrado y acceso público, corrige automáticamente si es necesario
"""

import boto3
import argparse
import sys
from botocore.exceptions import ClientError, NoCredentialsError

class S3ComplianceChecker:
    def __init__(self, bucket_name, fix_violations=False):
        """
        Inicializa el checker de compliance
        
        Args:
            bucket_name: Nombre del bucket S3
            fix_violations: Si es True, corrige violaciones automáticamente
        """
        self.s3_client = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.bucket_name = bucket_name
        self.fix_violations = fix_violations
        self.violations = []
        
    def check_encryption(self):
        """Verifica si el bucket tiene cifrado habilitado"""
        try:
            response = self.s3_client.get_bucket_encryption(
                Bucket=self.bucket_name
            )
            rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            
            if rules:
                algorithm = rules[0].get('ApplyServerSideEncryptionByDefault', {}).get('SSEAlgorithm')
                print(f" Cifrado habilitado: {algorithm}")
                return True
            else:
                self.violations.append("Cifrado no habilitado")
                return False
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                self.violations.append("Cifrado no habilitado")
                return False
            else:
                print(f" Error verificando cifrado: {e}")
                return None
    
    def check_public_access(self):
        """Verifica si el bucket tiene acceso público"""
        try:
            # Verificar bloqueo de acceso público
            response = self.s3_client.get_public_access_block(
                Bucket=self.bucket_name
            )
            config = response['PublicAccessBlockConfiguration']
            
            checks = [
                ('block_public_acls', config['BlockPublicAcls']),
                ('block_public_policy', config['BlockPublicPolicy']),
                ('ignore_public_acls', config['IgnorePublicAcls']),
                ('restrict_public_buckets', config['RestrictPublicBuckets'])
            ]
            
            all_blocked = all(value for _, value in checks)
            
            if all_blocked:
                print(" Acceso público bloqueado correctamente")
                return True
            else:
                failed = [name for name, value in checks if not value]
                violation_msg = f"Configuración de acceso público insuficiente: {', '.join(failed)}"
                self.violations.append(violation_msg)
                return False
                
        except ClientError as e:
            print(f"❌ Error verificando acceso público: {e}")
            return None
    
    def check_bucket_policy(self):
        """Verifica si hay políticas que permitan acceso público"""
        try:
            policy = self.s3_client.get_bucket_policy(Bucket=self.bucket_name)
            policy_doc = policy.get('Policy', '{}')
            
            # Análisis simple de la política (en producción usaría una librería de análisis de políticas)
            if '"Principal":"*"' in policy_doc and '"Effect":"Allow"' in policy_doc:
                self.violations.append("Política de bucket permite acceso público")
                return False
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                print("ℹ  No hay política de bucket configurada")
                return True
            else:
                print(f" Error verificando política: {e}")
                return None
    
    def fix_encryption(self):
        """Habilita cifrado SSE-S3 en el bucket"""
        try:
            self.s3_client.put_bucket_encryption(
                Bucket=self.bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [
                        {
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }
                    ]
                }
            )
            print(" Cifrado habilitado (AES256)")
            return True
        except ClientError as e:
            print(f" Error habilitando cifrado: {e}")
            return False
    
    def fix_public_access(self):
        """Configura bloqueo de acceso público"""
        try:
            self.s3_client.put_public_access_block(
                Bucket=self.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            print("🔧 Bloqueo de acceso público configurado")
            return True
        except ClientError as e:
            print(f" Error configurando bloqueo de acceso público: {e}")
            return False
    
    def run_compliance_check(self):
        """Ejecuta todas las verificaciones de compliance"""
        print(f" Verificando compliance del bucket: {self.bucket_name}")
        print("-" * 50)
        
        # Ejecutar verificaciones
        self.check_encryption()
        self.check_public_access()
        self.check_bucket_policy()
        
        # Reportar resultados
        print("\n" + "=" * 50)
        print("RESULTADO DE COMPLIANCE")
        print("=" * 50)
        
        if not self.violations:
            print(" ¡Bucket cumple con todos los requisitos de compliance!")
            return True
        else:
            print(f"  Se encontraron {len(self.violations)} violaciones:")
            for i, violation in enumerate(self.violations, 1):
                print(f"  {i}. {violation}")
            
            # Corregir automáticamente si está habilitado
            if self.fix_violations:
                print("\n  Intentando corregir violaciones automáticamente...")
                self._auto_fix()
            else:
                print("\n Ejecute con --fix para corregir automáticamente")
            
            return False
    
    def _auto_fix(self):
        """Corrige violaciones automáticamente"""
        fixes_applied = 0
        
        if "Cifrado no habilitado" in self.violations:
            if self.fix_encryption():
                fixes_applied += 1
        
        if any("acceso público" in v.lower() for v in self.violations):
            if self.fix_public_access():
                fixes_applied += 1
        
        print(f"\n {fixes_applied} correcciones aplicadas")
        
        # Verificar nuevamente después de las correcciones
        if fixes_applied > 0:
            print("\n Verificando compliance después de correcciones...")
            self.violations = []
            self.check_encryption()
            self.check_public_access()
            
            if not self.violations:
                print(" ¡Todas las violaciones corregidas!")
            else:
                print("  Algunas violaciones persisten")


def main():
    parser = argparse.ArgumentParser(
        description='Valida compliance de seguridad en buckets S3'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='Nombre del bucket S3 a verificar'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Corrige violaciones automáticamente'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='Región AWS (por defecto: us-east-1)'
    )
    
    args = parser.parse_args()
    
    try:
        # Configurar región
        boto3.setup_default_session(region_name=args.region)
        
        # Ejecutar checker
        checker = S3ComplianceChecker(args.bucket, args.fix)
        success = checker.run_compliance_check()
        
        sys.exit(0 if success else 1)
        
    except NoCredentialsError:
        print(" Error: No se encontraron credenciales AWS")
        print("   Configure AWS CLI o defina variables de entorno:")
        print("   export AWS_ACCESS_KEY_ID=xxx")
        print("   export AWS_SECRET_ACCESS_KEY=xxx")
        sys.exit(1)
    except Exception as e:
        print(f" Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()