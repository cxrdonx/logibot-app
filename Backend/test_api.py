#!/usr/bin/env python3
"""
Script de prueba para el API CRUD de Tarifas Logísticas
Ejecuta operaciones CRUD completas para verificar el funcionamiento
"""

import requests
import json
import sys
from decimal import Decimal

# Colores para la consola
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

class TarifasAPITester:
    def __init__(self, api_url):
        self.api_url = api_url.rstrip('/')
        self.created_ids = []

    def test_create(self):
        """Prueba CREATE - Crear nueva tarifa"""
        print_info("Probando CREATE - Crear nueva tarifa...")
        
        data = {
            "origen": "Puerto Quetzal",
            "destino": "Test Ciudad",
            "proveedor": "Test Provider",
            "fianza": 1500,
            "dias_libres": 5,
            "estadia": 600,
            "rango_base_precios": [
                {
                    "min_kg": 0,
                    "max_kg": 20000,
                    "costo": 4000,
                    "concepto": "Tarifa Base Test"
                }
            ]
        }

        try:
            response = requests.post(
                f"{self.api_url}/tarifas",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 201:
                result = response.json()
                tarifa_id = result.get('id')
                self.created_ids.append(tarifa_id)
                print_success(f"Tarifa creada con ID: {tarifa_id}")
                return tarifa_id
            else:
                print_error(f"Error al crear tarifa: {response.status_code}")
                print_error(f"Respuesta: {response.text}")
                return None
        except Exception as e:
            print_error(f"Excepción: {str(e)}")
            return None

    def test_read_all(self):
        """Prueba READ - Listar todas las tarifas"""
        print_info("Probando READ - Listar todas las tarifas...")
        
        try:
            response = requests.get(f"{self.api_url}/tarifas")
            
            if response.status_code == 200:
                result = response.json()
                count = result.get('count', 0)
                print_success(f"Se obtuvieron {count} tarifas")
                return True
            else:
                print_error(f"Error al listar tarifas: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Excepción: {str(e)}")
            return False

    def test_read_by_id(self, tarifa_id):
        """Prueba READ - Obtener tarifa por ID"""
        print_info(f"Probando READ - Obtener tarifa por ID: {tarifa_id}...")
        
        try:
            response = requests.get(f"{self.api_url}/tarifas/{tarifa_id}")
            
            if response.status_code == 200:
                result = response.json()
                print_success(f"Tarifa obtenida: {result.get('proveedor')}")
                return True
            else:
                print_error(f"Error al obtener tarifa: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Excepción: {str(e)}")
            return False

    def test_read_filtered(self):
        """Prueba READ - Filtrar tarifas"""
        print_info("Probando READ - Filtrar por origen...")
        
        try:
            response = requests.get(
                f"{self.api_url}/tarifas",
                params={"origen": "Puerto Quetzal"}
            )
            
            if response.status_code == 200:
                result = response.json()
                count = result.get('count', 0)
                print_success(f"Se obtuvieron {count} tarifas de Puerto Quetzal")
                return True
            else:
                print_error(f"Error al filtrar tarifas: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Excepción: {str(e)}")
            return False

    def test_update(self, tarifa_id):
        """Prueba UPDATE - Actualizar tarifa"""
        print_info(f"Probando UPDATE - Actualizar tarifa {tarifa_id}...")
        
        data = {
            "fianza": 2000,
            "estadia": 750
        }

        try:
            response = requests.put(
                f"{self.api_url}/tarifas/{tarifa_id}",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print_success("Tarifa actualizada exitosamente")
                print_info(f"Nueva fianza: {result['item']['fianza']}")
                print_info(f"Nueva estadía: {result['item']['estadia']}")
                return True
            else:
                print_error(f"Error al actualizar tarifa: {response.status_code}")
                print_error(f"Respuesta: {response.text}")
                return False
        except Exception as e:
            print_error(f"Excepción: {str(e)}")
            return False

    def test_delete(self, tarifa_id):
        """Prueba DELETE - Eliminar tarifa"""
        print_info(f"Probando DELETE - Eliminar tarifa {tarifa_id}...")
        
        try:
            response = requests.delete(f"{self.api_url}/tarifas/{tarifa_id}")
            
            if response.status_code == 200:
                print_success("Tarifa eliminada exitosamente")
                return True
            else:
                print_error(f"Error al eliminar tarifa: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Excepción: {str(e)}")
            return False

    def run_all_tests(self):
        """Ejecuta todas las pruebas CRUD"""
        print("\n" + "="*60)
        print("🧪 INICIANDO PRUEBAS DEL API CRUD DE TARIFAS")
        print("="*60 + "\n")

        results = {
            "create": False,
            "read_all": False,
            "read_by_id": False,
            "read_filtered": False,
            "update": False,
            "delete": False
        }

        # 1. CREATE
        tarifa_id = self.test_create()
        results["create"] = tarifa_id is not None
        print()

        if tarifa_id:
            # 2. READ ALL
            results["read_all"] = self.test_read_all()
            print()

            # 3. READ BY ID
            results["read_by_id"] = self.test_read_by_id(tarifa_id)
            print()

            # 4. READ FILTERED
            results["read_filtered"] = self.test_read_filtered()
            print()

            # 5. UPDATE
            results["update"] = self.test_update(tarifa_id)
            print()

            # 6. DELETE
            results["delete"] = self.test_delete(tarifa_id)
            print()

        # Resumen
        print("="*60)
        print("📊 RESUMEN DE PRUEBAS")
        print("="*60)
        
        for test, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            color = Colors.GREEN if passed else Colors.RED
            print(f"{color}{status}{Colors.RESET} - {test.upper()}")
        
        total = len(results)
        passed = sum(results.values())
        print(f"\n{Colors.BLUE}Total: {passed}/{total} pruebas pasadas{Colors.RESET}")
        
        if passed == total:
            print(f"{Colors.GREEN}🎉 ¡Todas las pruebas pasaron exitosamente!{Colors.RESET}\n")
            return 0
        else:
            print(f"{Colors.RED}⚠ Algunas pruebas fallaron{Colors.RESET}\n")
            return 1

def main():
    if len(sys.argv) < 2:
        print_error("Uso: python test_api.py <API_URL>")
        print_info("Ejemplo: python test_api.py https://abc123.execute-api.us-east-1.amazonaws.com/prod")
        sys.exit(1)

    api_url = sys.argv[1]
    
    print_info(f"URL del API: {api_url}")
    
    tester = TarifasAPITester(api_url)
    exit_code = tester.run_all_tests()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
