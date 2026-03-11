import boto3
import uuid
from decimal import Decimal

# --- CONFIGURACIÓN ---
region = 'us-east-1'
table_name = 'TarifasLogistica'

dynamodb = boto3.resource('dynamodb', region_name=region)
table = dynamodb.Table(table_name)

# --- DATOS ESTRUCTURADOS (Solo los primeros 5 registros convertidos al nuevo formato) ---
datos_completos = [
    # 1. Nixon Larios -> Mixco
    {
        'origen': 'Puerto Quetzal', 
        'destino': 'Mixco', 
        'proveedor': 'Nixon Larios',
        'fianza': 1000, 
        'dias_libres': 3, 
        'estadia': 500,
        'rango_base_precios': [
            {'min_kg': 0,     'max_kg': 20999, 'costo': 3600, 'concepto': 'Tarifa Base'},
            {'min_kg': 21000, 'max_kg': 25000, 'costo': 1000, 'concepto': 'Sobrepeso Nivel 1'},
            {'min_kg': 25001, 'max_kg': 28000, 'costo': 1500, 'concepto': 'Sobrepeso Nivel 2'}
        ]
    },
    # 2. Angel Paiz -> Mixco
    {
        'origen': 'Puerto Quetzal', 
        'destino': 'Mixco', 
        'proveedor': 'Angel Paiz',
        'fianza': 0, 
        'dias_libres': 3, 
        'estadia': 650,
        'rango_base_precios': [
            {'min_kg': 0,     'max_kg': 20999, 'costo': 3500, 'concepto': 'Tarifa Base'},
            {'min_kg': 21000, 'max_kg': 25000, 'costo': 690,  'concepto': 'Sobrepeso Nivel 1'},
            {'min_kg': 25001, 'max_kg': 28000, 'costo': 896,  'concepto': 'Sobrepeso Nivel 2'}
        ]
    },
    # 3. Transportes RAC -> Mixco
    {
        'origen': 'Puerto Quetzal', 
        'destino': 'Mixco', 
        'proveedor': 'Transportes RAC',
        'fianza': 600, 
        'dias_libres': 0, 
        'estadia': 500,
        'rango_base_precios': [
            {'min_kg': 0,     'max_kg': 20999, 'costo': 3500, 'concepto': 'Tarifa Base'},
            {'min_kg': 21000, 'max_kg': 25000, 'costo': 500,  'concepto': 'Sobrepeso Nivel 1'},
            {'min_kg': 25001, 'max_kg': 28000, 'costo': 500,  'concepto': 'Sobrepeso Nivel 2'}
        ]
    },
    # 4. Nixon Larios -> Zona 6,16,17,18
    {
        'origen': 'Puerto Quetzal', 
        'destino': 'Zona 6,16,17,18', 
        'proveedor': 'Nixon Larios',
        'fianza': 1000, 
        'dias_libres': 3, 
        'estadia': 500,
        'rango_base_precios': [
            {'min_kg': 0,     'max_kg': 20999, 'costo': 3600, 'concepto': 'Tarifa Base'},
            {'min_kg': 21000, 'max_kg': 25000, 'costo': 1000, 'concepto': 'Sobrepeso Nivel 1'},
            {'min_kg': 25001, 'max_kg': 28000, 'costo': 1500, 'concepto': 'Sobrepeso Nivel 2'}
        ]
    },
    # 5. Angel Paiz -> Zona 6,16,17,18
    {
        'origen': 'Puerto Quetzal', 
        'destino': 'Zona 6,16,17,18', 
        'proveedor': 'Angel Paiz',
        'fianza': 0, 
        'dias_libres': 3, 
        'estadia': 650,
        'rango_base_precios': [
            {'min_kg': 0,     'max_kg': 20999, 'costo': 3500, 'concepto': 'Tarifa Base'},
            {'min_kg': 21000, 'max_kg': 25000, 'costo': 690,  'concepto': 'Sobrepeso Nivel 1'},
            {'min_kg': 25001, 'max_kg': 28000, 'costo': 896,  'concepto': 'Sobrepeso Nivel 2'}
        ]
    }
]

def cargar_datos():
    print(f"🚀 Iniciando carga a la tabla: {table_name}")
    print(f"📦 Procesando {len(datos_completos)} registros con estructura anidada...")
    
    with table.batch_writer() as batch:
        for i, item in enumerate(datos_completos, 1):
            
            # 1. Convertir la lista de rangos a tipos DynamoDB (Decimal)
            rangos_decimal = []
            for rango in item['rango_base_precios']:
                rangos_decimal.append({
                    'min_kg': Decimal(str(rango['min_kg'])),
                    'max_kg': Decimal(str(rango['max_kg'])),
                    'costo':  Decimal(str(rango['costo'])),
                    'concepto': rango['concepto']
                })

            # 2. Crear el objeto registro principal
            registro = {
                'id': str(uuid.uuid4()),
                'origen': item['origen'],
                'destino': item['destino'],
                'proveedor': item['proveedor'],
                # Convertimos valores sueltos a Decimal
                'fianza': Decimal(str(item['fianza'])),
                'dias_libres': Decimal(str(item['dias_libres'])),
                'estadia': Decimal(str(item['estadia'])),
                # Insertamos la lista compleja preparada arriba
                'rango_base_precios': rangos_decimal
            }

            # 3. Enviar a DynamoDB
            batch.put_item(Item=registro)
            print(f"   ✅ ({i}/{len(datos_completos)}) Cargado: {registro['proveedor']} -> {registro['destino']}")

    print("\n✨ ¡Carga completada exitosamente!")

if __name__ == "__main__":
    cargar_datos()