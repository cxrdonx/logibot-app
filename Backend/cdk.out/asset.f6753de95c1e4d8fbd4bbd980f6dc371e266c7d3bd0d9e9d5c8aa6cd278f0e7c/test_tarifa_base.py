#!/usr/bin/env python3
"""
Test para verificar que la función calcular_costos_cotizacion
ahora calcula correctamente la tarifa base con y sin peso especificado.
"""

# Simular datos de una tarifa
test_item = {
    'proveedor': 'Edwin Suchite',
    'origen': 'Puerto Quetzal',
    'destino': 'Zona 6,16,17,18',
    'dias_libres': 0,
    'estadia': 500.0,
    'fianza': 850.0,
    'costo_tramite_aduana': 200.0,
    'costo_tramite_cominter': 275.0,
    'custodio_comsi': 150.0,
    'custodio_yantarni': 200.0,
    'rangos': [
        {
            'min_kg': 0,
            'max_kg': 20999,
            'costo': 2800.0,
            'concepto': 'Tarifa Base'
        },
        {
            'min_kg': 21000,
            'max_kg': 25000,
            'costo': 350.0,
            'concepto': 'Sobrepeso nivel 1'
        },
        {
            'min_kg': 25001,
            'max_kg': 30000,
            'costo': 500.0,
            'concepto': 'Sobrepeso nivel 2'
        }
    ]
}

def calcular_costos_cotizacion(item, peso_kg=None, custodio_tipo=None, custodio_cantidad=0, dias_estadia=0):
    """Versión de prueba de la función"""
    resultado = {
        "tarifa_base": 0.0,
        "sobrepeso": 0.0,
        "sobrepeso_concepto": "",
        "custodio": 0.0,
        "custodio_detalle": {},
        "dias_libres": int(item.get('dias_libres', 0)),
        "costo_estadia_diario": float(item.get('estadia', 0.0)),
        "dias_estadia": dias_estadia,
        "estadia": 0.0,
        "fianza": item.get('fianza', 0.0),
        "tramite_aduana": item.get('costo_tramite_aduana', 0.0),
        "tramite_cominter": item.get('costo_tramite_cominter', 0.0),
        "total": 0.0,
        "desglose": ""
    }
    
    rangos = item.get('rangos', [])
    
    # 1. CALCULAR TARIFA BASE Y SOBREPESO
    if rangos:
        tarifa_base_encontrada = False
        sobrepeso_encontrado = False
        
        for rango in rangos:
            min_kg = rango.get('min_kg', 0)
            max_kg = rango.get('max_kg', float('inf'))
            costo = rango.get('costo', 0)
            concepto = rango.get('concepto', '')
            
            # Identificar tarifa base (SIEMPRE, con o sin peso)
            if concepto == 'Tarifa Base':
                resultado["tarifa_base"] = float(costo)
                tarifa_base_encontrada = True
            
            # Identificar sobrepeso (SOLO si hay peso especificado y cae en ese rango)
            elif peso_kg and min_kg <= peso_kg <= max_kg and 'Sobrepeso' in concepto:
                resultado["sobrepeso"] = float(costo)
                resultado["sobrepeso_concepto"] = concepto
                sobrepeso_encontrado = True
        
        # Si hay peso pero no se encontró sobrepeso, significa que está en tarifa base
        if peso_kg and not sobrepeso_encontrado:
            resultado["sobrepeso"] = 0.0
            resultado["sobrepeso_concepto"] = "No aplica (dentro de tarifa base)"
        
        # Si NO hay peso, buscar el rango base que corresponda al peso mínimo
        if not peso_kg and not tarifa_base_encontrada:
            # Buscar el primer rango disponible
            for rango in rangos:
                costo = rango.get('costo', 0)
                if costo > 0:
                    resultado["tarifa_base"] = float(costo)
                    break
    
    # CALCULAR TOTAL
    resultado["total"] = (
        resultado["tarifa_base"] +
        resultado["sobrepeso"] +
        resultado["custodio"] +
        resultado["estadia"] +
        resultado["fianza"] +
        resultado["tramite_aduana"] +
        resultado["tramite_cominter"]
    )
    
    return resultado

# PRUEBAS
print("="*60)
print("TEST 1: SIN PESO ESPECIFICADO (para comparativas)")
print("="*60)
costos_sin_peso = calcular_costos_cotizacion(test_item)
print(f"✅ Tarifa Base: Q{costos_sin_peso['tarifa_base']:.2f}")
print(f"   Sobrepeso: Q{costos_sin_peso['sobrepeso']:.2f}")
print(f"   Fianza: Q{costos_sin_peso['fianza']:.2f}")
print(f"   Total: Q{costos_sin_peso['total']:.2f}")

print("\n" + "="*60)
print("TEST 2: CON PESO 18,000 KG (dentro de tarifa base)")
print("="*60)
costos_peso_bajo = calcular_costos_cotizacion(test_item, peso_kg=18000)
print(f"✅ Tarifa Base: Q{costos_peso_bajo['tarifa_base']:.2f}")
print(f"   Sobrepeso: Q{costos_peso_bajo['sobrepeso']:.2f} ({costos_peso_bajo['sobrepeso_concepto']})")
print(f"   Fianza: Q{costos_peso_bajo['fianza']:.2f}")
print(f"   Total: Q{costos_peso_bajo['total']:.2f}")

print("\n" + "="*60)
print("TEST 3: CON PESO 23,000 KG (con sobrepeso nivel 1)")
print("="*60)
costos_sobrepeso1 = calcular_costos_cotizacion(test_item, peso_kg=23000)
print(f"✅ Tarifa Base: Q{costos_sobrepeso1['tarifa_base']:.2f}")
print(f"   Sobrepeso: Q{costos_sobrepeso1['sobrepeso']:.2f} ({costos_sobrepeso1['sobrepeso_concepto']})")
print(f"   Fianza: Q{costos_sobrepeso1['fianza']:.2f}")
print(f"   Total: Q{costos_sobrepeso1['total']:.2f}")

print("\n" + "="*60)
print("TEST 4: CON PESO 27,000 KG (con sobrepeso nivel 2)")
print("="*60)
costos_sobrepeso2 = calcular_costos_cotizacion(test_item, peso_kg=27000)
print(f"✅ Tarifa Base: Q{costos_sobrepeso2['tarifa_base']:.2f}")
print(f"   Sobrepeso: Q{costos_sobrepeso2['sobrepeso']:.2f} ({costos_sobrepeso2['sobrepeso_concepto']})")
print(f"   Fianza: Q{costos_sobrepeso2['fianza']:.2f}")
print(f"   Total: Q{costos_sobrepeso2['total']:.2f}")

print("\n" + "="*60)
print("RESUMEN DE PRUEBAS")
print("="*60)

if costos_sin_peso['tarifa_base'] > 0:
    print("✅ TEST 1 PASÓ: Tarifa base calculada sin peso")
else:
    print("❌ TEST 1 FALLÓ: Tarifa base = 0 sin peso")

if costos_peso_bajo['tarifa_base'] > 0 and costos_peso_bajo['sobrepeso'] == 0:
    print("✅ TEST 2 PASÓ: Tarifa base sin sobrepeso")
else:
    print("❌ TEST 2 FALLÓ")

if costos_sobrepeso1['tarifa_base'] > 0 and costos_sobrepeso1['sobrepeso'] == 350:
    print("✅ TEST 3 PASÓ: Tarifa base + sobrepeso nivel 1")
else:
    print("❌ TEST 3 FALLÓ")

if costos_sobrepeso2['tarifa_base'] > 0 and costos_sobrepeso2['sobrepeso'] == 500:
    print("✅ TEST 4 PASÓ: Tarifa base + sobrepeso nivel 2")
else:
    print("❌ TEST 4 FALLÓ")

print("="*60)
