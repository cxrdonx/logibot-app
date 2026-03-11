import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TarifasService, Tarifa, RangoBasePrice } from '../../services/tarifas.service';
import { AuthService } from '../../services/auth.service';
import { HeaderComponent } from '../header/header';

@Component({
  selector: 'app-tarifas-form',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './tarifas-form.html',
  styleUrls: ['./tarifas-form.css']
})
export class TarifasFormComponent implements OnInit {
  tarifa: Tarifa = {
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

  isEditMode = false;
  loading = false;
  error: string | null = null;
  tarifaId: string | null = null;
  newRangoPrice: RangoBasePrice = { min_kg: 0, max_kg: 0, costo: 0, concepto: '' };

  constructor(
    private tarifasService: TarifasService,
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      if (params['id'] && params['id'] !== 'create') {
        this.isEditMode = true;
        this.tarifaId = params['id'];
        this.loadTarifa(params['id']);
      }
    });
  }

  onLogout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  onReset(): void {
    this.loadTarifa(this.tarifaId || '');
  }

  loadTarifa(id: string): void {
    this.loading = true;
    this.tarifasService.getTarifaById(id).subscribe({
      next: (data) => {
        this.tarifa = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error loading tarifa: ' + err.message;
        this.loading = false;
      }
    });
  }

  addRangoPrice(): void {
    if (this.newRangoPrice.costo > 0 && this.newRangoPrice.concepto) {
      if (!this.tarifa.rango_base_precios) {
        this.tarifa.rango_base_precios = [];
      }
      this.tarifa.rango_base_precios.push({ ...this.newRangoPrice });
      this.newRangoPrice = { min_kg: 0, max_kg: 0, costo: 0, concepto: '' };
    }
  }

  removeRangoPrice(index: number): void {
    this.tarifa.rango_base_precios.splice(index, 1);
  }

  saveTarifa(): void {
    if (!this.validateForm()) {
      return;
    }

    this.loading = true;
    this.error = null;

    const operation = this.isEditMode && this.tarifaId
      ? this.tarifasService.updateTarifa(this.tarifaId, this.tarifa)
      : this.tarifasService.createTarifa(this.tarifa);

    operation.subscribe({
      next: () => {
        this.router.navigate(['/tarifas']);
      },
      error: (err) => {
        this.error = 'Error saving tarifa: ' + err.message;
        this.loading = false;
      }
    });
  }

  validateForm(): boolean {
    if (!this.tarifa.origen || !this.tarifa.destino || !this.tarifa.proveedor) {
      this.error = 'Los campos origen, destino y proveedor son requeridos';
      return false;
    }
    if (this.tarifa.fianza < 0 || this.tarifa.dias_libres < 0 || this.tarifa.estadia < 0) {
      this.error = 'Los valores numéricos no pueden ser negativos';
      return false;
    }
    return true;
  }

  cancel(): void {
    this.router.navigate(['/tarifas']);
  }
}
