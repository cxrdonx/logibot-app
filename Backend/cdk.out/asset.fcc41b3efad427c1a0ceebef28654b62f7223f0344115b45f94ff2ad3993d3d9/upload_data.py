import boto3
import uuid
from decimal import Decimal

# --- CONFIGURACIÓN ---
region = 'us-east-1'
table_name = 'TarifasLogistica'

dynamodb = boto3.resource('dynamodb', region_name=region)
table = dynamodb.Table(table_name)

# --- DATA ESTRUCTURADA (Ahora con ORIGEN explícito) ---
datos_completos = [
    # --- ORIGEN: PUERTO QUETZAL ---
    {'origen': 'Puerto Quetzal', 'destino': 'Mixco', 'proveedor': 'Nixon Larios',    'base': 3600, 'sp1': 1000, 'sp2': 1500, 'fianza':'1000', 'dias_libres': 3, 'estadia': 500, 'tramite_aduana_cominter': 825, 'condiciones_cominter': 'Hasta 50 Lineas Adicionles 2.50', 'tramite_aduana_ard': 650,'condiciones_ard': 'Hasta 10 Lineas Adicionles 0.75', 'custodio_comsi':450, 'custodio_yantarni':375},
    {'origen': 'Puerto Quetzal', 'destino': 'Mixco', 'proveedor': 'Angel Paiz',      'base': 3500, 'sp1': 690,  'sp2': 896, 'fianza':'0', 'dias_libres': 3, 'estadia': 650, 'tramite_aduana_cominter': 825, 'condiciones_cominter': 'Hasta 50 Lineas Adicionles 2.50', 'tramite_aduana_ard': 650,'condiciones_ard': 'Hasta 10 Lineas Adicionles 0.75', 'custodio_comsi':450, 'custodio_yantarni':375},
    {'origen': 'Puerto Quetzal', 'destino': 'Mixco', 'proveedor': 'Transportes RAC', 'base': 3500, 'sp1': 500,  'sp2': 500, 'fianza':'600', 'dias_libres': 0, 'estadia': 500, 'tramite_aduana_cominter': 825, 'condiciones_cominter': 'Hasta 50 Lineas Adicionles 2.50', 'tramite_aduana_ard': 650,'condiciones_ard': 'Hasta 10 Lineas Adicionles 0.75', 'custodio_comsi':450, 'custodio_yantarni':375},

    # Zonas Norte
    {'origen': 'Puerto Quetzal', 'destino': 'Zona 6,16,17,18',  'proveedor': 'Nixon Larios', 'base': 3600, 'sp1': 1000, 'sp2': 1500, 'fianza': 1000, 'dias_libres': 3, 'estadia': 500, 'tramite_aduana_cominter': 825, 'condiciones_cominter': 'Hasta 50 Lineas Adicionles 2.50', 'tramite_aduana_ard': 650,'condiciones_ard': 'Hasta 10 Lineas Adicionles 0.75', 'custodio_comsi':450, 'custodio_yantarni':375},
    {'origen': 'Puerto Quetzal', 'destino': 'Zona 6,16,17,18',  'proveedor': 'Angel Paiz',   'base': 3500, 'sp1': 690,  'sp2': 896,  'fianza': 0, 'dias_libres': 3, 'estadia': 650, 'tramite_aduana_cominter': 825, 'condiciones_cominter': 'Hasta 50 Lineas Adicionles 2.50', 'tramite_aduana_ard': 650,'condiciones_ard': 'Hasta 10 Lineas Adicionles 0.75', 'custodio_comsi':450, 'custodio_yantarni':375},
    {'origen': 'Puerto Quetzal', 'destino': 'Zona 6,16,17,18', 'proveedor': 'Transportes RAC', 'base': 3500, 'sp1': 123, 'sp2': 600, 'fianza': 600, 'dias_libres': 3, 'estadia': 600, 'tramite_aduana_cominter': 825, 'condiciones_cominter': 'Hasta 50 Lineas Adicionles 2.50', 'tramite_aduana_ard': 650,'condiciones_ard': 'Hasta 10 Lineas Adicionles 0.75', 'custodio_comsi':450, 'custodio_yantarni':375},

    # Villa Nueva
    {'origen': 'Puerto Quetzal', 'destino': 'Villa Nueva', 'proveedor': 'Nixon Larios',  'base': 3500, 'sp1': 1000, 'sp2': 1500, 'dias_libres': 3, 'estadia': 500},
    {'origen': 'Puerto Quetzal', 'destino': 'Villa Nueva', 'proveedor': 'Angel Paiz',    'base': 3500, 'sp1': 690,  'sp2': 896,  'dias_libres': 3, 'estadia': 650},
    {'origen': 'Puerto Quetzal', 'destino': 'Villa Nueva', 'proveedor': 'Edwin Suchite', 'base': 3300, 'sp1': 500,  'sp2': 500,  'dias_libres': 3, 'estadia': 450},

    # Escuintla
    {'origen': 'Puerto Quetzal', 'destino': 'Escuintla', 'proveedor': 'Transportes RAC', 'base': 2800, 'sp1': 400, 'sp2': 800, 'dias_libres': 3, 'estadia': 400},
    {'origen': 'Puerto Quetzal', 'destino': 'Escuintla', 'proveedor': 'Fletes del Sur',  'base': 2750, 'sp1': 450, 'sp2': 850, 'dias_libres': 2, 'estadia': 350},

    # Amatitlán
    {'origen': 'Puerto Quetzal', 'destino': 'Amatitlán', 'proveedor': 'Angel Paiz',   'base': 3200, 'sp1': 600, 'sp2': 800, 'dias_libres': 3, 'estadia': 550},
    {'origen': 'Puerto Quetzal', 'destino': 'Amatitlán', 'proveedor': 'Nixon Larios', 'base': 3300, 'sp1': 800, 'sp2': 1200, 'dias_libres': 3, 'estadia': 500},

    # Carr. El Salvador
    {'origen': 'Puerto Quetzal', 'destino': 'Carr. El Salvador', 'proveedor': 'Nixon Larios', 'base': 4000, 'sp1': 1200, 'sp2': 1800, 'dias_libres': 3, 'estadia': 600},

    # Chimaltenango
    {'origen': 'Puerto Quetzal', 'destino': 'Chimaltenango', 'proveedor': 'Edwin Suchite', 'base': 4500, 'sp1': 700, 'sp2': 900, 'dias_libres': 4, 'estadia': 500},

    # Zona 12
    {'origen': 'Puerto Quetzal', 'destino': 'Zona 12', 'proveedor': 'Transportes RAC', 'base': 3400, 'sp1': 500, 'sp2': 600, 'dias_libres': 3, 'estadia': 550},
    {'origen': 'Puerto Quetzal', 'destino': 'Zona 12', 'proveedor': 'Transportes Golán', 'base': 3500, 'sp1': 500, 'sp2': 500, 'dias_libres': 3, 'estadia': 500},

    # --- ORIGEN: SANTO TOMÁS (Atlántico) ---
    {'origen': 'Santo Tomás', 'destino': 'Ciudad Capital', 'proveedor': 'Transportes Golán', 'base': 5000, 'sp1': 800, 'sp2': 1000, 'dias_libres': 4, 'estadia': 800},
    {'origen': 'Santo Tomás', 'destino': 'Mixco',          'proveedor': 'Transportes RAC',   'base': 5200, 'sp1': 850, 'sp2': 1100, 'dias_libres': 4, 'estadia': 800},
]

def cargar_datos():
    print(f"🚀 Iniciando carga masiva a la tabla: {table_name}")
    print(f"📦 Total de registros a procesar: {len(datos_completos)}")
    
    with table.batch_writer() as batch:
        for i, item in enumerate(datos_completos, 1):
            registro = {
                'id': str(uuid.uuid4()),
                'origen': item['origen'],     # Campo obligatorio
                'destino': item['destino'],
                'proveedor': item['proveedor'],
                'base': Decimal(str(item['base'])),
                'sp1': Decimal(str(item['sp1'])),
                'sp2': Decimal(str(item['sp2'])),
                'dias_libres': Decimal(str(item['dias_libres'])),
                'estadia': Decimal(str(item['estadia']))
            }
            batch.put_item(Item=registro)
            print(f"   ✅ ({i}/{len(datos_completos)}) Cargado: [{registro['origen']}] -> {registro['destino']} ({registro['proveedor']})")

    print("\n✨ ¡Carga completada exitosamente!")

if __name__ == "__main__":
    cargar_datos()