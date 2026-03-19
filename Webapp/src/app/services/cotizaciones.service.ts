import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

export interface Cotizacion {
  id: string;
  numero_cotizacion: string;
  tipo: string;
  tarifa_id?: string;
  fecha_creacion: string;
  fecha_actualizacion?: string;
  estado: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  datos: any;
}

export interface SaveCotizacionRequest {
  numero_cotizacion: string;
  tipo: string;
  tarifa_id?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  datos: any;
}

export interface SaveCotizacionResponse {
  message: string;
  id: string;
  numero_cotizacion: string;
}

@Injectable({ providedIn: 'root' })
export class CotizacionesService {
  private readonly apiUrl =
    'https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod/cotizaciones';

  constructor(private http: HttpClient) {}

  save(payload: SaveCotizacionRequest): Observable<SaveCotizacionResponse> {
    return this.http.post<SaveCotizacionResponse>(this.apiUrl, payload);
  }

  private getByTipo(tipo: string): Observable<Cotizacion[]> {
    const params = new HttpParams().set('tipo', tipo);
    return this.http
      .get<{ count: number; items: Cotizacion[] }>(this.apiUrl, { params })
      .pipe(map((res) => res.items ?? []));
  }

  getMaritimas(): Observable<Cotizacion[]> {
    return this.getByTipo('maritimo');
  }

  getTerrestres(): Observable<Cotizacion[]> {
    return this.getByTipo('terrestre');
  }

  getById(id: string): Observable<Cotizacion> {
    return this.http.get<Cotizacion>(`${this.apiUrl}/${id}`);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  update(id: string, body: { datos?: any; estado?: string }): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/${id}`, body);
  }
}
