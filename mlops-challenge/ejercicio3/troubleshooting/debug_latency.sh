#!/bin/bash
# Script de debugging para problemas de latencia en Kubernetes/AWS

set -e

echo "🔍 Iniciando diagnóstico de problemas de latencia"
echo "=================================================="

# Variables
POD_NAME=${1:-$(kubectl get pods -n mlops -l app=mlops-inference -o jsonpath='{.items[0].metadata.name}')}
NODE_NAME=$(kubectl get pod $POD_NAME -n mlops -o jsonpath='{.spec.nodeName}')

echo "Pod: $POD_NAME"
echo "Node: $NODE_NAME"
echo ""

# 1. Verificar estado del pod
echo "1.  ESTADO DEL POD"
echo "-------------------"
kubectl describe pod $POD_NAME -n mlops | grep -A 10 "Status:"
kubectl get pod $POD_NAME -n mlops -o wide
echo ""

# 2. Verificar logs de la aplicación
echo "2.  LOGS DE LA APLICACIÓN"
echo "---------------------------"
kubectl logs $POD_NAME -n mlops --tail=50 --timestamps | grep -i "latency\|time\|error\|warn" | tail -20
echo ""

# 3. Verificar métricas Prometheus desde dentro del pod
echo "3.  MÉTRICAS INTERNAS"
echo "-----------------------"
kubectl exec $POD_NAME -n mlops -- sh -c '
  echo "Conexiones activas:"
  curl -s localhost:8080/metrics | grep active_connections
  echo ""
  echo "Latencia P95:"
  curl -s localhost:8080/metrics | grep inference_latency_seconds
' 2>/dev/null || echo "No se pudo obtener métricas"
echo ""

# 4. Diagnosticar red dentro del contenedor
echo "4.  DIAGNÓSTICO DE RED"
echo "-----------------------"
echo "DNS resolution test:"
kubectl exec $POD_NAME -n mlops -- nslookup google.com 2>/dev/null || echo "DNS test failed"
echo ""

echo "Conectividad a servicios dependientes:"
# Listar servicios dependientes (ajustar según tu caso)
SERVICES="mlops-inference-service:8080 prometheus-server:9090"
for svc in $SERVICES; do
  echo -n "Testing $svc: "
  kubectl exec $POD_NAME -n mlops -- timeout 2 bash -c "echo > /dev/tcp/${svc/://}" 2>/dev/null \
    && echo "✅" || echo "❌"
done
echo ""

# 5. Verificar recursos del nodo
echo "5.  RECURSOS DEL NODO"
echo "-----------------------"
kubectl describe node $NODE_NAME | grep -A 5 "Allocated resources:"
echo ""

# 6. Diagnosticar desde el nodo
echo "6.   DIAGNÓSTICO DESDE EL NODO"
echo "-------------------------------"
echo "Latencia de red del nodo a AWS services:"
echo "  Latencia a S3:"
ping -c 2 s3.${AWS_REGION}.amazonaws.com 2>/dev/null | grep "time=" || echo "    Test no disponible"
echo ""

# 7. Profiling de Python (si está habilitado)
echo "7.  PROFILING DE PYTHON"
echo "-------------------------"
kubectl exec $POD_NAME -n mlops -- sh -c '
  echo "Importando cProfile para profiling..."
  python3 -c "
  import cProfile, pstats, io
  pr = cProfile.Profile()
  pr.enable()
  # Simular una llamada a predicción
  import requests
  try:
      response = requests.post(\"http://localhost:8080/predict\", 
                              json={\"features\": {\"test\": 1}}, 
                              timeout=2)
  except:
      pass
  pr.disable()
  s = io.StringIO()
  ps = pstats.Stats(pr, stream=s).sort_stats(\"cumulative\")
  ps.print_stats(10)
  print(s.getvalue())
  " 2>/dev/null | head -30
' || echo "Profiling no disponible"
echo ""

# 8. Comandos avanzados de red
echo "8.  COMANDOS AVANZADOS DE RED"
echo "------------------------------"
cat << EOF
Comandos manuales para ejecutar según sea necesario:

# Dentro del pod:
kubectl exec -it $POD_NAME -n mlops -- bash
  netstat -tulpn           # Ver conexiones activas
  ss -s                    # Estadísticas de sockets
  top -b -n 1              # Uso de recursos
  python -m cProfile -o profile.stats script.py  # Profiling detallado

# Desde el nodo:
kubectl debug node/$NODE_NAME -it --image=nicolaka/netshoot
  tcptraceroute <servicio> # Trace route a servicios
  iperf3 -c <servidor>     # Test de ancho de banda
  tcpdump -i any port 8080 # Capturar tráfico HTTP

# AWS CLI:
aws cloudwatch get-metric-data --metric-data-queries ...
aws ec2 describe-instances --instance-ids ...
EOF

echo ""
echo " Diagnóstico completado. Revisar resultados arriba."