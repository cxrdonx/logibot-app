#!/bin/bash

# Script de despliegue automatizado para el API de Tarifas Logísticas
# Autor: Sistema de IA
# Descripción: Despliega el stack CDK y prueba el API

set -e  # Salir si hay algún error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 Despliegue del API CRUD de Tarifas Logísticas        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Verificar dependencias
echo -e "${BLUE}📋 Verificando dependencias...${NC}"

if ! command -v cdk &> /dev/null; then
    echo -e "${RED}❌ AWS CDK no está instalado${NC}"
    echo "Instala con: npm install -g aws-cdk"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI no está instalado${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Todas las dependencias están instaladas${NC}"
echo ""

# 2. Instalar paquetes de Python
echo -e "${BLUE}📦 Instalando dependencias de Python...${NC}"
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencias instaladas${NC}"
echo ""

# 3. Sintetizar el stack
echo -e "${BLUE}🔨 Sintetizando el stack CDK...${NC}"
cdk synth > /dev/null
echo -e "${GREEN}✓ Stack sintetizado exitosamente${NC}"
echo ""

# 4. Preguntar si desea desplegar
echo -e "${YELLOW}¿Deseas desplegar el stack ahora? (y/n)${NC}"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠ Despliegue cancelado${NC}"
    exit 0
fi

# 5. Desplegar
echo ""
echo -e "${BLUE}🚀 Desplegando stack...${NC}"
echo ""

# Capturar la salida del despliegue
cdk deploy --require-approval never 2>&1 | tee deploy_output.txt

# 6. Extraer la URL del API
echo ""
echo -e "${BLUE}🔍 Extrayendo información del despliegue...${NC}"

API_URL=$(grep -o 'https://[^[:space:]]*execute-api[^[:space:]]*' deploy_output.txt | head -1)

if [ -z "$API_URL" ]; then
    echo -e "${YELLOW}⚠ No se pudo extraer la URL del API automáticamente${NC}"
    echo "Puedes obtenerla con:"
    echo "  aws cloudformation describe-stacks --stack-name IaProjectStack --query 'Stacks[0].Outputs'"
else
    echo -e "${GREEN}✓ API desplegado en: ${API_URL}${NC}"
    
    # Guardar URL en archivo
    echo "$API_URL" > api_url.txt
    echo -e "${GREEN}✓ URL guardada en: api_url.txt${NC}"
fi

echo ""
echo -e "${BLUE}📊 Información del despliegue:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Obtener información de la tabla
TABLE_NAME="TarifasLogistica"
echo -e "Tabla DynamoDB: ${GREEN}${TABLE_NAME}${NC}"

# Obtener información del User Pool
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --query "UserPools[?Name=='ia-project-user-pool'].Id" --output text 2>/dev/null || echo "")
if [ ! -z "$USER_POOL_ID" ]; then
    echo -e "Cognito User Pool ID: ${GREEN}${USER_POOL_ID}${NC}"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 7. Preguntar si desea ejecutar pruebas
if [ ! -z "$API_URL" ]; then
    echo -e "${YELLOW}¿Deseas ejecutar las pruebas del API ahora? (y/n)${NC}"
    read -r test_response
    
    if [[ "$test_response" =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}🧪 Ejecutando pruebas...${NC}"
        echo ""
        python3 test_api.py "$API_URL" || true
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Despliegue completado exitosamente                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 8. Instrucciones finales
echo -e "${BLUE}📝 Próximos pasos:${NC}"
echo ""
echo "1. Cargar datos iniciales:"
echo "   cd tests && python dynamo.py"
echo ""
echo "2. Probar el API:"
if [ ! -z "$API_URL" ]; then
    echo "   python3 test_api.py \"$API_URL\""
else
    echo "   python3 test_api.py <API_URL>"
fi
echo ""
echo "3. Usar el frontend:"
echo "   Abre frontend_example.html en tu navegador"
if [ ! -z "$API_URL" ]; then
    echo "   y pega esta URL: $API_URL"
fi
echo ""
echo "4. Ver logs:"
echo "   aws logs tail /aws/lambda/IaProjectStack-BackendReadTarifaHandler --follow"
echo ""
echo "5. Destruir el stack (cuando termines):"
echo "   cdk destroy"
echo ""

# Limpiar archivo temporal
rm -f deploy_output.txt

exit 0
