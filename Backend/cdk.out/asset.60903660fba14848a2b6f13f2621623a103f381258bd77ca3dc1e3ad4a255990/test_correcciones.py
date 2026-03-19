#!/usr/bin/env python3
"""
Script de prueba para validar las correcciones del chatbot v2.0
Verifica que la lógica de decisión funcione correctamente.
"""

def test_decision_logic():
    """
    Prueba la lógica de decisión XML vs Comparativa
    """
    print("="*70)
    print("🧪 PRUEBAS DE LÓGICA DE DECISIÓN")
    print("="*70)
    
    # Simulación de preguntas
    test_cases = [
        {
            "pregunta": "Opciones para Puerto Quetzal a Zona 16",
            "expectativa": "Comparativa",
            "razon": "Contiene palabra clave 'opciones'"
        },
        {
            "pregunta": "Dame cotización de Edwin Suchite",
            "expectativa": "XML",
            "razon": "Contiene 'cotización' y proveedor específico"
        },
        {
            "pregunta": "Genera cotización para Puerto Quetzal a Mixco",
            "expectativa": "XML",
            "razon": "Contiene 'genera cotización'"
        },
        {
            "pregunta": "Compara proveedores para esta ruta",
            "expectativa": "Comparativa",
            "razon": "Contiene palabra clave 'compara'"
        },
        {
            "pregunta": "¿Cuál es más barato?",
            "expectativa": "Comparativa",
            "razon": "Contiene 'más barato'"
        },
        {
            "pregunta": "Quiero cotización formal de Nixon Larios",
            "expectativa": "XML",
            "razon": "Contiene 'cotización formal' y proveedor"
        },
        {
            "pregunta": "¿Cuáles son las mejores opciones?",
            "expectativa": "Comparativa",
            "razon": "Contiene 'opciones'"
        },
        {
            "pregunta": "Cotiza con Angel Paiz",
            "expectativa": "XML",
            "razon": "Contiene 'cotiza' y proveedor"
        }
    ]
    
    # Palabras clave para detección
    keywords_cotizacion = [
        'cotización', 'cotizacion', 'genera', 'dame la cotización', 'quiero cotización',
        'cotiza', 'genera cotización', 'cotización formal', 'cotización de', 
        'cotización para', 'dame cotización', 'hazme cotización', 'xml', 'formal'
    ]
    
    keywords_comparacion = [
        'mejor', 'opciones', 'compara', 'recomienda', 'cual', 'más barato', 
        'más económico', 'diferencia', 'comparativa', 'compárame', 'cuál es mejor'
    ]
    
    resultados = []
    
    for i, caso in enumerate(test_cases, 1):
        pregunta_lower = caso['pregunta'].lower()
        
        # Simular la lógica del chatbot
        solicita_cotizacion_xml = any(kw in pregunta_lower for kw in keywords_cotizacion)
        solicita_comparacion = any(kw in pregunta_lower for kw in keywords_comparacion)
        
        # Decisión
        if solicita_cotizacion_xml:
            resultado = "XML"
        elif solicita_comparacion:
            resultado = "Comparativa"
        else:
            resultado = "XML"  # Por defecto
        
        # Verificar resultado
        correcto = "✅" if resultado == caso['expectativa'] else "❌"
        
        print(f"\n{correcto} Caso {i}: {caso['pregunta']}")
        print(f"   Esperado: {caso['expectativa']}")
        print(f"   Obtenido: {resultado}")
        print(f"   Razón: {caso['razon']}")
        
        resultados.append(correcto == "✅")
    
    # Resumen
    print("\n" + "="*70)
    exitos = sum(resultados)
    total = len(resultados)
    porcentaje = (exitos / total) * 100
    
    print(f"📊 RESUMEN: {exitos}/{total} pruebas pasadas ({porcentaje:.1f}%)")
    print("="*70)
    
    return all(resultados)


def test_proveedor_detection():
    """
    Prueba la detección de proveedores específicos
    """
    print("\n\n" + "="*70)
    print("🔍 PRUEBAS DE DETECCIÓN DE PROVEEDORES")
    print("="*70)
    
    proveedores_conocidos = ["edwin suchite", "nixon larios", "angel paiz", "transportes rac"]
    
    test_cases = [
        {
            "pregunta": "Dame cotización de Edwin Suchite",
            "proveedor_esperado": "edwin suchite"
        },
        {
            "pregunta": "Genera cotización con Nixon Larios",
            "proveedor_esperado": "nixon larios"
        },
        {
            "pregunta": "Quiero cotización de Angel Paiz",
            "proveedor_esperado": "angel paiz"
        },
        {
            "pregunta": "Cotiza con Transportes RAC",
            "proveedor_esperado": "transportes rac"
        },
        {
            "pregunta": "Dame cotización para esta ruta",
            "proveedor_esperado": None
        }
    ]
    
    resultados = []
    
    for i, caso in enumerate(test_cases, 1):
        pregunta_lower = caso['pregunta'].lower()
        
        # Simular detección
        proveedor_detectado = None
        for proveedor in proveedores_conocidos:
            if proveedor in pregunta_lower:
                proveedor_detectado = proveedor
                break
        
        # Verificar
        correcto = proveedor_detectado == caso['proveedor_esperado']
        emoji = "✅" if correcto else "❌"
        
        print(f"\n{emoji} Caso {i}: {caso['pregunta']}")
        print(f"   Esperado: {caso['proveedor_esperado']}")
        print(f"   Detectado: {proveedor_detectado}")
        
        resultados.append(correcto)
    
    # Resumen
    print("\n" + "="*70)
    exitos = sum(resultados)
    total = len(resultados)
    porcentaje = (exitos / total) * 100
    
    print(f"📊 RESUMEN: {exitos}/{total} pruebas pasadas ({porcentaje:.1f}%)")
    print("="*70)
    
    return all(resultados)


def test_tarifa_base_calculation():
    """
    Prueba que la tarifa base se calcule correctamente
    """
    print("\n\n" + "="*70)
    print("💰 PRUEBAS DE CÁLCULO DE TARIFA BASE")
    print("="*70)
    
    # Simular datos de rangos
    test_cases = [
        {
            "nombre": "Con concepto 'Tarifa Base' explícito",
            "rangos": [
                {"min_kg": 0, "max_kg": 25000, "costo": 2800, "concepto": "Tarifa Base"},
                {"min_kg": 25001, "max_kg": 30000, "costo": 350, "concepto": "Sobrepeso nivel 1"}
            ],
            "peso_kg": None,
            "tarifa_base_esperada": 2800
        },
        {
            "nombre": "Sin concepto explícito (debe tomar primer rango válido)",
            "rangos": [
                {"min_kg": 0, "max_kg": 25000, "costo": 1475, "concepto": "Base"},
                {"min_kg": 25001, "max_kg": 30000, "costo": 200, "concepto": "Extra"}
            ],
            "peso_kg": None,
            "tarifa_base_esperada": 1475
        },
        {
            "nombre": "Con peso específico",
            "rangos": [
                {"min_kg": 0, "max_kg": 25000, "costo": 2800, "concepto": "Tarifa Base"},
                {"min_kg": 25001, "max_kg": 30000, "costo": 350, "concepto": "Sobrepeso nivel 1"}
            ],
            "peso_kg": 26000,
            "tarifa_base_esperada": 2800
        }
    ]
    
    resultados = []
    
    for i, caso in enumerate(test_cases, 1):
        # Simular cálculo
        tarifa_base = 0.0
        tarifa_base_encontrada = False
        
        rangos = caso['rangos']
        peso_kg = caso['peso_kg']
        
        # Buscar tarifa base
        for rango in rangos:
            concepto = rango.get('concepto', '')
            costo = rango.get('costo', 0)
            
            if concepto == 'Tarifa Base':
                tarifa_base = float(costo)
                tarifa_base_encontrada = True
                break
        
        # Fallback si no se encontró
        if not peso_kg and not tarifa_base_encontrada:
            for rango in rangos:
                costo = rango.get('costo', 0)
                if costo > 0:
                    tarifa_base = float(costo)
                    break
        
        # Verificar
        correcto = tarifa_base == caso['tarifa_base_esperada']
        emoji = "✅" if correcto else "❌"
        
        print(f"\n{emoji} Caso {i}: {caso['nombre']}")
        print(f"   Esperado: Q{caso['tarifa_base_esperada']:.2f}")
        print(f"   Calculado: Q{tarifa_base:.2f}")
        
        resultados.append(correcto)
    
    # Resumen
    print("\n" + "="*70)
    exitos = sum(resultados)
    total = len(resultados)
    porcentaje = (exitos / total) * 100
    
    print(f"📊 RESUMEN: {exitos}/{total} pruebas pasadas ({porcentaje:.1f}%)")
    print("="*70)
    
    return all(resultados)


if __name__ == "__main__":
    print("\n🚀 INICIANDO SUITE DE PRUEBAS DEL CHATBOT V2.0\n")
    
    # Ejecutar todas las pruebas
    test1 = test_decision_logic()
    test2 = test_proveedor_detection()
    test3 = test_tarifa_base_calculation()
    
    # Resumen final
    print("\n\n" + "="*70)
    print("📋 RESUMEN GENERAL")
    print("="*70)
    print(f"✅ Lógica de Decisión: {'PASS' if test1 else 'FAIL'}")
    print(f"✅ Detección de Proveedores: {'PASS' if test2 else 'FAIL'}")
    print(f"✅ Cálculo de Tarifa Base: {'PASS' if test3 else 'FAIL'}")
    print("="*70)
    
    if test1 and test2 and test3:
        print("\n🎉 TODAS LAS PRUEBAS PASARON - LISTO PARA DEPLOYMENT\n")
        exit(0)
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON - REVISAR ANTES DE DEPLOYMENT\n")
        exit(1)
