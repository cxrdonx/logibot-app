import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CotizacionesService, Cotizacion } from '../../services/cotizaciones.service';
import { HeaderComponent } from '../header/header';

@Component({
  selector: 'app-orden-compra',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './orden-compra.html',
  styleUrl: './orden-compra.css',
})
export class OrdenCompraComponent implements OnInit {
  // ── Data ────────────────────────────────────────────────────────────────────
  maritimas: Cotizacion[] = [];
  terrestres: Cotizacion[] = [];

  // ── Selection ────────────────────────────────────────────────────────────────
  selectedMaritimas: Set<string> = new Set();
  selectedTerrestres: Set<string> = new Set();

  // ── Loading / error ──────────────────────────────────────────────────────────
  loadingMaritimas = false;
  loadingTerrestres = false;
  errorMaritimas: string | null = null;
  errorTerrestres: string | null = null;

  // ── PO state ─────────────────────────────────────────────────────────────────
  poNumber: string = '';
  fechaPO: string = '';
  generatingPDF = false;

  // ── Editable PO fields ────────────────────────────────────────────────────────
  notas_po = '';
  autorizado_por = '';
  departamento = '';

  constructor(
    private cotizacionesService: CotizacionesService,
    private cdr: ChangeDetectorRef,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.poNumber = this.generatePoNumber();
    this.fechaPO = new Date().toLocaleDateString('es-GT');
    this.loadMaritimas();
    this.loadTerrestres();
  }

  // ── Loaders ──────────────────────────────────────────────────────────────────

  loadMaritimas(): void {
    this.loadingMaritimas = true;
    this.errorMaritimas = null;
    this.cotizacionesService.getMaritimas().subscribe({
      next: (items) => {
        this.maritimas = items;
        this.loadingMaritimas = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loadingMaritimas = false;
        this.errorMaritimas = 'Error al cargar cotizaciones marítimas.';
        this.cdr.detectChanges();
      },
    });
  }

  loadTerrestres(): void {
    this.loadingTerrestres = true;
    this.errorTerrestres = null;
    this.cotizacionesService.getTerrestres().subscribe({
      next: (items) => {
        this.terrestres = items;
        this.loadingTerrestres = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loadingTerrestres = false;
        this.errorTerrestres = 'Error al cargar cotizaciones terrestres.';
        this.cdr.detectChanges();
      },
    });
  }

  // ── Selection helpers ─────────────────────────────────────────────────────────

  toggleMaritima(id: string): void {
    if (this.selectedMaritimas.has(id)) {
      this.selectedMaritimas.delete(id);
    } else {
      this.selectedMaritimas.add(id);
    }
  }

  toggleTerrestre(id: string): void {
    if (this.selectedTerrestres.has(id)) {
      this.selectedTerrestres.delete(id);
    } else {
      this.selectedTerrestres.add(id);
    }
  }

  get selectedMaritimasList(): Cotizacion[] {
    return this.maritimas.filter((c) => this.selectedMaritimas.has(c.id));
  }

  get selectedTerrestresList(): Cotizacion[] {
    return this.terrestres.filter((c) => this.selectedTerrestres.has(c.id));
  }

  get hasSelection(): boolean {
    return this.selectedMaritimas.size > 0 || this.selectedTerrestres.size > 0;
  }

  // ── Display helpers ───────────────────────────────────────────────────────────

  getClienteMaritimo(cot: Cotizacion): string {
    return cot.datos?.company?.name || cot.datos?.requested_by || 'Sin cliente';
  }

  getClienteTerrestre(cot: Cotizacion): string {
    return cot.datos?.cliente || cot.datos?.proveedor || 'Sin cliente';
  }

  formatDate(iso: string): string {
    return iso ? new Date(iso).toLocaleDateString('es-GT') : '';
  }

  toNum(val: number | string | null | undefined): number {
    return Number(val) || 0;
  }

  // ── Totals ────────────────────────────────────────────────────────────────────

  calcTotalMaritimo(cot: Cotizacion): number {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const li = cot.datos?.line_items || [];
    return cot.datos?.total_amount ?? li.reduce((s: number, i: any) => s + (i.amount || 0), 0);
  }

  calcTotalTerrestre(cot: Cotizacion): number {
    return cot.datos?.resumen_costos?.total ?? 0;
  }

  get totalMaritimas(): number {
    return this.selectedMaritimasList.reduce((s, c) => s + this.calcTotalMaritimo(c), 0);
  }

  get totalTerrestres(): number {
    return this.selectedTerrestresList.reduce((s, c) => s + this.calcTotalTerrestre(c), 0);
  }

  get grandTotal(): number {
    return this.totalMaritimas + this.totalTerrestres;
  }

  // ── Private helpers ───────────────────────────────────────────────────────────

  private generatePoNumber(): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = 'PO-';
    for (let i = 0; i < 8; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  private loadImg(url: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        canvas.getContext('2d')!.drawImage(img, 0, 0);
        resolve(canvas.toDataURL('image/jpeg'));
      };
      img.onerror = reject;
      img.src = url;
    });
  }

  // ── PDF generation ────────────────────────────────────────────────────────────

  async generatePDF(): Promise<void> {
    if (!this.hasSelection) return;
    this.generatingPDF = true;
    this.cdr.detectChanges();

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { jsPDF } = await import('jspdf');
      const autoTable = (await import('jspdf-autotable')).default;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const doc = new (jsPDF as any)({ orientation: 'portrait', unit: 'mm', format: 'a4' });

      const pageW = 210;
      const margin = 15;
      const contentW = pageW - margin * 2;

      // Load logo once
      let logoData: string | null = null;
      try {
        logoData = await this.loadImg('/alonso.jpeg');
      } catch {
        /* skip if logo unavailable */
      }

      // ── HEADER ──────────────────────────────────────────────────────────────
      if (logoData) {
        doc.addImage(logoData, 'JPEG', margin, 6, 70, 20);
      }

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(16);
      doc.setTextColor(5, 13, 158);
      doc.text('PURCHASE ORDER', pageW / 2, 14, { align: 'center' });

      doc.setFontSize(10);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(0, 0, 0);
      doc.text(this.poNumber, pageW - margin, 13, { align: 'right' });

      doc.setFontSize(8.5);
      doc.setFont('helvetica', 'normal');
      doc.text(this.fechaPO, pageW - margin, 20, { align: 'right' });

      // Separator line
      doc.setDrawColor(200, 200, 200);
      doc.line(margin, 31, pageW - margin, 31);

      // ── GENERAL INFO ────────────────────────────────────────────────────────
      let y = 38;
      const colMid = margin + contentW * 0.5;

      const leftInfo: [string, string][] = [
        ['Autorizado por:', this.autorizado_por || '—'],
        ['Departamento:', this.departamento || '—'],
        ['Fecha:', this.fechaPO],
      ];
      const rightInfo: [string, string][] = [
        ['Total Marítimo:', `USD ${this.totalMaritimas.toFixed(2)}`],
        ['Total Terrestre:', `GTQ ${this.totalTerrestres.toFixed(2)}`],
        ['TOTAL GENERAL:', `${this.grandTotal.toFixed(2)}`],
      ];

      leftInfo.forEach(([label, val]) => {
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(8);
        doc.text(label, margin, y);
        doc.setFont('helvetica', 'normal');
        doc.text(val, margin + 32, y);
        y += 5.5;
      });

      let yR = 38;
      rightInfo.forEach(([label, val], idx) => {
        doc.setFont('helvetica', idx === 2 ? 'bold' : 'bold');
        doc.setFontSize(8);
        doc.text(label, colMid, yR);
        doc.setFont('helvetica', idx === 2 ? 'bold' : 'normal');
        doc.setTextColor(idx === 2 ? 5 : 0, idx === 2 ? 13 : 0, idx === 2 ? 158 : 0);
        doc.text(val, pageW - margin, yR, { align: 'right' });
        doc.setTextColor(0, 0, 0);
        yR += 5.5;
      });

      y = Math.max(y, yR) + 6;

      // ── COTIZACIONES MARÍTIMAS ───────────────────────────────────────────────
      if (this.selectedMaritimasList.length > 0) {
        doc.setFillColor(5, 13, 158);
        doc.rect(margin, y, contentW, 8, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(9);
        doc.setTextColor(255, 255, 255);
        doc.text('COTIZACIONES MARÍTIMAS', pageW / 2, y + 5.5, { align: 'center' });
        doc.setTextColor(0, 0, 0);
        y += 10;

        for (const cot of this.selectedMaritimasList) {
          const d = cot.datos || {};
          const pol = d.routing?.origin_port || 'N/A';
          const pod = d.routing?.destination_port || 'N/A';
          const cliente = this.getClienteMaritimo(cot);
          const currency: string = d.currency || 'USD';
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const lineItems: any[] = d.line_items || [];
          const total = this.calcTotalMaritimo(cot);

          // Sub-header
          doc.setFillColor(220, 232, 255);
          doc.rect(margin, y, contentW, 7, 'F');
          doc.setFont('helvetica', 'bold');
          doc.setFontSize(8);
          doc.setTextColor(20, 40, 160);
          const subHeader = `#${cot.numero_cotizacion}  |  ${cliente}  |  ${pol} → ${pod}`;
          doc.text(subHeader, margin + 3, y + 5);
          doc.setTextColor(0, 0, 0);
          y += 9;

          // Info row: naviera, tipo contenedor, transit time
          const naviera: string = d.logistics?.shipping_line || '';
          const tipoCont: string = d.commodities?.[0]?.container_type || '';
          const tt: number | null = d.logistics?.transit_time_days ?? null;
          const infoLine = [
            naviera ? `Naviera: ${naviera}` : '',
            tipoCont ? `Contenedor: ${tipoCont}` : '',
            tt !== null ? `T/T: ${tt} días` : '',
          ]
            .filter(Boolean)
            .join('   |   ');
          if (infoLine) {
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.5);
            doc.setTextColor(80, 80, 80);
            doc.text(infoLine, margin + 3, y);
            doc.setTextColor(0, 0, 0);
            y += 5;
          }

          // Line items table
          autoTable(doc, {
            startY: y,
            margin: { left: margin, right: margin },
            head: [['CONCEPTO', 'Cantidad', 'Base', 'Precio', 'Notas']],
            body: [
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              ...lineItems.map((li: any) => [
                li.description || '',
                `${li.quantity ?? 1}`,
                li.unit || 'P/CONT',
                `${li.currency || currency}  ${(li.unit_price ?? 0).toFixed(2)}`,
                li.amount_note || '',
              ]),
              [
                { content: 'TOTAL', styles: { fontStyle: 'bold' } },
                '',
                '',
                {
                  content: `${currency}  ${total.toFixed(2)}`,
                  styles: { fontStyle: 'bold', fillColor: [230, 235, 255] },
                },
                { content: '', styles: { fillColor: [230, 235, 255] } },
              ],
            ],
            headStyles: {
              fillColor: [240, 240, 240],
              textColor: [0, 0, 0],
              fontStyle: 'bold',
              fontSize: 7.5,
              halign: 'center',
            },
            bodyStyles: { fontSize: 7.5 },
            columnStyles: {
              0: { cellWidth: 65 },
              1: { cellWidth: 18, halign: 'center' },
              2: { cellWidth: 22, halign: 'center' },
              3: { cellWidth: 48, halign: 'right' },
              4: { cellWidth: 'auto' },
            },
          });

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          y = (doc as any).lastAutoTable.finalY + 5;
        }
      }

      // ── COTIZACIONES TERRESTRES ──────────────────────────────────────────────
      if (this.selectedTerrestresList.length > 0) {
        doc.setFillColor(5, 13, 158);
        doc.rect(margin, y, contentW, 8, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(9);
        doc.setTextColor(255, 255, 255);
        doc.text('COTIZACIONES TERRESTRES', pageW / 2, y + 5.5, { align: 'center' });
        doc.setTextColor(0, 0, 0);
        y += 10;

        for (const cot of this.selectedTerrestresList) {
          const d = cot.datos || {};
          const origen: string = d.ruta?.origen || 'N/A';
          const destino: string = d.ruta?.destino || 'N/A';
          const cliente = this.getClienteTerrestre(cot);
          const moneda: string = d.tarifa_base?.moneda || d.resumen_costos?.moneda || 'GTQ';

          // Sub-header
          doc.setFillColor(220, 240, 220);
          doc.rect(margin, y, contentW, 7, 'F');
          doc.setFont('helvetica', 'bold');
          doc.setFontSize(8);
          doc.setTextColor(20, 100, 30);
          const subHeader = `#${cot.numero_cotizacion}  |  ${cliente}  |  ${origen} → ${destino}`;
          doc.text(subHeader, margin + 3, y + 5);
          doc.setTextColor(0, 0, 0);
          y += 9;

          // Info row: proveedor, tipo unidad, peso
          const proveedor: string = d.proveedor || '';
          const tipoUnidad: string = d.unidad?.tipo || '';
          const peso: number = d.unidad?.peso_solicitado || 0;
          const pesoUnidad: string = d.unidad?.peso_unidad || 'kg';
          const infoLine = [
            proveedor ? `Proveedor: ${proveedor}` : '',
            tipoUnidad ? `Unidad: ${tipoUnidad}` : '',
            peso ? `Peso: ${peso} ${pesoUnidad}` : '',
          ]
            .filter(Boolean)
            .join('   |   ');
          if (infoLine) {
            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.5);
            doc.setTextColor(80, 80, 80);
            doc.text(infoLine, margin + 3, y);
            doc.setTextColor(0, 0, 0);
            y += 5;
          }

          // Cost rows
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rows: any[][] = [];
          rows.push([
            d.tarifa_base?.rango || 'Tarifa Base',
            (d.tarifa_base?.monto || 0).toFixed(2),
            moneda,
            '',
          ]);
          if (d.sobrepeso?.aplica) {
            rows.push([
              'Sobrepeso',
              (d.sobrepeso.monto || 0).toFixed(2),
              moneda,
              d.sobrepeso.descripcion || '',
            ]);
          }
          if (d.custodio) {
            rows.push([
              `Custodio (${d.custodio.tipo || ''})`,
              (d.custodio.costo_total || 0).toFixed(2),
              moneda,
              `${d.custodio.cantidad_unidades} × ${d.custodio.costo_unitario} ${moneda}`,
            ]);
          }
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (d.costos_adicionales || []).forEach((c: any) => {
            rows.push([
              c.concepto || '',
              Number(c.valor || 0).toFixed(2),
              c.unidad || moneda,
              c.descripcion || '',
            ]);
          });

          const subtotal: number = d.resumen_costos?.subtotal ?? 0;
          const total: number = d.resumen_costos?.total ?? 0;

          autoTable(doc, {
            startY: y,
            margin: { left: margin, right: margin },
            head: [['CONCEPTO', 'MONTO', 'MONEDA', 'DESCRIPCIÓN']],
            body: [
              ...rows,
              [
                { content: 'SUBTOTAL', styles: { fontStyle: 'bold' } },
                { content: subtotal.toFixed(2), styles: { fontStyle: 'bold' } },
                moneda,
                '',
              ],
              [
                {
                  content: 'TOTAL',
                  styles: { fontStyle: 'bold', fillColor: [220, 240, 220] },
                },
                {
                  content: total.toFixed(2),
                  styles: { fontStyle: 'bold', fillColor: [220, 240, 220] },
                },
                { content: moneda, styles: { fillColor: [220, 240, 220] } },
                { content: '', styles: { fillColor: [220, 240, 220] } },
              ],
            ],
            headStyles: {
              fillColor: [240, 240, 240],
              textColor: [0, 0, 0],
              fontStyle: 'bold',
              fontSize: 7.5,
            },
            bodyStyles: { fontSize: 7.5 },
            columnStyles: {
              0: { cellWidth: 65 },
              1: { cellWidth: 28, halign: 'right' },
              2: { cellWidth: 22, halign: 'center' },
              3: { cellWidth: 'auto' },
            },
          });

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          y = (doc as any).lastAutoTable.finalY + 5;
        }
      }

      // ── RESUMEN FINAL ────────────────────────────────────────────────────────
      doc.setFillColor(5, 13, 158);
      doc.rect(margin, y, contentW, 8, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.setTextColor(255, 255, 255);
      doc.text('RESUMEN TOTAL', pageW / 2, y + 5.5, { align: 'center' });
      doc.setTextColor(0, 0, 0);
      y += 10;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const summaryRows: any[][] = [];
      this.selectedMaritimasList.forEach((cot) => {
        summaryRows.push([
          cot.numero_cotizacion,
          'Marítimo',
          `USD  ${this.calcTotalMaritimo(cot).toFixed(2)}`,
        ]);
      });
      this.selectedTerrestresList.forEach((cot) => {
        summaryRows.push([
          cot.numero_cotizacion,
          'Terrestre',
          `GTQ  ${this.calcTotalTerrestre(cot).toFixed(2)}`,
        ]);
      });
      summaryRows.push([
        { content: 'TOTAL GENERAL', styles: { fontStyle: 'bold', fillColor: [230, 235, 255] } },
        { content: '', styles: { fillColor: [230, 235, 255] } },
        {
          content: this.grandTotal.toFixed(2),
          styles: { fontStyle: 'bold', fillColor: [230, 235, 255] },
        },
      ]);

      autoTable(doc, {
        startY: y,
        margin: { left: margin, right: margin },
        head: [['COTIZACIÓN', 'TIPO', 'TOTAL']],
        body: summaryRows,
        headStyles: {
          fillColor: [240, 240, 240],
          textColor: [0, 0, 0],
          fontStyle: 'bold',
          fontSize: 8,
        },
        bodyStyles: { fontSize: 8 },
        columnStyles: {
          0: { cellWidth: 60 },
          1: { cellWidth: 40 },
          2: { cellWidth: 'auto', halign: 'right' },
        },
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      y = (doc as any).lastAutoTable.finalY + 6;

      // ── NOTES ────────────────────────────────────────────────────────────────
      if (this.notas_po) {
        doc.setFillColor(245, 245, 245);
        doc.rect(margin, y, contentW, 6, 'F');
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(8.5);
        doc.text('NOTAS:', margin + 2, y + 4);
        y += 7;

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(7.5);
        const notasLines = doc.splitTextToSize(this.notas_po, contentW - 4);
        doc.text(notasLines, margin + 2, y);
        y += notasLines.length * 3.8 + 6;
      }

      // ── FOOTER ───────────────────────────────────────────────────────────────
      const footerY = Math.min(y + 4, 265);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9);
      doc.text(this.autorizado_por || 'Autorizado por', margin, footerY);
      if (this.departamento) {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(7.5);
        doc.text(this.departamento, margin, footerY + 5);
      }

      if (logoData) {
        doc.addImage(logoData, 'JPEG', pageW - margin - 58, footerY - 2, 55, 18);
      }

      doc.save(`${this.poNumber}.pdf`);
    } finally {
      this.generatingPDF = false;
      this.cdr.detectChanges();
    }
  }

  // ── Navigation ────────────────────────────────────────────────────────────────

  goBack(): void {
    this.router.navigate(['/tarifas']);
  }
}
