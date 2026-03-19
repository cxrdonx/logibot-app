"""
Script para demostrar el impacto de las optimizaciones de tokens
"""
import json
from decimal import Decimal

# Simular datos de DynamoDB
datos_sin_optimizar = [
    {
        'id': '123',
        'origen': 'Puerto Quetzal',
        'destino': 'Mixco',
        'proveedor': 'Nixon Larios',
        'fianza': Decimal('1000'),
        'dias_libres': Decimal('3'),
        'estadia': Decimal('500'),
        'rango_base_precios': [
            {'min_kg': Decimal('0'), 'max_kg': Decimal('20999'), 'costo': Decimal('3600'), 'concepto': 'Tarifa Base'},
            {'min_kg': Decimal('21000'), 'max_kg': Decimal('25000'), 'costo': Decimal('1000'), 'concepto': 'Sobrepeso Nivel 1'},
            {'min_kg': Decimal('25001'), 'max_kg': Decimal('28000'), 'costo': Decimal('1500'), 'concepto': 'Sobrepeso Nivel 2'}
        ]
    }
] * 10  # Simular 10 registros

# Función de optimización (copiada del código)
def extraer_datos_relevantes(items, peso_kg=None):
    datos_simplificados = []
    
    for item in items:
        rangos_relevantes = item.get('rango_base_precios', [])
        
        if peso_kg and rangos_relevantes:
            rangos_filtrados = []
            for rango in rangos_relevantes:
                min_kg = float(rango.get('min_kg', 0))
                max_kg = float(rango.get('max_kg', float('inf')))
                
                if rango.get('concepto') == 'Tarifa Base' or (min_kg <= peso_kg <= max_kg):
                    rangos_filtrados.append({
                        'min_kg': min_kg,
                        'max_kg': max_kg,
                        'costo': float(rango.get('costo', 0)),
                        'concepto': rango.get('concepto')
                    })
            rangos_relevantes = rangos_filtrados
        else:
            rangos_relevantes = [
                {
                    'min_kg': float(r.get('min_kg', 0)),
                    'max_kg': float(r.get('max_kg', 0)),
                    'costo': float(r.get('costo', 0)),
                    'concepto': r.get('concepto')
                }
                for r in rangos_relevantes
            ]
        
        datos_simplificados.append({
            'origen': item.get('origen'),
            'destino': item.get('destino'),
            'proveedor': item.get('proveedor'),
            'dias_libres': float(item.get('dias_libres', 0)),
            'estadia': float(item.get('estadia', 0)),
            'fianza': float(item.get('fianza', 0)),
            'rangos': rangos_relevantes
        })
    
    return datos_simplificados

# Encoder para Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# COMPARACIÓN
print("="*80)
print("📊 ANÁLISIS DE OPTIMIZACIÓN DE TOKENS")
print("="*80)

# Caso 1: Sin optimización (enviando todo)
json_sin_optimizar = json.dumps(datos_sin_optimizar, cls=DecimalEncoder, indent=2)
tokens_sin_optimizar = len(json_sin_optimizar)

print(f"\n❌ SIN OPTIMIZACIÓN (10 registros completos):")
print(f"   Caracteres: {tokens_sin_optimizar:,}")
print(f"   Tokens estimados: ~{tokens_sin_optimizar // 4:,}")

# Caso 2: Con optimización de campos (sin peso)
datos_optimizados = extraer_datos_relevantes(datos_sin_optimizar)
json_optimizado = json.dumps(datos_optimizados, indent=2)
tokens_optimizado = len(json_optimizado)

print(f"\n✅ CON OPTIMIZACIÓN DE CAMPOS (sin peso):")
print(f"   Caracteres: {tokens_optimizado:,}")
print(f"   Tokens estimados: ~{tokens_optimizado // 4:,}")
print(f"   Ahorro: {((tokens_sin_optimizar - tokens_optimizado) / tokens_sin_optimizar * 100):.1f}%")

# Caso 3: Con optimización de campos + peso específico (22,000 kg)
datos_optimizados_peso = extraer_datos_relevantes(datos_sin_optimizar, peso_kg=22000)
json_optimizado_peso = json.dumps(datos_optimizados_peso, indent=2)
tokens_optimizado_peso = len(json_optimizado_peso)

print(f"\n✅ CON OPTIMIZACIÓN + FILTRO DE PESO (22,000 kg):")
print(f"   Caracteres: {tokens_optimizado_peso:,}")
print(f"   Tokens estimados: ~{tokens_optimizado_peso // 4:,}")
print(f"   Ahorro: {((tokens_sin_optimizar - tokens_optimizado_peso) / tokens_sin_optimizar * 100):.1f}%")

# Caso 4: Con límite de 5 registros
datos_optimizados_limite = datos_optimizados_peso[:5]
json_optimizado_limite = json.dumps(datos_optimizados_limite, indent=2)
tokens_optimizado_limite = len(json_optimizado_limite)

print(f"\n✅ CON TODAS LAS OPTIMIZACIONES (límite 5 registros):")
print(f"   Caracteres: {tokens_optimizado_limite:,}")
print(f"   Tokens estimados: ~{tokens_optimizado_limite // 4:,}")
print(f"   Ahorro: {((tokens_sin_optimizar - tokens_optimizado_limite) / tokens_sin_optimizar * 100):.1f}%")

# Resumen
print(f"\n{'='*80}")
print("💰 IMPACTO ECONÓMICO")
print("="*80)

# Asumiendo $0.008 por 1K tokens de entrada (Nova Pro)
costo_sin_optimizar = (tokens_sin_optimizar // 4) / 1000 * 0.008
costo_con_optimizar = (tokens_optimizado_limite // 4) / 1000 * 0.008

print(f"\nCosto por consulta (asumiendo $0.008 por 1K tokens):")
print(f"   Sin optimización: ${costo_sin_optimizar:.4f}")
print(f"   Con optimización: ${costo_con_optimizar:.4f}")
print(f"   Ahorro por consulta: ${costo_sin_optimizar - costo_con_optimizar:.4f}")

consultas_mensuales = 1000
ahorro_mensual = (costo_sin_optimizar - costo_con_optimizar) * consultas_mensuales
print(f"\n💵 Ahorro mensual (1,000 consultas): ${ahorro_mensual:.2f}")
print(f"💵 Ahorro anual: ${ahorro_mensual * 12:.2f}")

print(f"\n{'='*80}\n")
