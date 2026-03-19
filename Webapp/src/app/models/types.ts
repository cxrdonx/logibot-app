export interface QuoteData {
  proveedor: string;
  origen: string;
  destino: string;
  base: number;
  dias_libres: number;
  estadia: number;
}

export interface CalculationData {
  weight: number;
  label: string;
  surcharge: number;
  total: number;
}

export interface ComparisonItem {
  proveedor: string;
  base: number;
  surcharge: number;
  total: number;
  dias_libres?: number;
}

export interface ApiResponse {
  type: 'text' | 'quote' | 'comparison';
  text?: string;
  data?: {
    quote?: QuoteData;
    calc?: CalculationData;
    dest?: string;
    items?: ComparisonItem[];
  };
}

export interface Message {
  id: number;
  sender: 'bot' | 'user';
  text?: string;
  type: 'text' | 'quote' | 'comparison' | 'xml-quotation';
  data?: any;
  timestamp: Date;
  isError?: boolean;
}

// XML Quotation structure
export interface XMLQuotation {
  proveedor: string;
  tipo?: string;       // 'terrestre' | 'maritimo'
  tarifa_id?: string;  // ID of source tarifa in DynamoDB
  datos_completos?: any;  // Full source tariff data (populated for maritime quotations)
  ruta: {
    origen: string;
    destino: string;
  };
  unidad: {
    tipo: string;
    peso_solicitado: number;
    peso_unidad: string;
  };
  tarifa_base: {
    monto: number;
    moneda: string;
    rango: string;
  };
  sobrepeso: {
    aplica: boolean;
    monto: number;
    moneda: string;
    descripcion: string;
  };
  custodio?: {
    tipo: string;
    costo_unitario: number;
    cantidad_unidades: number;
    costo_total: number;
    moneda: string;
    descripcion: string;
  };
  costos_adicionales: Array<{
    concepto: string;
    valor: number | string;
    unidad: string;
    descripcion: string;
  }>;
  resumen_costos: {
    subtotal: number;
    total: number;
    moneda: string;
    detalles: string;
    condiciones_aduana?: string;
    condiciones_cominter?: string;
    descripcion?: string;
    nota?: string;
  };
}

// New types for Chatbot V2 API
export interface ChatbotMessage {
  role: 'user' | 'assistant';
  content: [{ text: string }];
}

export interface ChatbotRequest {
  query: string;
  conversation_history?: ChatbotMessage[];
}

export interface ChatbotResponse {
  respuesta: string;
  items_found: number;
  datos_completos?: any;  // Full tariff data for maritime quotations
}

// Conversation management
export interface Conversation {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
  conversationHistory: ChatbotMessage[];
}

// Maritime Quotation types (ALCE V2)
export interface MaritimeLineItem {
  description: string;
  quantity: number;
  unit: string;
  currency: string;
  unit_price: number;
  amount: number;
}

export interface MaritimeCommodity {
  description: string;
  container_type: string;
  gross_weight: number;
  volume_cbm?: number;
  hs_code: string;
  country_of_origin: string;
}

export interface MaritimeTermsAndConditions {
  hs_code_limitations?: string;
  exclusions?: string[];
  carrier_conditions?: string[];
  currency_notes?: string;
  general_notes?: string;
}

export interface MaritimeQuotation {
  id?: string;
  dates: {
    quote_date: string;
    valid_from: string;
    valid_till: string;
  };
  prepared_by: string;
  requested_by: string;
  company: {
    name: string;
    contact: string;
    address: string;
    vat_number?: string;
  };
  shipment_type: string;
  movement_type: string;
  shipment_term: string;
  routing: {
    origin_port: string;
    via_port?: string;
    destination_port: string;
  };
  logistics: {
    shipping_line: string;
    transit_time_days: number;
  };
  commodities: MaritimeCommodity[];
  line_items: MaritimeLineItem[];
  total_amount: number;
  currency: string;
  terms_and_conditions?: MaritimeTermsAndConditions;
}
