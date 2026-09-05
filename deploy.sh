#!/usr/bin/env bash

set -euo pipefail

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-Plugoh-dev-rg}"
REGISTRY_NAME="${AZURE_REGISTRY_NAME:-plugohdev}"
CONTAINER_APP="${AZURE_CONTAINER_APP:-resolveai-api-demo}"
IMAGE_NAME="${AZURE_IMAGE_NAME:-resolveai-api}"
IMAGE_TAG="${1:-demo}"
IMAGE="${REGISTRY_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

az account show --output none
az acr build --registry "${REGISTRY_NAME}" --image "${IMAGE_NAME}:${IMAGE_TAG}" .
az containerapp update \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --image "${IMAGE}" \
  --output none

FQDN="$(az containerapp show \
  --name "${CONTAINER_APP}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query properties.configuration.ingress.fqdn \
  --output tsv)"

curl --fail --show-error --silent --retry 6 --retry-delay 5 \
  "https://${FQDN}/healthz"
printf '\nDeployed %s to https://%s\n' "${IMAGE}" "${FQDN}"
