import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TarifasService, Tarifa } from '../../services/tarifas.service';
import { AuthService } from '../../services/auth.service';
import { HeaderComponent } from '../header/header';

@Component({
  selector: 'app-tarifas-list',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './tarifas-list.html',
  styleUrls: ['./tarifas-list.css']
})
export class TarifasListComponent implements OnInit {
  tarifas: Tarifa[] = [];
  filteredTarifas: Tarifa[] = [];
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;

  // Filter criteria
  filterOrigen = '';
  filterDestino = '';
  filterProveedor = '';

  constructor(
    private tarifasService: TarifasService,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadTarifas();
  }

  onLogout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  onReset(): void {
    this.filterOrigen = '';
    this.filterDestino = '';
    this.filterProveedor = '';
    this.loadTarifas();
  }

  loadTarifas(): void {
    this.loading = true;
    this.error = null;

    const filters = {
      origen: this.filterOrigen || undefined,
      destino: this.filterDestino || undefined,
      proveedor: this.filterProveedor || undefined
    };

    this.tarifasService.getTarifas(filters).subscribe({
      next: (data) => {
        this.tarifas = data;
        this.filteredTarifas = [...this.tarifas];
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error loading tarifas: ' + err.message;
        this.loading = false;
      }
    });
  }

  applyFilters(): void {
    this.loadTarifas();
  }

  clearFilters(): void {
    this.filterOrigen = '';
    this.filterDestino = '';
    this.filterProveedor = '';
    this.loadTarifas();
  }

  editTarifa(id?: string): void {
    if (id) {
      this.router.navigate(['/tarifas/edit', id]);
    }
  }

  createTarifa(): void {
    this.router.navigate(['/tarifas/create']);
  }

  deleteTarifa(id?: string): void {
    if (!id) return;

    if (confirm('¿Está seguro de que desea eliminar esta tarifa?')) {
      this.loading = true;
      this.tarifasService.deleteTarifa(id).subscribe({
        next: () => {
          this.successMessage = 'Tarifa eliminada exitosamente';
          this.loadTarifas();
          setTimeout(() => {
            this.successMessage = null;
          }, 3000);
        },
        error: (err) => {
          this.error = 'Error al eliminar tarifa: ' + err.message;
          this.loading = false;
        }
      });
    }
  }

  viewDetails(id?: string): void {
    if (id) {
      this.router.navigate(['/tarifas/view', id]);
    }
  }
}
