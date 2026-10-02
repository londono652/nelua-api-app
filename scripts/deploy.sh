#!/usr/bin/env bash
# Despliega la API en un entorno y verifica que la versión nueva responde.
#   uso: bash scripts/deploy.sh <staging|prod> <tag-de-imagen>
#
# Todo lo que necesita de la infraestructura lo lee de Parameter Store:
# este script no conoce ARNs, nombres de clúster ni dominios.
set -euo pipefail

ENVIRONMENT="$1"
IMAGE_TAG="$2"
PROJECT="${PROJECT:-nelua-api}"

param() {
  aws ssm get-parameter --name "/$PROJECT/$1" --query Parameter.Value --output text
}

CLUSTER=$(param eks/cluster-name)
REPOSITORY=$(param ecr/repository-url)
HOSTNAME=$(param "dns/hostname-$ENVIRONMENT")

aws eks update-kubeconfig --name "$CLUSTER" >/dev/null

echo "Desplegando $REPOSITORY:$IMAGE_TAG en $ENVIRONMENT..."

# --wait espera a que los pods nuevos estén listos; --rollback-on-failure
# vuelve a la versión anterior si el despliegue no termina bien.
helm upgrade --install nelua-api chart \
  --namespace "$ENVIRONMENT" \
  --values "chart/values-$ENVIRONMENT.yaml" \
  --set image.repository="$REPOSITORY" \
  --set image.tag="$IMAGE_TAG" \
  --wait --rollback-on-failure --timeout 5m

echo "Verificando https://$HOSTNAME/healthz ..."
for attempt in $(seq 1 30); do
  version=$(curl -fsS --max-time 5 "https://$HOSTNAME/healthz" | jq -r .version 2>/dev/null || true)
  if [ "$version" = "$IMAGE_TAG" ]; then
    echo "OK: $ENVIRONMENT responde con la versión $version"
    exit 0
  fi
  echo "Intento $attempt: versión actual '${version:-sin respuesta}', esperando..."
  sleep 5
done

echo "ERROR: $ENVIRONMENT no respondió con la versión $IMAGE_TAG" >&2
exit 1
