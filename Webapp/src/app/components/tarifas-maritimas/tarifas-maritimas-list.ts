import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MaritimeQuotationsService } from '../../services/maritime-quotations.service';
import { MaritimeQuotation } from '../../models/types';
import { HeaderComponent } from '../header/header';

@Component({
  selector: 'app-tarifas-maritimas-list',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './tarifas-maritimas-list.html',
  styleUrls: ['./tarifas-maritimas-list.css']
})
export class TarifasMaritimasListComponent implements OnInit {
  quotations: MaritimeQuotation[] = [];
  filteredQuotations: MaritimeQuotation[] = [];
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;
  filterText = '';

  constructor(
    private maritimeService: MaritimeQuotationsService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadQuotations();
  }

  loadQuotations(): void {
    this.loading = true;
    this.error = null;

    this.maritimeService.getAll().subscribe({
      next: (data) => {
        this.quotations = data;
        this.applyFilter();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al cargar cotizaciones: ' + (err.message ?? 'Error desconocido');
        this.loading = false;
      }
    });
  }

  applyFilter(): void {
    const term = this.filterText.trim().toLowerCase();
    if (!term) {
      this.filteredQuotations = [...this.quotations];
      return;
    }
    this.filteredQuotations = this.quotations.filter(
      (q) =>
        q.quotation_number.toLowerCase().includes(term) ||
        q.routing.origin_port.toLowerCase().includes(term) ||
        q.routing.destination_port.toLowerCase().includes(term)
    );
  }

  clearFilter(): void {
    this.filterText = '';
    this.applyFilter();
  }

  createQuotation(): void {
    this.router.navigate(['/tarifas/maritimo/create']);
  }

  viewDetails(id: string | undefined): void {
    if (id) {
      this.router.navigate(['/tarifas/maritimo/view', id]);
    }
  }

  editQuotation(id: string | undefined): void {
    if (id) {
      this.router.navigate(['/tarifas/maritimo/edit', id]);
    }
  }

  deleteQuotation(id: string | undefined): void {
    if (!id) return;
    if (!confirm('¿Está seguro de que desea eliminar esta cotización?')) return;

    this.loading = true;
    this.maritimeService.delete(id).subscribe({
      next: () => {
        this.successMessage = 'Cotización eliminada exitosamente';
        this.loadQuotations();
        setTimeout(() => {
          this.successMessage = null;
        }, 3000);
      },
      error: (err) => {
        this.error = 'Error al eliminar la cotización: ' + (err.message ?? 'Error desconocido');
        this.loading = false;
      }
    });
  }
}
