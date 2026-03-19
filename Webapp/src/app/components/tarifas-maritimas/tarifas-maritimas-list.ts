import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
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
    private router: Router,
    private cdr: ChangeDetectorRef
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
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = 'Error al cargar tarifas: ' + (err.message ?? 'Error desconocido');
        this.loading = false;
        this.cdr.detectChanges();
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
        (q.routing?.origin_port ?? '').toLowerCase().includes(term) ||
        (q.routing?.destination_port ?? '').toLowerCase().includes(term) ||
        (q.logistics?.shipping_line ?? '').toLowerCase().includes(term)
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
    if (!confirm('¿Está seguro de que desea eliminar esta tarifa?')) return;

    this.loading = true;
    this.maritimeService.delete(id).subscribe({
      next: () => {
        this.successMessage = 'Tarifa eliminada exitosamente';
        this.loadQuotations();
        setTimeout(() => {
          this.successMessage = null;
          this.cdr.detectChanges();
        }, 3000);
      },
      error: (err) => {
        this.error = 'Error al eliminar la tarifa: ' + (err.message ?? 'Error desconocido');
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }
}
