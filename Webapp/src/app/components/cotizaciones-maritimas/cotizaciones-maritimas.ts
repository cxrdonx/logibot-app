import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CotizacionesService, Cotizacion } from '../../services/cotizaciones.service';
import { HeaderComponent } from '../header/header';

interface LineItem {
  description: string;
  quantity: number;
  unit: string;
  currency: string;
  unit_price: number;
  amount: number;
  amount_note?: string;
}

interface FormModel {
  // Cliente
  cliente: string;
  contacto: string;
  incoterm: string;
  shipper: string;
  consignee: string;
  descripcion_producto: string;
  valor_fob: string;
  // Ruta
  pol: string;
  pod: string;
  via_port: string;
  tipo_contenedor: string;
  naviera: string;
  kilos_gross: string;
  piezas: string;
  dim: string;
  volumen: string;
  peso_volumen: string;
  transit_time: number | null;
  dias_libres_display: string;
  // Costos
  line_items: LineItem[];
  currency: string;
  // Vendedor
  vendedor_nombre: string;
  vendedor_contacto: string;
  notas_adicionales: string;
}

@Component({
  selector: 'app-cotizaciones-maritimas',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './cotizaciones-maritimas.html',
  styleUrl: './cotizaciones-maritimas.css',
})
export class CotizacionesMaritimasComponent implements OnInit {
  cotizaciones: Cotizacion[] = [];
  filtered: Cotizacion[] = [];
  selected: Cotizacion | null = null;
  searchTerm = '';

  get selectedId(): string | null {
    return this.selected?.id ?? null;
  }
  loading = false;
  saving = false;
  saveSuccess: string | null = null;
  saveError: string | null = null;

  get totalItems(): number {
    return this.filtered.length;
  }

  form: FormModel = this.emptyForm();

  constructor(
    private cotizacionesService: CotizacionesService,
    private cdr: ChangeDetectorRef,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.cotizacionesService.getMaritimas().subscribe({
      next: (items) => {
        this.cotizaciones = items;
        this.applyFilter();
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  applyFilter(): void {
    const q = this.searchTerm.toLowerCase();
    this.filtered = q
      ? this.cotizaciones.filter(
          (c) =>
            c.numero_cotizacion.toLowerCase().includes(q) ||
            this.getCliente(c).toLowerCase().includes(q),
        )
      : [...this.cotizaciones];
  }

  selectCotizacion(cot: Cotizacion): void {
    this.selected = cot;
    this.saveSuccess = null;
    this.saveError = null;
    this.form = this.buildForm(cot);
  }

  getCliente(cot: Cotizacion): string {
    return cot.datos?.company?.name || cot.datos?.requested_by || 'Sin cliente';
  }

  formatDate(iso: string): string {
    return iso ? new Date(iso).toLocaleDateString('es-GT') : '';
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  buildForm(cot: Cotizacion): FormModel {
    const d = cot.datos || {};
    const c0 = d.commodities?.[0] || {};
    return {
      cliente: d.company?.name || d.requested_by || '',
      contacto: d.company?.contact || '',
      incoterm: d.shipment_term || 'FOB',
      shipper: d.shipper || 'N/A',
      consignee: d.consignee || 'N/A',
      descripcion_producto: c0.description || '',
      valor_fob: d.valor_fob || 'PENDIENTE',
      pol: d.routing?.origin_port || '',
      pod: d.routing?.destination_port || '',
      via_port: d.routing?.via_port || '',
      tipo_contenedor: c0.container_type || '',
      naviera: d.logistics?.shipping_line || '',
      kilos_gross: c0.gross_weight?.toString() || 'N/A',
      piezas: d.piezas || 'N/A',
      dim: d.dim || 'N/A',
      volumen: c0.volume_cbm?.toString() || 'N/A',
      peso_volumen: d.peso_volumen || 'N/A',
      transit_time: d.logistics?.transit_time_days ?? null,
      dias_libres_display: d.dias_libres_display || 'N/A',
      line_items: (d.line_items || []).map((li: LineItem) => ({ ...li })),
      currency: d.currency || 'USD',
      vendedor_nombre: d.vendedor_nombre || 'MILDRED PALACIOS',
      vendedor_contacto:
        d.vendedor_contacto ||
        'Edificio Geminis 10 Torre Norte Oficina 1206 Nivel 12, 12 calle 1-25 zona 10 Guatemala\n' +
          'www.grupo-alonso.com  Tel. 23353290, Cel: 502 39910747',
      notas_adicionales: d.notas_adicionales || '',
    };
  }

  emptyForm(): FormModel {
    return {
      cliente: '',
      contacto: '',
      incoterm: 'FOB',
      shipper: 'N/A',
      consignee: 'N/A',
      descripcion_producto: '',
      valor_fob: 'PENDIENTE',
      pol: '',
      pod: '',
      via_port: '',
      tipo_contenedor: '',
      naviera: '',
      kilos_gross: 'N/A',
      piezas: 'N/A',
      dim: 'N/A',
      volumen: 'N/A',
      peso_volumen: 'N/A',
      transit_time: null,
      dias_libres_display: 'N/A',
      line_items: [],
      currency: 'USD',
      vendedor_nombre: 'MILDRED PALACIOS',
      vendedor_contacto:
        'Edificio Geminis 10 Torre Norte Oficina 1206 Nivel 12, 12 calle 1-25 zona 10 Guatemala\n' +
        'www.grupo-alonso.com  Tel. 23353290, Cel: 502 39910747',
      notas_adicionales: '',
    };
  }

  addLineItem(): void {
    this.form.line_items.push({
      description: '',
      quantity: 1,
      unit: 'P/CONT',
      currency: this.form.currency,
      unit_price: 0,
      amount: 0,
    });
  }

  removeLineItem(i: number): void {
    this.form.line_items.splice(i, 1);
  }

  recalcItem(i: number): void {
    const li = this.form.line_items[i];
    li.amount = (li.quantity || 0) * (li.unit_price || 0);
  }

  calcTotal(): number {
    return this.form.line_items.reduce((s, li) => s + (li.amount || 0), 0);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  buildDatos(): any {
    if (!this.selected) return {};
    const d = JSON.parse(JSON.stringify(this.selected.datos || {}));
    if (!d.company) d.company = {};
    d.company.name = this.form.cliente;
    d.company.contact = this.form.contacto;
    d.shipment_term = this.form.incoterm;
    d.shipper = this.form.shipper;
    d.consignee = this.form.consignee;
    d.valor_fob = this.form.valor_fob;
    if (!d.routing) d.routing = {};
    d.routing.origin_port = this.form.pol;
    d.routing.destination_port = this.form.pod;
    d.routing.via_port = this.form.via_port || null;
    if (!d.logistics) d.logistics = {};
    d.logistics.shipping_line = this.form.naviera;
    d.logistics.transit_time_days = this.form.transit_time;
    if (!d.commodities || !d.commodities[0]) d.commodities = [{}];
    d.commodities[0].description = this.form.descripcion_producto;
    d.commodities[0].container_type = this.form.tipo_contenedor;
    d.commodities[0].gross_weight = isNaN(Number(this.form.kilos_gross))
      ? null
      : Number(this.form.kilos_gross);
    d.commodities[0].volume_cbm = isNaN(Number(this.form.volumen))
      ? null
      : Number(this.form.volumen);
    d.piezas = this.form.piezas;
    d.dim = this.form.dim;
    d.peso_volumen = this.form.peso_volumen;
    d.dias_libres_display = this.form.dias_libres_display;
    d.line_items = this.form.line_items;
    d.total_amount = this.calcTotal();
    d.currency = this.form.currency;
    d.vendedor_nombre = this.form.vendedor_nombre;
    d.vendedor_contacto = this.form.vendedor_contacto;
    d.notas_adicionales = this.form.notas_adicionales;
    return d;
  }

  saveChanges(): void {
    if (!this.selected) return;
    this.saving = true;
    this.saveError = null;
    this.saveSuccess = null;
    const datos = this.buildDatos();
    this.cotizacionesService.update(this.selected.id, { datos }).subscribe({
      next: () => {
        this.saving = false;
        this.saveSuccess = 'Cotización actualizada correctamente';
        this.selected!.datos = datos;
        setTimeout(() => {
          this.saveSuccess = null;
          this.cdr.detectChanges();
        }, 4000);
        this.cdr.detectChanges();
      },
      error: () => {
        this.saving = false;
        this.saveError = 'Error al actualizar. Intenta de nuevo.';
        this.cdr.detectChanges();
      },
    });
  }

  async generateOrdenEmbarque(cot: Cotizacion): Promise<void> {
    const tempCot: Cotizacion = { ...cot, datos: this.buildDatos() };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { jsPDF } = await import('jspdf');
    const autoTable = (await import('jspdf-autotable')).default;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const doc = new (jsPDF as any)({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const d = tempCot.datos;
    const pageW = 210;
    const margin = 15;
    const contentW = pageW - margin * 2;

    const loadImg = (url: string): Promise<string> =>
      new Promise((resolve, reject) => {
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

    // Load logo once for reuse in header and footer
    let logoData: string | null = null;
    try {
      logoData = await loadImg('/alonso.jpeg');
    } catch {
      /* skip if logo unavailable */
    }

    // Header — logo
    if (logoData) {
      doc.addImage(logoData, 'JPEG', margin, 6, 70, 20);
    }

    // doc.setFontSize(7.5);
    // doc.setTextColor(80, 80, 80);
    // doc.text('FORWARDING GUATEMALA', margin + 47, 14);
    // doc.text('NIT: 118777033', margin, 30);

    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text(`COTIZACIÓN #  ${tempCot.numero_cotizacion}`, pageW - margin, 13, { align: 'right' });

    doc.setFontSize(8.5);
    doc.setFont('helvetica', 'normal');
    const fechaStr = new Date(tempCot.fecha_creacion).toLocaleDateString('es-GT');
    doc.text(fechaStr, pageW - margin - 25, 30);
    doc.text('Validez', pageW - margin, 30, { align: 'right' });

    doc.setDrawColor(200, 200, 200);
    doc.line(margin, 33, pageW - margin, 33);

    // Client + Route columns
    const colMid = margin + contentW * 0.48;
    let yL = 38;

    const labels: [string, string][] = [
      ['Cliente:', d.company?.name || d.requested_by || 'N/A'],
      ['Contacto:', d.company?.contact || 'N/A'],
      ['Incoterm:', d.shipment_term || 'N/A'],
      ['Tipo de Servicio:', 'Marítimo'],
      ['Origen:', d.routing?.origin_port || 'N/A'],
      ['Shipper:', d.shipper || 'N/A'],
      ['Consignee:', d.consignee || 'N/A'],
    ];
    labels.forEach(([label, val]) => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text(label, margin, yL);
      doc.setFont('helvetica', 'normal');
      doc.text(val, margin + 30, yL);
      yL += 5.5;
    });
    doc.setFont('helvetica', 'bold');
    doc.text('Descripción del producto:', margin, yL);
    doc.setFont('helvetica', 'normal');
    doc.text(d.commodities?.[0]?.description || 'N/A', margin + 43, yL);
    yL += 5.5;
    doc.setFont('helvetica', 'bold');
    doc.text('Valor FOB:', margin, yL);
    doc.setFont('helvetica', 'normal');
    doc.text(d.valor_fob || 'PENDIENTE', margin + 22, yL);
    yL += 5.5;

    // POL / POD boxes
    let yR = 38;
    const boxW = contentW * 0.52;
    doc.setFillColor(220, 232, 255);
    doc.rect(colMid, yR - 3, boxW, 14, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.setTextColor(20, 40, 160);
    doc.text('POL', colMid + 3, yR + 1);
    doc.text('POD', pageW - margin - 3, yR + 1, { align: 'right' });
    doc.setTextColor(0, 0, 0);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    const polLines = doc.splitTextToSize(d.routing?.origin_port || 'N/A', 35);
    doc.text(polLines, colMid + 3, yR + 6);
    const podLines = doc.splitTextToSize(d.routing?.destination_port || 'N/A', 35);
    doc.text(podLines, pageW - margin - 3, yR + 6, { align: 'right' });
    yR += 16;

    const tipoCont: string = d.commodities?.[0]?.container_type || 'N/A';
    const rightLabels: [string, string][] = [
      ['Type:', tipoCont],
      ['Naviera:', d.logistics?.shipping_line || 'N/A'],
      [
        'Kilos Gross:',
        d.commodities?.[0]?.gross_weight ? `${d.commodities[0].gross_weight} KG` : 'N/A',
      ],
      ['Piezas:', d.piezas || 'N/A'],
      ['Dim:', d.dim || 'N/A'],
      [
        'Volumen:',
        d.commodities?.[0]?.volume_cbm ? `${d.commodities[0].volume_cbm} CBM` : 'N/A',
      ],
      ['Peso Volumen:', d.peso_volumen || 'N/A'],
      [
        'T/T:',
        d.logistics?.transit_time_days ? `${d.logistics.transit_time_days} días` : 'N/A',
      ],
      ['Días libres:', d.dias_libres_display || 'N/A'],
    ];
    rightLabels.forEach(([label, val]) => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text(label, colMid + 3, yR);
      doc.setFont('helvetica', 'normal');
      doc.text(val, colMid + 30, yR);
      yR += 5.5;
    });

    // Section title bar
    let tableStartY = Math.max(yL, yR) + 5;
    doc.setFillColor(20, 40, 160);
    doc.rect(margin, tableStartY, contentW, 7, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.setTextColor(255, 255, 255);
    doc.text('DETALLES DE LA COTIZACIÓN', pageW / 2, tableStartY + 5, { align: 'center' });
    doc.setTextColor(0, 0, 0);
    tableStartY += 8;

    // Line items table
    const currency: string = d.currency || 'USD';
    const colLabel = tipoCont !== 'N/A' ? `1x${tipoCont}` : '1xCONT';
    const lineItems: LineItem[] = d.line_items || [];
    const totalAmount: number =
      d.total_amount ??
      lineItems.reduce((s: number, li: LineItem) => s + (li.amount || 0), 0);

    autoTable(doc, {
      startY: tableStartY,
      margin: { left: margin, right: margin },
      head: [['CONCEPTO', 'Cantidad', 'Base', colLabel, '']],
      body: [
        ...lineItems.map((li: LineItem) => [
          li.description || '',
          `${li.quantity || 1}`,
          li.unit || 'P/CONT',
          `${li.currency || currency}     ${(li.unit_price ?? 0).toFixed(2)}`,
          li.amount_note || '',
        ]),
        [
          { content: 'TOTAL', styles: { fontStyle: 'bold' } },
          '',
          '',
          {
            content: `${currency}     ${totalAmount.toFixed(2)}`,
            styles: { fontStyle: 'bold' },
          },
          '',
        ],
      ],
      headStyles: {
        fillColor: [240, 240, 240],
        textColor: [0, 0, 0],
        fontStyle: 'bold',
        fontSize: 8,
        halign: 'center',
      },
      bodyStyles: { fontSize: 8 },
      columnStyles: {
        0: { cellWidth: 60 },
        1: { cellWidth: 20, halign: 'center' },
        2: { cellWidth: 22, halign: 'center' },
        3: { cellWidth: 48, halign: 'right' },
        4: { cellWidth: 'auto' },
      },
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let finalY = (doc as any).lastAutoTable.finalY + 5;

    // Notes section
    const defaultNotas = [
      'Gastos de Origen se facturan al shipper, gastos en destino se facturan en destino.',
      'Solo incluyen gastos descritos en esta cotización.',
      'Tarifa válida para carga general no peligrosa.',
      'Tarifa válida para carga no sobredimensionada.',
      '* Las tarifas están sujetas a fecha de zarpe, por favor reconfirmar previo a embarcar.',
      '*En caso de que la mercadería no logre la salida programada podría existir un costo de almacenaje y demora.',
      '*Alonso Forwarding Guatemala está excluido de responsabilidad por incumplimiento en itinerarios.',
      '*Los días libres para embarques FTL inician desde la asignación de datos de piloto.',
      '* El servicio de tramité de aduanas, NO incluye permisos especiales.',
    ].join('\n');
    const notas: string = d.notas_adicionales || defaultNotas;

    doc.setFillColor(245, 245, 245);
    doc.rect(margin, finalY, contentW, 6, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.text('NOTAS:', margin + 2, finalY + 4);
    finalY += 7;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    const notasLines = doc.splitTextToSize(notas, contentW - 4);
    doc.text(notasLines, margin + 2, finalY);
    finalY += notasLines.length * 3.8 + 6;

    // Footer
    const footerY = Math.min(finalY + 4, 262);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text(d.vendedor_nombre || 'MILDRED PALACIOS', margin, footerY);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    const contactText: string =
      d.vendedor_contacto ||
      'Edificio Geminis 10 Torre Norte Oficina 1206 Nivel 12, 12 calle 1-25 zona 10 Guatemala\n' +
        'www.grupo-alonso.com  Tel. 23353290, Cel: 502 39910747';
    contactText.split('\n').forEach((line: string, i: number) => {
      doc.text(line, margin, footerY + 5 + i * 4);
    });

    if (logoData) {
      doc.addImage(logoData, 'JPEG', pageW - margin - 58, footerY - 2, 55, 18);
    }

    doc.save(`orden-embarque-${tempCot.numero_cotizacion}.pdf`);
  }

  goBack(): void {
    this.router.navigate(['/tarifas']);
  }
}
