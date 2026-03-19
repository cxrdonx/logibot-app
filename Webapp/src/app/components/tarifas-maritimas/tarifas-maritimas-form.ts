import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { HeaderComponent } from '../header/header';
import { MaritimeQuotationsService } from '../../services/maritime-quotations.service';
import { MaritimeQuotation, MaritimeLineItem, MaritimeCommodity } from '../../models/types';

export type RequestedBy = {
  nameCompany: string;
  primaryContact: string;
  address: string;
  phone: string;
  email: string;
  vatNumber: string;
};

export type PortInfo = {
  portCodeName: string; // ej: NLRTM - ROTTERDAM - NETHERLANDS
};

export type QuoteDetails = {
  poNumber: string;
  shipmentType: string; // ej: CONTAINER (FCL)
  movementType: string; // ej: DOOR TO PORT
  shipmentTerm: string; // ej: FREE ON BOARD
};

export type CommodityItem = {
  description: string;
  containerType: string; // ej: 1 X 40HC
  grossWeightKg: number;
};

export type QuoteInfo = {
  quoteDate: string;
  validFrom: string;
  validTill: string;
  viaPort: string;
  shippingLine: string;
  transitTimeDays: number;
};

export type ChargeItem = {
  description: string;
  quantity: number;
  unit: string;
  minimum: number;
  currency: string; // ej: EUR
  price: number; // unit price
  exchangeRate: number;
  tax: string;
  frCr: string;
};

export type TarifaMaritima = {
  // Header / supplier
  supplierName: string;
  supplierWebsite: string;
  supplierEmail: string;
  supplierVat: string;

  requestedBy: RequestedBy;
  origin: PortInfo;
  destination: PortInfo;
  details: QuoteDetails;
  commodities: CommodityItem[];
  quoteInfo: QuoteInfo;
  charges: ChargeItem[];

  notes: string;
};

@Component({
  selector: 'app-tarifas-maritimas-form',
  standalone: true,
  imports: [CommonModule, FormsModule, HeaderComponent],
  templateUrl: './tarifas-maritimas-form.html',
  styleUrls: ['./tarifas-maritimas-form.css']
})
export class TarifasMaritimasFormComponent implements OnInit {
  loading = false;
  error: string | null = null;
  successMessage: string | null = null;
  editId: string | null = null;
  isViewMode = false;

  newCommodity: CommodityItem = { description: '', containerType: '', grossWeightKg: 0 };
  newCharge: ChargeItem = {
    description: '',
    quantity: 1,
    unit: 'PER SHIPMENT',
    minimum: 0,
    currency: 'EUR',
    price: 0,
    exchangeRate: 1,
    tax: '—',
    frCr: ''
  };

  tarifa: TarifaMaritima = {
    supplierName: 'Grupo Alonso',
    supplierWebsite: 'https://grupo-alonso.com/en/',
    supplierEmail: '',
    supplierVat: '',

    requestedBy: {
      nameCompany: '',
      primaryContact: '',
      address: '',
      phone: '',
      email: '',
      vatNumber: ''
    },
    origin: { portCodeName: '' },
    destination: { portCodeName: '' },
    details: {
      poNumber: '',
      shipmentType: 'CONTAINER (FCL)',
      movementType: 'DOOR TO PORT',
      shipmentTerm: 'FREE ON BOARD'
    },
    commodities: [],
    quoteInfo: {
      quoteDate: new Date().toISOString().slice(0, 10),
      validFrom: new Date().toISOString().slice(0, 10),
      validTill: '',
      viaPort: '',
      shippingLine: '',
      transitTimeDays: 0
    },
    charges: [],
    notes: ''
  };

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private maritimeService: MaritimeQuotationsService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    const url = this.router.url;

    if (id) {
      this.editId = id;
      this.isViewMode = url.includes('/view/');
      this.loadQuotation(id);
    }
  }

  private loadQuotation(id: string): void {
    this.loading = true;
    this.error = null;

    this.maritimeService.getById(id).subscribe({
      next: (data) => {
        this.loading = false;
        this.mapApiToForm(data);
      },
      error: (err) => {
        this.loading = false;
        this.error = 'Error al cargar la tarifa: ' + (err.message ?? 'Error desconocido');
      }
    });
  }

  private mapApiToForm(data: MaritimeQuotation): void {
    this.tarifa = {
      supplierName: data.prepared_by ?? '',
      supplierWebsite: '',
      supplierEmail: '',
      supplierVat: data.company.vat_number ?? '',

      requestedBy: {
        nameCompany: data.company.name ?? '',
        primaryContact: data.company.contact ?? '',
        address: data.company.address ?? '',
        phone: '',
        email: '',
        vatNumber: data.company.vat_number ?? ''
      },
      origin: { portCodeName: data.routing.origin_port ?? '' },
      destination: { portCodeName: data.routing.destination_port ?? '' },
      details: {
        poNumber: '',
        shipmentType: data.shipment_type ?? 'CONTAINER (FCL)',
        movementType: data.movement_type ?? 'DOOR TO PORT',
        shipmentTerm: data.shipment_term ?? 'FREE ON BOARD'
      },
      commodities: (data.commodities ?? []).map((c) => ({
        description: c.description,
        containerType: c.container_type,
        grossWeightKg: c.gross_weight
      })),
      quoteInfo: {
        quoteDate: data.dates.quote_date ?? '',
        validFrom: data.dates.valid_from ?? '',
        validTill: data.dates.valid_till ?? '',
        viaPort: data.routing.via_port ?? '',
        shippingLine: data.logistics.shipping_line ?? '',
        transitTimeDays: data.logistics.transit_time_days ?? 0
      },
      charges: (data.line_items ?? []).map((li) => ({
        description: li.description,
        quantity: li.quantity,
        unit: li.unit,
        minimum: 0,
        currency: li.currency,
        price: li.unit_price,
        exchangeRate: 1,
        tax: '—',
        frCr: ''
      })),
      notes: data.terms_and_conditions?.general_notes ?? ''
    };
  }

  private mapFormToApi(): MaritimeQuotation {
    const commodities: MaritimeCommodity[] = this.tarifa.commodities.map((c) => ({
      description: c.description,
      container_type: c.containerType,
      gross_weight: c.grossWeightKg,
      hs_code: '',
      country_of_origin: ''
    }));

    const lineItems: MaritimeLineItem[] = this.tarifa.charges.map((ch) => ({
      description: ch.description,
      quantity: ch.quantity,
      unit: ch.unit,
      currency: ch.currency,
      unit_price: ch.price,
      amount: this.getChargeAmount(ch)
    }));

    const totalAmount = lineItems.reduce((sum, li) => sum + li.amount, 0);

    const payload: MaritimeQuotation = {
      dates: {
        quote_date: this.tarifa.quoteInfo.quoteDate,
        valid_from: this.tarifa.quoteInfo.validFrom,
        valid_till: this.tarifa.quoteInfo.validTill
      },
      prepared_by: this.tarifa.supplierName,
      requested_by: this.tarifa.requestedBy.primaryContact || this.tarifa.requestedBy.nameCompany,
      company: {
        name: this.tarifa.requestedBy.nameCompany,
        contact: this.tarifa.requestedBy.primaryContact,
        address: this.tarifa.requestedBy.address,
        vat_number: this.tarifa.requestedBy.vatNumber || undefined
      },
      shipment_type: this.tarifa.details.shipmentType,
      movement_type: this.tarifa.details.movementType,
      shipment_term: this.tarifa.details.shipmentTerm,
      routing: {
        origin_port: this.tarifa.origin.portCodeName,
        via_port: this.tarifa.quoteInfo.viaPort || undefined,
        destination_port: this.tarifa.destination.portCodeName
      },
      logistics: {
        shipping_line: this.tarifa.quoteInfo.shippingLine,
        transit_time_days: Number(this.tarifa.quoteInfo.transitTimeDays) || 0
      },
      commodities,
      line_items: lineItems,
      total_amount: totalAmount,
      currency: lineItems[0]?.currency ?? 'EUR',
      terms_and_conditions: this.tarifa.notes
        ? { general_notes: this.tarifa.notes }
        : undefined
    };

    return payload;
  }

  getChargeAmount(c: ChargeItem): number {
    const base = (Number(c.quantity) || 0) * (Number(c.price) || 0);
    const min = Number(c.minimum) || 0;
    return Math.max(base, min);
  }

  get subTotal(): number {
    return (this.tarifa.charges || []).reduce((acc, c) => acc + this.getChargeAmount(c), 0);
  }

  addCommodity(): void {
    if (!this.newCommodity.description || !this.newCommodity.containerType) {
      return;
    }
    this.tarifa.commodities.push({
      ...this.newCommodity,
      grossWeightKg: Number(this.newCommodity.grossWeightKg) || 0
    });
    this.newCommodity = { description: '', containerType: '', grossWeightKg: 0 };
  }

  removeCommodity(index: number): void {
    this.tarifa.commodities.splice(index, 1);
  }

  addCharge(): void {
    if (!this.newCharge.description) {
      return;
    }
    this.tarifa.charges.push({
      ...this.newCharge,
      quantity: Number(this.newCharge.quantity) || 0,
      minimum: Number(this.newCharge.minimum) || 0,
      price: Number(this.newCharge.price) || 0,
      exchangeRate: Number(this.newCharge.exchangeRate) || 1
    });

    this.newCharge = {
      description: '',
      quantity: 1,
      unit: 'PER SHIPMENT',
      minimum: 0,
      currency: 'EUR',
      price: 0,
      exchangeRate: 1,
      tax: '—',
      frCr: ''
    };
  }

  removeCharge(index: number): void {
    this.tarifa.charges.splice(index, 1);
  }

  save(): void {
    this.error = null;

    if (!this.tarifa.origin.portCodeName || !this.tarifa.destination.portCodeName) {
      this.error = 'Origin port y Destination port son requeridos';
      return;
    }

    this.loading = true;
    const payload = this.mapFormToApi();

    if (this.editId) {
      this.maritimeService.update(this.editId, payload).subscribe({
        next: () => {
          this.loading = false;
          this.router.navigate(['/tarifas/maritimo/list']);
        },
        error: (err) => {
          this.loading = false;
          this.error = 'Error al actualizar la tarifa: ' + (err.message ?? 'Error desconocido');
        }
      });
    } else {
      this.maritimeService.create(payload).subscribe({
        next: () => {
          this.loading = false;
          this.router.navigate(['/tarifas/maritimo/list']);
        },
        error: (err) => {
          this.loading = false;
          this.error = 'Error al guardar la tarifa: ' + (err.message ?? 'Error desconocido');
        }
      });
    }
  }

  cancel(): void {
    this.router.navigate(['/tarifas/maritimo/list']);
  }
}
