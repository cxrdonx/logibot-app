import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TarifasService, Tarifa } from '../../services/tarifas.service';
import { RangoBasePrice } from '../../services/tarifas.service';

@Component({
  selector: 'app-tarifas-menu',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tarifas-menu.html',
  styleUrls: ['./tarifas-menu.css']
})
export class TarifasMenuComponent implements OnInit {
  tarifas: Tarifa[] = [];
  filteredTarifas: Tarifa[] = [];
  
  // Modos de operación
  operationMode: 'create' | 'update' | 'delete' = 'create';
  
  // Tarifa seleccionada para editar/eliminar
  selectedTarifa: Tarifa | null = null;
  selectedTarifaId: string = '';
  
  // Formulario de tarifa
  tarifaForm: Tarifa = this.getEmptyTarifa();
  
  // Estado
  loading: boolean = false;
  message: string = '';
  messageType: 'success' | 'error' | '' = '';
  
  // Rango de precios temporal
  newRango: RangoBasePrice = {
    min_kg: 0,
    max_kg: 0,
    costo: 0,
    concepto: ''
  };

  constructor(private tarifasService: TarifasService, private router: Router) {}

  ngOnInit(): void {
    this.loadTarifas();
  }

  navigateToChat(): void {
    this.router.navigate(['/']);
  }

  getEmptyTarifa(): Tarifa {
    return {
      origen: '',
      destino: '',
      proveedor: '',
      fianza: 0,
      dias_libres: 0,
      estadia: 0,
      tramite_de_aduana_cominter: 0,
      condiciones_de_aduana_cominter: '',
      tramite_aduana: 0,
      condiciones_aduana: '',
      custodio_comsi: 0,
      custodio_yantarni: 0,
      rango_base_precios: []
    };
  }

  loadTarifas(): void {
    this.loading = false;
    this.tarifasService.getTarifas().subscribe({
      next: (response:any) => {
        
        console.log('Response del API:', response);
        
        // Manejar diferentes estructuras de respuesta
        let tarifasData;
        
        if (response && typeof response === 'object') {
          // Si tiene items (minúscula) - respuesta actual del API
          if (response.items && Array.isArray(response.items)) {
            tarifasData = response.items;
          }
          // Si tiene Items (mayúscula) - respuesta de DynamoDB
          else if (response.Items && Array.isArray(response.Items)) {
            tarifasData = response.Items;
          }
          // Si tiene body (respuesta con statusCode)
          else if (response.body) {
            tarifasData = typeof response.body === 'string' 
              ? JSON.parse(response.body) 
              : response.body;
          } 
          // Si es un array directo
          else if (Array.isArray(response)) {
            tarifasData = response;
          }
          // Otro caso
          else {
            tarifasData = response;
          }
        } else {
          tarifasData = [];
        }
        
        // Asegurar que sea un array
        this.tarifas = Array.isArray(tarifasData) ? tarifasData : [];
        this.filteredTarifas = [...this.tarifas];
        
        console.log('Tarifas cargadas:', this.tarifas);
        console.log('Cantidad de tarifas:', this.tarifas.length);
        this.loading = false;
      },
      error: (error) => {
        console.error('Error cargando tarifas:', error);
        this.showMessage('Error al cargar las tarifas', 'error');
        this.tarifas = [];
        this.filteredTarifas = [];
        this.loading = false;
      }
    });
  }

  onModeChange(): void {
    this.selectedTarifa = null;
    this.selectedTarifaId = '';
    this.tarifaForm = this.getEmptyTarifa();
    this.message = '';
  }

  onTarifaSelect(): void {
    if (!this.selectedTarifaId) {
      this.selectedTarifa = null;
      this.tarifaForm = this.getEmptyTarifa();
      return;
    }

    const tarifa = this.tarifas.find(t => t.id === this.selectedTarifaId);
    if (tarifa) {
      this.selectedTarifa = tarifa;
      if (this.operationMode === 'update') {
        // Copiar los datos de la tarifa seleccionada al formulario
        this.tarifaForm = { ...tarifa };
        if (!this.tarifaForm.rango_base_precios) {
          this.tarifaForm.rango_base_precios = [];
        }
      }
      
      // Scroll hacia el formulario después de seleccionar
      setTimeout(() => {
        const formElement = document.querySelector('.form-card');
        if (formElement) {
          formElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    }
  }

  getTarifaLabel(tarifa: Tarifa): string {
    return `${tarifa.proveedor} - ${tarifa.origen} → ${tarifa.destino}`;
  }

  createTarifa(): void {
    if (!this.validateForm()) {
      return;
    }

    this.loading = true;
    this.tarifasService.createTarifa(this.tarifaForm).subscribe({
      next: (response) => {
        this.showMessage('Tarifa creada exitosamente', 'success');
        this.tarifaForm = this.getEmptyTarifa();
        // Recargar la página completa después de crear
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      },
      error: (error) => {
        console.error('Error creando tarifa:', error);
        this.showMessage('Error al crear la tarifa', 'error');
        this.loading = false;
      }
    });
  }

  updateTarifa(): void {
    if (!this.selectedTarifa || !this.selectedTarifa.id) {
      this.showMessage('Selecciona una tarifa para actualizar', 'error');
      this.loading = false;
      return;
    }

    if (!this.validateForm()) {
      this.loading = false;
      return;
    }

    this.loading = true;
    const { id, ...tarifaData } = this.tarifaForm;
    
    this.tarifasService.updateTarifa(this.selectedTarifa.id, tarifaData).subscribe({
      next: (response) => {
        this.showMessage('Tarifa actualizada exitosamente', 'success');
        this.selectedTarifa = null;
        this.selectedTarifaId = '';
        this.tarifaForm = this.getEmptyTarifa();
        // Recargar la página completa después de actualizar
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      },
      error: (error) => {
        console.error('Error actualizando tarifa:', error);
        this.showMessage('Error al actualizar la tarifa', 'error');
        this.loading = false;
      }
    });
  }

  deleteTarifa(): void {
    if (!this.selectedTarifa || !this.selectedTarifa.id) {
      this.showMessage('Selecciona una tarifa para eliminar', 'error');
      return;
    }

    if (!confirm(`¿Estás seguro de eliminar la tarifa de ${this.selectedTarifa.proveedor}?`)) {
      return;
    }

    this.loading = true;
    this.tarifasService.deleteTarifa(this.selectedTarifa.id).subscribe({
      next: (response) => {
        this.showMessage('Tarifa eliminada exitosamente', 'success');
        this.selectedTarifa = null;
        this.selectedTarifaId = '';
        // Recargar la página completa después de eliminar
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      },
      error: (error) => {
        console.error('Error eliminando tarifa:', error);
        this.showMessage('Error al eliminar la tarifa', 'error');
        this.loading = false;
      }
    });
  }

  validateForm(): boolean {
    if (!this.tarifaForm.origen || !this.tarifaForm.destino || !this.tarifaForm.proveedor) {
      this.showMessage('Por favor completa los campos obligatorios (Origen, Destino, Proveedor)', 'error');
      return false;
    }
    return true;
  }

  // Gestión de rangos de precios
  addRango(): void {
    if (!this.newRango.concepto || this.newRango.costo <= 0) {
      this.showMessage('Completa todos los campos del rango de precios', 'error');
      return;
    }

    if (!this.tarifaForm.rango_base_precios) {
      this.tarifaForm.rango_base_precios = [];
    }

    this.tarifaForm.rango_base_precios.push({ ...this.newRango });
    
    // Resetear formulario de rango
    this.newRango = {
      min_kg: 0,
      max_kg: 0,
      costo: 0,
      concepto: ''
    };
    
    this.showMessage('Rango agregado', 'success');
  }

  removeRango(index: number): void {
    if (this.tarifaForm.rango_base_precios) {
      this.tarifaForm.rango_base_precios.splice(index, 1);
    }
  }

  showMessage(text: string, type: 'success' | 'error'): void {
    this.message = text;
    this.messageType = type;
    setTimeout(() => {
      this.message = '';
      this.messageType = '';
    }, 5000);
  }
}
