import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface RangoBasePrice {
  min_kg: number;
  max_kg: number;
  costo: number;
  concepto: string;
}

export interface Tarifa {
  id?: string;
  origen: string;
  destino: string;
  proveedor: string;
  fianza: number;
  dias_libres: number;
  estadia: number;
  tramite_de_aduana_cominter: number;
  condiciones_de_aduana_cominter: string;
  tramite_aduana: number;
  condiciones_aduana: string;
  custodio_comsi: number;
  custodio_yantarni: number;
  rango_base_precios: RangoBasePrice[];
}

@Injectable({
  providedIn: 'root'
})
export class TarifasService {
  private apiUrl = 'https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod/tarifas';

  constructor(private http: HttpClient) {}

  // GET all tarifas or filtered — API returns { count, items }
  getTarifas(filters?: { origen?: string; destino?: string; proveedor?: string }): Observable<Tarifa[]> {
    let params = new HttpParams();

    if (filters) {
      if (filters.origen) params = params.set('origen', filters.origen);
      if (filters.destino) params = params.set('destino', filters.destino);
      if (filters.proveedor) params = params.set('proveedor', filters.proveedor);
    }

    return this.http.get<{ count: number; items: Tarifa[] }>(this.apiUrl, { params }).pipe(
      map(res => res.items ?? [])
    );
  }

  // GET single tarifa by ID
  getTarifaById(id: string): Observable<Tarifa> {
    return this.http.get<Tarifa>(`${this.apiUrl}/${id}`);
  }

  // POST create new tarifa
  createTarifa(tarifa: Tarifa): Observable<Tarifa> {
    return this.http.post<Tarifa>(this.apiUrl, tarifa);
  }

  // PUT update tarifa
  updateTarifa(id: string, tarifa: Partial<Tarifa>): Observable<Tarifa> {
    return this.http.put<Tarifa>(`${this.apiUrl}/${id}`, tarifa);
  }

  // DELETE tarifa
  deleteTarifa(id: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/${id}`);
  }
}
