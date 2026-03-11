import { Component, Input, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message, XMLQuotation } from '../../models/types';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-100 scroll-smooth h-full" #scrollContainer>

      <div class="text-center py-2">
        <span class="bg-white/50 text-gray-500 text-[10px] px-2 py-1 rounded-full shadow-sm">
          Hoy {{ today | date:'shortTime' }}
        </span>
      </div>

      <div *ngFor="let msg of messages" class="flex w-full" [ngClass]="msg.sender === 'user' ? 'justify-end' : 'justify-start'">

        <div class="max-w-[90%] flex flex-col gap-1">

          <div [ngClass]="{
            'text-white rounded-2xl rounded-tr-none shadow-md': msg.sender === 'user' && !msg.isError,
            'bg-white text-gray-800 rounded-2xl rounded-tl-none shadow-sm border border-gray-100': msg.sender === 'bot' && !msg.isError,
            'bg-red-50 text-red-800 border border-red-200 rounded-2xl rounded-tl-none': msg.isError
          }" [style.background-color]="msg.sender === 'user' && !msg.isError ? '#050D9E' : ''" class="p-3 transition-all duration-300">

            <p *ngIf="msg.text" class="text-sm whitespace-pre-wrap leading-relaxed">{{ msg.text }}</p>

            <!-- CARD: COTIZACIÓN ÚNICA -->
            <div *ngIf="msg.type === 'quote' && msg.data" class="mt-2 w-full min-w-[240px]">
              <div class="flex justify-between items-start border-b border-gray-100 pb-2 mb-2">
                <div>
                  <p class="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Proveedor</p>
                  <div class="flex items-center gap-1 font-bold text-slate-800">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[#050D9E]"><path d="M5 18H3c-.6 0-1-.4-1-1V7c0-.6.4-1 1-1h10c.6 0 1 .4 1 1v11"/><path d="M14 9h4l4 4v4c0 .6-.4 1-1 1h-2"/><circle cx="7" cy="18" r="2"/><path d="M15 18H9"/><circle cx="17" cy="18" r="2"/></svg>
                    {{ msg.data.quote.proveedor }}
                  </div>
                </div>
                <span class="bg-blue-50 text-blue-700 text-[10px] px-2 py-0.5 rounded border border-blue-100 font-medium">
                  {{ msg.data.quote.dias_libres }} Días Libres
                </span>
              </div>

              <div class="bg-slate-50 p-2 rounded mb-3 border border-slate-100 flex items-center gap-2">
                  <div class="text-red-500">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                  </div>
                  <div>
                    <p class="text-[10px] text-gray-400 uppercase">Ruta</p>
                    <p class="text-xs font-semibold text-gray-700">{{ msg.data.quote.origen }} <span class="text-gray-400">➝</span> {{ msg.data.quote.destino }}</p>
                  </div>
              </div>

              <div class="space-y-1.5 text-xs mb-3">
                <div class="flex justify-between text-gray-500">
                  <span>Base (Hasta 21t)</span>
                  <span>Q{{ msg.data.quote.base | number:'1.2-2' }}</span>
                </div>

                <div *ngIf="msg.data.calc.surcharge > 0" class="flex justify-between text-orange-700 bg-orange-50 px-1.5 py-0.5 rounded font-medium">
                  <span class="flex items-center gap-1">
                    ⚠️ {{ msg.data.calc.label }}
                  </span>
                  <span>+ Q{{ msg.data.calc.surcharge | number:'1.2-2' }}</span>
                </div>

                <div *ngIf="msg.data.calc.surcharge === 0" class="flex justify-between text-green-600 px-1.5">
                  <span class="flex items-center gap-1">✅ Peso Estándar</span>
                  <span>Q0.00</span>
                </div>
              </div>

              <div class="border-t border-dashed border-gray-300 pt-2 flex justify-between items-center">
                  <span class="text-[10px] uppercase font-bold text-gray-500">Total Estimado</span>
                  <span class="text-xl font-bold text-[#050D9E]">Q{{ msg.data.calc.total | number:'1.2-2' }}</span>
              </div>

              <button class="w-full mt-3 bg-slate-800 hover:bg-slate-900 text-white text-xs py-2 rounded transition-colors flex items-center justify-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2"/><path d="M8 17h2"/><path d="M14 13h2"/><path d="M14 17h2"/></svg>
                Generar Orden
              </button>
            </div>

            <!-- CARD: COMPARATIVA -->
            <div *ngIf="msg.type === 'comparison' && msg.data" class="mt-2 w-full min-w-[260px]">
              <div class="border-b border-gray-100 pb-2 mb-2 flex justify-between items-center">
                  <div>
                    <p class="text-[10px] text-gray-400 font-bold uppercase">Comparativa de Precios</p>
                    <p class="font-bold text-slate-800 text-sm">Destino: {{ msg.data.dest }}</p>
                  </div>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[#050D9E]"><path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/></svg>
              </div>

              <div class="space-y-2">
                <div *ngFor="let item of msg.data.items" class="bg-slate-50 border border-slate-200 p-2 rounded hover:bg-white hover:border-[#050D9E] transition-colors cursor-pointer group">
                  <div class="flex justify-between items-center mb-1">
                    <span class="text-xs font-bold text-slate-700 group-hover:text-[#050D9E]">{{ item.proveedor }}</span>
                    <span class="text-sm font-bold text-[#050D9E]">Q{{ item.total | number:'1.0-0' }}</span>
                  </div>
                  <div class="flex justify-between text-[10px] text-gray-500">
                      <span>Base: Q{{ item.base }}</span>
                      <span *ngIf="item.surcharge > 0" class="text-orange-600 font-medium">+Q{{item.surcharge}} Peso</span>
                  </div>
                </div>
              </div>
              <p class="text-[10px] text-center text-gray-400 mt-2">Calculado por LogiBot AI.</p>
            </div>

            <!-- CARD: COTIZACIÓN XML -->
            <div *ngIf="msg.type === 'xml-quotation' && msg.data" class="w-full min-w-[320px] max-w-[480px]">
              <!-- Header con Proveedor -->
              <div class="bg-gradient-to-r from-[#050D9E] to-[#050D9E] text-white p-4 rounded-t-lg">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-[10px] uppercase tracking-wider opacity-90">Cotización de Transporte</p>
                    <h3 class="text-lg font-bold flex items-center gap-2 mt-1">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 18H3c-.6 0-1-.4-1-1V7c0-.6.4-1 1-1h10c.6 0 1 .4 1 1v11"/><path d="M14 9h4l4 4v4c0 .6-.4 1-1 1h-2"/><circle cx="7" cy="18" r="2"/><path d="M15 18H9"/><circle cx="17" cy="18" r="2"/></svg>
                      {{ msg.data.proveedor }}
                    </h3>
                  </div>
                  <div class="text-right">
                    <p class="text-2xl font-bold">{{ calculateTotalFinal(msg.data) | number:'1.2-2' }}</p>
                    <p class="text-xs opacity-90">{{ msg.data.resumen_costos.moneda }}</p>
                  </div>
                </div>
              </div>

              <!-- Ruta -->
              <div class="bg-slate-50 border-x border-gray-200 p-3 flex items-center gap-3">
                <div class="flex-1">
                  <p class="text-[10px] text-gray-500 uppercase font-semibold">Origen</p>
                  <p class="text-sm font-bold text-gray-800">{{ msg.data.ruta.origen }}</p>
                </div>
                <div class="text-[#050D9E]">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                </div>
                <div class="flex-1">
                  <p class="text-[10px] text-gray-500 uppercase font-semibold">Destino</p>
                  <p class="text-sm font-bold text-gray-800">{{ msg.data.ruta.destino }}</p>
                </div>
              </div>

              <!-- Unidad y Peso -->
              <div class="bg-white border-x border-gray-200 p-3">
                <div class="flex items-center gap-2 mb-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-[#050D9E]"><rect x="1" y="3" width="15" height="13"/><path d="M16 8h2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-2"/></svg>
                  <span class="text-sm font-semibold text-gray-800">{{ msg.data.unidad.tipo }}</span>
                </div>
                <div class="flex gap-4 text-xs">
                  <div class="flex-1 bg-blue-50 p-2 rounded">
                    <p class="text-gray-600">Peso Solicitado</p>
                    <p class="font-bold text-blue-700">{{ msg.data.unidad.peso_solicitado | number:'1.0-0' }} {{ msg.data.unidad.peso_unidad }}</p>
                  </div>
                  <div class="flex-1 bg-gray-50 p-2 rounded">
                    <p class="text-gray-600">Rango Tarifa</p>
                    <p class="font-bold text-gray-700">{{ msg.data.tarifa_base.rango }}</p>
                  </div>
                </div>
              </div>

              <!-- Desglose de Costos -->
              <div class="bg-white border-x border-gray-200 p-3">
                <p class="text-xs font-bold text-gray-600 uppercase mb-2">Desglose de Costos</p>
                <div class="space-y-2">
                  <!-- Tarifa Base -->
                  <div class="flex justify-between items-center text-sm">
                    <span class="text-gray-700">Tarifa Base</span>
                    <span class="font-semibold text-gray-800">{{ msg.data.tarifa_base.monto | number:'1.2-2' }} {{ msg.data.tarifa_base.moneda }}</span>
                  </div>

                  <!-- Sobrepeso -->
                  <div *ngIf="msg.data.sobrepeso.aplica" class="flex justify-between items-center text-sm bg-orange-50 p-2 rounded-md border border-orange-200">
                    <div>
                      <span class="text-orange-800 font-medium flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        Sobrepeso
                      </span>
                      <p class="text-[10px] text-orange-600">{{ msg.data.sobrepeso.descripcion }}</p>
                    </div>
                    <span class="font-bold text-orange-700">+ {{ msg.data.sobrepeso.monto | number:'1.2-2' }} {{ msg.data.sobrepeso.moneda }}</span>
                  </div>

                  <!-- Custodio (si aplica) -->
                  <div *ngIf="msg.data.custodio" class="flex justify-between items-center text-sm bg-purple-50 p-2 rounded-md border border-purple-200">
                    <div>
                      <span class="text-purple-800 font-medium">{{ msg.data.custodio.tipo }}</span>
                      <p class="text-[10px] text-purple-600">{{ msg.data.custodio.descripcion }} ({{ msg.data.custodio.cantidad_unidades }} unidades × {{ msg.data.custodio.costo_unitario }})</p>
                    </div>
                    <span class="font-bold text-purple-700">{{ msg.data.custodio.costo_total | number:'1.2-2' }} {{ msg.data.custodio.moneda }}</span>
                  </div>

                  <!-- Subtotal -->
                  <div class="flex justify-between items-center text-sm pt-2 border-t border-dashed border-gray-300">
                    <span class="font-semibold text-gray-700">Subtotal</span>
                    <span class="font-bold text-[#050D9E]">{{ calculateSubtotal(msg.data) | number:'1.2-2' }} {{ msg.data.resumen_costos.moneda }}</span>
                  </div>
                </div>
              </div>

              <!-- Costos Adicionales -->
              <div *ngIf="msg.data.costos_adicionales && msg.data.costos_adicionales.length > 0" class="bg-gray-50 border-x border-gray-200 p-3">
                <p class="text-xs font-bold text-gray-600 uppercase mb-2 flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                  Información Adicional
                </p>
                <div class="space-y-1.5">
                  <div *ngFor="let costo of msg.data.costos_adicionales" class="flex justify-between items-start text-xs bg-white p-2 rounded border border-gray-200">
                    <div class="flex-1">
                      <p class="font-medium text-gray-700">{{ costo.concepto }}</p>
                      <p class="text-[10px] text-gray-500">{{ costo.descripcion }}</p>
                    </div>
                    <span class="font-semibold text-gray-800 whitespace-nowrap ml-2">{{ costo.valor }} {{ costo.unidad }}</span>
                  </div>
                </div>
              </div>

              <!-- Condiciones -->
              <div *ngIf="msg.data.resumen_costos.condiciones_aduana || msg.data.resumen_costos.condiciones_cominter" class="bg-blue-50 border-x border-gray-200 p-3">
                <p class="text-xs font-bold text-blue-800 uppercase mb-2">Condiciones Especiales</p>
                <div class="space-y-1 text-xs text-blue-700">
                  <p *ngIf="msg.data.resumen_costos.condiciones_aduana" class="flex items-start gap-1">
                    <span class="font-semibold">Aduana:</span>
                    <span>{{ msg.data.resumen_costos.condiciones_aduana }}</span>
                  </p>
                  <p *ngIf="msg.data.resumen_costos.condiciones_cominter" class="flex items-start gap-1">
                    <span class="font-semibold">Cominter:</span>
                    <span>{{ msg.data.resumen_costos.condiciones_cominter }}</span>
                  </p>
                </div>
              </div>

              <!-- Footer con Total y Nota -->
              <div class="bg-gradient-to-br from-slate-700 to-slate-800 text-white p-4 rounded-b-lg">
                <div class="flex justify-between items-center mb-2">
                  <span class="text-sm font-semibold uppercase tracking-wide">Total Final</span>
                  <span class="text-3xl font-bold">{{ calculateTotalFinal(msg.data) | number:'1.2-2' }}</span>
                </div>
                <p *ngIf="msg.data.resumen_costos.detalles" class="text-xs opacity-80 mb-1">{{ msg.data.resumen_costos.detalles }}</p>
                <p *ngIf="msg.data.resumen_costos.nota" class="text-[10px] bg-yellow-500/20 text-yellow-200 p-2 rounded mt-2 border border-yellow-500/30">
                  ℹ️ {{ msg.data.resumen_costos.nota }}
                </p>
              </div>

              <!-- Botón de Acción -->
              <button 
                (click)="generateQuotationPDF(msg.data)" 
                class="w-full mt-3 bg-[#050D9E] hover:bg-[#040b7a] text-white text-sm py-3 rounded-lg transition-colors flex items-center justify-center gap-2 shadow-md hover:shadow-lg active:scale-95 transform">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                Aceptar Cotización
              </button>
            </div>

          </div>

          <span class="text-[10px] text-gray-400 px-1" [ngClass]="msg.sender === 'user' ? 'text-right' : 'text-left'">
            {{ msg.sender === 'bot' ? 'LogiBot AI' : 'Tú' }} • {{ msg.timestamp | date:'shortTime' }}
          </span>
        </div>
      </div>

      <div *ngIf="isTyping" class="flex justify-start animate-fade-in p-4 pt-0">
          <div class="bg-white p-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 flex gap-1 items-center">
            <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
            <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-100"></div>
            <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-200"></div>
          </div>
      </div>

      <div #scrollEnd></div>
    </div>
  `,
  styles: [`
    .overflow-y-auto::-webkit-scrollbar {
      width: 6px;
    }
    .overflow-y-auto::-webkit-scrollbar-track {
      background: transparent;
    }
    .overflow-y-auto::-webkit-scrollbar-thumb {
      background-color: #cbd5e1;
      border-radius: 20px;
    }
  `]
})
export class ChatComponent implements AfterViewChecked {
  @Input() messages: Message[] = [];
  @Input() isTyping: boolean = false;
  @ViewChild('scrollEnd') private scrollEnd!: ElementRef;

  today: Date = new Date();

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.scrollEnd.nativeElement.scrollIntoView({ behavior: 'smooth' });
    } catch(err) { }
  }

  /**
   * Calcula el subtotal sumando tarifa base + sobrepeso + custodio
   */
  calculateSubtotal(quotation: XMLQuotation): number {
    let subtotal = quotation.tarifa_base.monto;
    
    // Sumar sobrepeso si aplica
    if (quotation.sobrepeso.aplica) {
      subtotal += quotation.sobrepeso.monto;
    }
    
    // Sumar custodio si existe
    if (quotation.custodio) {
      subtotal += quotation.custodio.costo_total;
    }
    
    return subtotal;
  }

  /**
   * Calcula el total final sumando manualmente subtotal + costos adicionales
   * (fianza, trámite de aduana, trámite de cominter, etc.)
   */
  calculateTotalFinal(quotation: XMLQuotation): number {
    // Iniciar con el subtotal (tarifa base + sobrepeso + custodio)
    let total = this.calculateSubtotal(quotation);
    
    // Sumar costos adicionales que no sean "días libres"
    if (quotation.costos_adicionales && quotation.costos_adicionales.length > 0) {
      quotation.costos_adicionales.forEach(costo => {
        // Excluir conceptos que contengan "día" en cualquier parte
        if (costo.concepto.toLowerCase().indexOf('libres') === -1) {
          const valor = parseFloat(String(costo.valor).replace('Q', '').replace(',', '')) || 0;
          total += valor;
        }
      });
    }
    
    return total;
  }

  /**
   * Carga una imagen y la convierte a Data URL para usar en jsPDF
   */
  private loadImageAsDataUrl(url: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'Anonymous';
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0);
          resolve(canvas.toDataURL('image/jpeg'));
        } else {
          reject('No se pudo obtener el contexto del canvas');
        }
      };
      img.onerror = () => reject('Error al cargar la imagen');
      img.src = url;
    });
  }

  /**
   * Genera un PDF con la cotización y lo descarga
   */
  async generateQuotationPDF(quotation: XMLQuotation): Promise<void> {
    // Cargar la imagen primero
    const logoDataUrl = await this.loadImageAsDataUrl('/alonso.jpeg');
    
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    let yPos = 20;

    // Header
    doc.setFillColor(5, 13, 158); // #050D9E
    doc.rect(0, 0, pageWidth, 60, 'F');
    
    // Debe de estar centrado y es un banner alargado por lo que debe de ir con más largo para que se ve abien la imagen
    if (logoDataUrl) {
      doc.addImage(logoDataUrl, 'JPEG', (pageWidth - 150) / 2, 5, 150, 30);
    }
    
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(19);
    doc.setFont('helvetica', 'bold');
    doc.text('COTIZACIÓN DE TRANSPORTE', pageWidth / 2, 50, { align: 'center' });
    
    //doc.setFontSize(16);
    //doc.text(quotation.proveedor, pageWidth / 2, 28, { align: 'center' });

    yPos =  70;
    doc.setTextColor(0, 0, 0);

    // Información de Ruta
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('OFERTA DE SERVICIOS', 14, yPos);
    yPos += 8;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    autoTable(doc, {
      startY: yPos,
      head: [['Origen', 'Destino']],
      body: [[quotation.ruta.origen, quotation.ruta.destino]],
      theme: 'grid',
      headStyles: { fillColor: [5, 13, 158] }, // #050D9E
      margin: { left: 14, right: 14 }
    });

    yPos = (doc as any).lastAutoTable.finalY + 10;

    // Información de Unidad
    // doc.setFontSize(12);
    // doc.setFont('helvetica', 'bold');
    // doc.text('INFORMACIÓN DE UNIDAD', 14, yPos);
    // yPos += 8;

    // autoTable(doc, {
    //   startY: yPos,
    //   head: [['Tipo de Unidad', 'Peso Solicitado', 'Rango de Tarifa']],
    //   body: [[
    //     quotation.unidad.tipo,
    //     `${quotation.unidad.peso_solicitado.toLocaleString()} ${quotation.unidad.peso_unidad}`,
    //     quotation.tarifa_base.rango
    //   ]],
    //   theme: 'grid',
    //   headStyles: { fillColor: [5, 13, 158] }, // #050D9E
    //   margin: { left: 14, right: 14 }
    // });

    // yPos = (doc as any).lastAutoTable.finalY + 10;

    // Calcular subtotal correcto
    const subtotalCalculado = this.calculateSubtotal(quotation);

    // Desglose de Costos
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('DESGLOSE DE COSTOS', 14, yPos);
    yPos += 8;

    //AÑADIR EL PESO DEL CONTENEDOR
    const pesoContenedor = `${quotation.unidad.peso_solicitado.toLocaleString()} ${quotation.unidad.peso_unidad}`;
    const costosBody: any[] = [
      [`Tarifa  ${pesoContenedor}`, `${quotation.tarifa_base.monto.toFixed(2)} ${quotation.tarifa_base.moneda} `]
    ];

    if (quotation.sobrepeso.aplica) {
      costosBody.push([
        `Sobrepeso - ${quotation.sobrepeso.descripcion}`,
        `${quotation.sobrepeso.monto.toFixed(2)} ${quotation.sobrepeso.moneda}`
      ]);
    }

    if (quotation.custodio) {
      costosBody.push([
        `${quotation.custodio.tipo} - ${quotation.custodio.descripcion}`,
        `${quotation.custodio.costo_total.toFixed(2)} ${quotation.custodio.moneda}`
      ]);
    }

    costosBody.push([
      { content: 'SUBTOTAL', styles: { fontStyle: 'bold' } },
      { content: `${subtotalCalculado.toFixed(2)} ${quotation.resumen_costos.moneda}`, styles: { fontStyle: 'bold' } }
    ]);

    autoTable(doc, {
      startY: yPos,
      head: [['Concepto', 'Monto']],
      body: costosBody,
      theme: 'striped',
      headStyles: { fillColor: [5, 13, 158] }, // #050D9E
      margin: { left: 14, right: 14 }
    });

    yPos = (doc as any).lastAutoTable.finalY + 10;
    
    // Costos Adicionales (Información)
    if (quotation.costos_adicionales && quotation.costos_adicionales.length > 0) {
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      doc.text('INFORMACIÓN ADICIONAL', 14, yPos);
      yPos += 8;

      // Procesar costos adicionales y consolidar trámites de aduana
      const costosAdicionalesBody: any[] = [];
      let tramiteAduanaValores: string[] = [];
      let tramiteAduanaDescripciones: string[] = [];

      quotation.costos_adicionales.forEach(costo => {
        const conceptoLower = costo.concepto.toLowerCase();
        
        // Si es trámite de aduana o cominter, guardar el valor
        if (conceptoLower.includes('aduana') || conceptoLower.includes('cominter')) {
          // Extraer solo el número del valor y agregar símbolo Q
          const valorNumerico = String(costo.valor).replace('Q', '').replace(',', '').trim();
          tramiteAduanaValores.push(`Q${valorNumerico}`);
          if (costo.descripcion && !tramiteAduanaDescripciones.includes(costo.descripcion)) {
            tramiteAduanaDescripciones.push(costo.descripcion);
          }
        } else {
          // Otros conceptos se agregan normalmente
          costosAdicionalesBody.push([
            costo.concepto,
            `${costo.valor} ${costo.unidad}`,
            costo.descripcion
          ]);
        }
      });

      // Agregar la fila consolidada de trámite de aduana si hay valores
      if (tramiteAduanaValores.length > 0) {
        const valorConsolidado = tramiteAduanaValores.join(' o ');
        const descripcionConsolidada = tramiteAduanaDescripciones.join(' / ');
        
        costosAdicionalesBody.unshift([
          'Tramite de aduana',
          valorConsolidado,
          descripcionConsolidada
        ]);
      }

      autoTable(doc, {
        startY: yPos,
        head: [['Concepto', 'Valor', 'Descripción']],
        body: costosAdicionalesBody,
        theme: 'grid',
        headStyles: { fillColor: [204, 204, 204] }, // #cccccc
        margin: { left: 14, right: 14 },
        styles: { fontSize: 8 }
      });

      yPos = (doc as any).lastAutoTable.finalY + 10;
    }

    // Calcular el total final sumando manualmente todos los componentes
    const totalFinalCalculado = this.calculateTotalFinal(quotation);

    // Condiciones Especiales
    if (quotation.resumen_costos.condiciones_aduana || quotation.resumen_costos.condiciones_cominter) {
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      doc.text('CONDICIONES ESPECIALES', 14, yPos);
      yPos += 8;

      const condicionesBody: any[] = [];
      
      if (quotation.resumen_costos.condiciones_aduana) {
        condicionesBody.push(['Hasta 10 Lineas o 50 lineas dependiendo el proveedor']);
      }
      

      autoTable(doc, {
        startY: yPos,
        body: condicionesBody,
        theme: 'plain',
        margin: { left: 14, right: 14 },
        styles: { fontSize: 9 }
      });

      yPos = (doc as any).lastAutoTable.finalY + 40;
    }

    // Total Final
    doc.setFillColor(204, 204, 204); // #cccccc
    doc.rect(14, yPos, pageWidth - 28, 25, 'F');
    
    doc.setTextColor(0, 0, 0); // Texto negro para que contraste con el gris
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text('TOTAL FINAL', 20, yPos + 10);
    doc.setFontSize(20);
    doc.text(
      `${totalFinalCalculado.toFixed(2)} ${quotation.resumen_costos.moneda}`,
      pageWidth - 20,
      yPos + 10,
      { align: 'right' }
    );

    yPos += 30;
    doc.setTextColor(0, 0, 0);

    // Detalles y Nota
    // if (quotation.resumen_costos.detalles) {
    //   doc.setFontSize(9);
    //   doc.setFont('helvetica', 'italic');
    //   doc.setTextColor(204, 204, 204); // #cccccc
    //   doc.text(`Detalles: ${quotation.resumen_costos.detalles}`, 14, yPos);
    //   yPos += 6;
    // }

    // if (quotation.resumen_costos.nota) {
    //   doc.setFontSize(9);
    //   doc.setFont('helvetica', 'bold');
    //   doc.setTextColor(204, 204, 204); // #cccccc
    //   doc.text(`Nota: ${quotation.resumen_costos.nota}`, 14, yPos);
    //   yPos += 6;
    // }

    // Footer
    const pageHeight = doc.internal.pageSize.getHeight();
    
    // Agregar logo pequeño en el footer
    // if (logoDataUrl) {
    //   doc.addImage(logoDataUrl, 'JPEG', pageWidth / 2 - 5, pageHeight - 20, 10, 10);
    // }
    
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    //cambiar por negro
    doc.setTextColor(0, 0, 0);

    // Generar nombre de archivo solo con la ruta y el timestamp en lugar del proveedor
    const filePath = `Cotizacion_${new Date().getTime()}.pdf`;

    // Descargar PDF
    doc.save(filePath);
  }
}
