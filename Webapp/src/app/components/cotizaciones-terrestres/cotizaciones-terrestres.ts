import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CotizacionesService, Cotizacion } from '../../services/cotizaciones.service';
import { HeaderComponent } from '../header/header';

interface CostoAdicional {
  concepto: string;
  valor: number | string;
  unidad: string;
  descripcion: string;
}

interface FormModel {
  // Sección 1 — Información del Envío
  proveedor: string;
  cliente: string;
  contacto: string;
  shipper: string;
  consignee: string;
  descripcion_producto: string;
  valor_declarado: string;
  // Sección 2 — Ruta y Unidad
  origen: string;
  destino: string;
  tipo_unidad: string;
  peso_solicitado: number;
  peso_unidad: string;
  dias_libres: number;
  estadia: number;
  fianza: number;
  // Sección 3 — Costos
  tarifa_base_monto: number;
  tarifa_base_moneda: string;
  tarifa_base_rango: string;
  sobrepeso_aplica: boolean;
  sobrepeso_monto: number;
  sobrepeso_descripcion: string;
  custodio_tipo: string;
  custodio_costo_unitario: number;
  custodio_cantidad: number;
  costos_adicionales: CostoAdicional[];
  condiciones_aduana: string;
  condiciones_cominter: string;
  resumen_nota: string;
  // Sección 4 — Vendedor
  vendedor_nombre: string;
  vendedor_contacto: string;
  notas_adicionales: string;
}

@Component({
  selector: 'app-cotizaciones-terrestres',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './cotizaciones-terrestres.html',
  styleUrl: './cotizaciones-terrestres.css',
})
export class CotizacionesTerrestresComponent implements OnInit {
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
    this.cotizacionesService.getTerrestres().subscribe({
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
    return cot.datos?.cliente || cot.datos?.proveedor || 'Sin cliente';
  }

  formatDate(iso: string): string {
    return iso ? new Date(iso).toLocaleDateString('es-GT') : '';
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  buildForm(cot: Cotizacion): FormModel {
    const d = cot.datos || {};
    return {
      proveedor: d.proveedor || '',
      cliente: d.cliente || '',
      contacto: d.contacto || '',
      shipper: d.shipper || 'N/A',
      consignee: d.consignee || 'N/A',
      descripcion_producto: d.descripcion_producto || '',
      valor_declarado: d.valor_declarado || 'N/A',
      origen: d.ruta?.origen || '',
      destino: d.ruta?.destino || '',
      tipo_unidad: d.unidad?.tipo || '',
      peso_solicitado: d.unidad?.peso_solicitado || 0,
      peso_unidad: d.unidad?.peso_unidad || 'kg',
      dias_libres: d.dias_libres ?? 0,
      estadia: d.estadia ?? 0,
      fianza: d.fianza ?? 0,
      tarifa_base_monto: d.tarifa_base?.monto || 0,
      tarifa_base_moneda: d.tarifa_base?.moneda || 'GTQ',
      tarifa_base_rango: d.tarifa_base?.rango || '',
      sobrepeso_aplica: d.sobrepeso?.aplica ?? false,
      sobrepeso_monto: d.sobrepeso?.monto || 0,
      sobrepeso_descripcion: d.sobrepeso?.descripcion || '',
      custodio_tipo: d.custodio?.tipo || '',
      custodio_costo_unitario: d.custodio?.costo_unitario || 0,
      custodio_cantidad: d.custodio?.cantidad_unidades || 0,
      costos_adicionales: (d.costos_adicionales || []).map((c: CostoAdicional) => ({ ...c })),
      condiciones_aduana: d.resumen_costos?.condiciones_aduana || '',
      condiciones_cominter: d.resumen_costos?.condiciones_cominter || '',
      resumen_nota: d.resumen_costos?.nota || '',
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
      proveedor: '',
      cliente: '',
      contacto: '',
      shipper: 'N/A',
      consignee: 'N/A',
      descripcion_producto: '',
      valor_declarado: 'N/A',
      origen: '',
      destino: '',
      tipo_unidad: '',
      peso_solicitado: 0,
      peso_unidad: 'kg',
      dias_libres: 0,
      estadia: 0,
      fianza: 0,
      tarifa_base_monto: 0,
      tarifa_base_moneda: 'GTQ',
      tarifa_base_rango: '',
      sobrepeso_aplica: false,
      sobrepeso_monto: 0,
      sobrepeso_descripcion: '',
      custodio_tipo: '',
      custodio_costo_unitario: 0,
      custodio_cantidad: 0,
      costos_adicionales: [],
      condiciones_aduana: '',
      condiciones_cominter: '',
      resumen_nota: '',
      vendedor_nombre: 'MILDRED PALACIOS',
      vendedor_contacto:
        'Edificio Geminis 10 Torre Norte Oficina 1206 Nivel 12, 12 calle 1-25 zona 10 Guatemala\n' +
        'www.grupo-alonso.com  Tel. 23353290, Cel: 502 39910747',
      notas_adicionales: '',
    };
  }

  addCostoAdicional(): void {
    this.form.costos_adicionales.push({
      concepto: '',
      valor: 0,
      unidad: this.form.tarifa_base_moneda,
      descripcion: '',
    });
  }

  removeCostoAdicional(i: number): void {
    this.form.costos_adicionales.splice(i, 1);
  }

  get custodioTotal(): number {
    return (this.form.custodio_costo_unitario || 0) * (this.form.custodio_cantidad || 0);
  }

  calcSubtotal(): number {
    let sub = this.form.tarifa_base_monto || 0;
    if (this.form.sobrepeso_aplica) sub += this.form.sobrepeso_monto || 0;
    if (this.form.custodio_tipo) sub += this.custodioTotal;
    return sub;
  }

  calcTotal(): number {
    return (
      this.calcSubtotal() +
      this.form.costos_adicionales.reduce((s, c) => s + (Number(c.valor) || 0), 0)
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  buildDatos(): any {
    const d = { ...(this.selected!.datos || {}) };
    d.proveedor = this.form.proveedor;
    d.cliente = this.form.cliente;
    d.contacto = this.form.contacto;
    d.shipper = this.form.shipper;
    d.consignee = this.form.consignee;
    d.descripcion_producto = this.form.descripcion_producto;
    d.valor_declarado = this.form.valor_declarado;
    d.ruta = { origen: this.form.origen, destino: this.form.destino };
    d.unidad = {
      tipo: this.form.tipo_unidad,
      peso_solicitado: this.form.peso_solicitado,
      peso_unidad: this.form.peso_unidad,
    };
    d.dias_libres = this.form.dias_libres;
    d.estadia = this.form.estadia;
    d.fianza = this.form.fianza;
    d.tarifa_base = {
      monto: this.form.tarifa_base_monto,
      moneda: this.form.tarifa_base_moneda,
      rango: this.form.tarifa_base_rango,
    };
    d.sobrepeso = {
      aplica: this.form.sobrepeso_aplica,
      monto: this.form.sobrepeso_monto,
      moneda: this.form.tarifa_base_moneda,
      descripcion: this.form.sobrepeso_descripcion,
    };
    if (this.form.custodio_tipo) {
      d.custodio = {
        tipo: this.form.custodio_tipo,
        costo_unitario: this.form.custodio_costo_unitario,
        cantidad_unidades: this.form.custodio_cantidad,
        costo_total: this.form.custodio_costo_unitario * this.form.custodio_cantidad,
        moneda: this.form.tarifa_base_moneda,
        descripcion: '',
      };
    }
    d.costos_adicionales = this.form.costos_adicionales;
    d.resumen_costos = {
      subtotal: this.calcSubtotal(),
      total: this.calcTotal(),
      moneda: this.form.tarifa_base_moneda,
      detalles: d.resumen_costos?.detalles || '',
      condiciones_aduana: this.form.condiciones_aduana,
      condiciones_cominter: this.form.condiciones_cominter,
      nota: this.form.resumen_nota,
    };
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
    const moneda: string = d.tarifa_base?.moneda || 'GTQ';

    const loadImg = (url: string): Promise<string> =>
      new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
          const c = document.createElement('canvas');
          c.width = img.naturalWidth;
          c.height = img.naturalHeight;
          c.getContext('2d')!.drawImage(img, 0, 0);
          resolve(c.toDataURL('image/jpeg'));
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



    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text(`COTIZACIÓN #  ${tempCot.numero_cotizacion}`, pageW - margin, 13, { align: 'right' });

    doc.setFontSize(8.5);
    doc.setFont('helvetica', 'normal');
    doc.text('NIT: 118777033', margin, 40);
    const fechaStr = new Date(tempCot.fecha_creacion).toLocaleDateString('es-GT');
    doc.text(fechaStr, pageW - margin - 25, 40);
    doc.text('Validez', pageW - margin, 40, { align: 'right' });

    doc.setDrawColor(200, 200, 200);
    doc.line(margin, 43, pageW - margin, 43);

    // Two-column info section
    const colMid = margin + contentW * 0.5;
    let yL = 48;
    let yR = 48;

    const leftRows: [string, string][] = [
      ['Cliente:', d.cliente || 'N/A'],
      ['Contacto:', d.contacto || 'N/A'],
      ['Proveedor:', d.proveedor || 'N/A'],
      ['Shipper:', d.shipper || 'N/A'],
      ['Consignee:', d.consignee || 'N/A'],
      ['Descripción:', d.descripcion_producto || 'N/A'],
      ['Valor Declarado:', d.valor_declarado || 'N/A'],
    ];

    const rightRows: [string, string][] = [
      ['Origen:', d.ruta?.origen || 'N/A'],
      ['Destino:', d.ruta?.destino || 'N/A'],
      ['Tipo de Unidad:', d.unidad?.tipo || 'N/A'],
      ['Peso:', `${d.unidad?.peso_solicitado || 0} ${d.unidad?.peso_unidad || 'kg'}`],
      ['Días Libres:', `${d.dias_libres ?? 'N/A'}`],
      ['Estadía:', `${d.estadia ?? 'N/A'} ${moneda}/día`],
      ['Fianza:', `${d.fianza ?? 'N/A'} ${moneda}`],
    ];

    leftRows.forEach(([label, val]) => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text(label, margin, yL);
      doc.setFont('helvetica', 'normal');
      doc.text(val, margin + 30, yL);
      yL += 5.5;
    });

    rightRows.forEach(([label, val]) => {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text(label, colMid, yR);
      doc.setFont('helvetica', 'normal');
      doc.text(val, colMid + 28, yR);
      yR += 5.5;
    });

    // Section title
    let tableY = Math.max(yL, yR) + 4;
    doc.setFillColor(20, 40, 160);
    doc.rect(margin, tableY, contentW, 7, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.setTextColor(255, 255, 255);
    doc.text('DETALLES DE LA COTIZACIÓN', pageW / 2, tableY + 5, { align: 'center' });
    doc.setTextColor(0, 0, 0);
    tableY += 8;

    // Cost rows
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const rows: any[][] = [];
    rows.push([d.tarifa_base?.rango || 'Tarifa Base', (d.tarifa_base?.monto || 0).toFixed(2), moneda, '']);
    if (d.sobrepeso?.aplica) {
      rows.push(['Sobrepeso', (d.sobrepeso.monto || 0).toFixed(2), moneda, d.sobrepeso.descripcion || '']);
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
      rows.push([c.concepto || '', Number(c.valor || 0).toFixed(2), c.unidad || moneda, c.descripcion || '']);
    });

    const subtotal: number = d.resumen_costos?.subtotal ?? 0;
    const total: number = d.resumen_costos?.total ?? 0;

    autoTable(doc, {
      startY: tableY,
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
          { content: 'TOTAL', styles: { fontStyle: 'bold', fillColor: [230, 235, 255] } },
          { content: total.toFixed(2), styles: { fontStyle: 'bold', fillColor: [230, 235, 255] } },
          { content: moneda, styles: { fillColor: [230, 235, 255] } },
          { content: '', styles: { fillColor: [230, 235, 255] } },
        ],
      ],
      headStyles: {
        fillColor: [240, 240, 240],
        textColor: [0, 0, 0],
        fontStyle: 'bold',
        fontSize: 8,
      },
      bodyStyles: { fontSize: 8 },
      columnStyles: {
        0: { cellWidth: 60 },
        1: { cellWidth: 28, halign: 'right' },
        2: { cellWidth: 22, halign: 'center' },
        3: { cellWidth: 'auto' },
      },
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let finalY = (doc as any).lastAutoTable.finalY + 5;

    // Conditions
    const condAduana: string = d.resumen_costos?.condiciones_aduana;
    const condCominter: string = d.resumen_costos?.condiciones_cominter;
    const nota: string = d.resumen_costos?.nota;

    if (condAduana) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text('Condiciones de Aduana:', margin, finalY);
      doc.setFont('helvetica', 'normal');
      const lines = doc.splitTextToSize(condAduana, contentW - 45);
      doc.text(lines, margin + 44, finalY);
      finalY += lines.length * 4 + 3;
    }
    if (condCominter) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text('Condiciones Cominter:', margin, finalY);
      doc.setFont('helvetica', 'normal');
      const lines = doc.splitTextToSize(condCominter, contentW - 42);
      doc.text(lines, margin + 42, finalY);
      finalY += lines.length * 4 + 3;
    }
    if (nota) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.text('Nota:', margin, finalY);
      doc.setFont('helvetica', 'normal');
      doc.text(nota, margin + 12, finalY);
      finalY += 6;
    }

    // Notes
    finalY += 2;
    const defaultNotas =
      'Solo incluyen gastos descritos en esta cotización.\n' +
      'Tarifa válida para carga general no peligrosa.\n' +
      '* Las tarifas están sujetas a disponibilidad de unidad, reconfirmar previo al embarque.\n' +
      '* En caso de demoras no atribuibles al proveedor podrían aplicar cargos adicionales.\n' +
      '* Alonso Forwarding Guatemala está excluido de responsabilidad por incumplimiento en itinerarios.\n' +
      '* El servicio de tramité de aduanas NO incluye permisos especiales.\n' +
      '* La mercancía debe estar debidamente embalada y rotulada desde origen.';
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
