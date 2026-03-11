import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MaritimeQuotation } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class MaritimeQuotationsService {
  private apiUrl = 'https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod/maritime-quotations';

  constructor(private http: HttpClient) {}

  // GET all maritime quotations
  getAll(): Observable<MaritimeQuotation[]> {
    return this.http.get<MaritimeQuotation[]>(this.apiUrl);
  }

  // GET single maritime quotation by ID
  getById(id: string): Observable<MaritimeQuotation> {
    return this.http.get<MaritimeQuotation>(`${this.apiUrl}/${id}`);
  }

  // POST create new maritime quotation
  create(quotation: MaritimeQuotation): Observable<MaritimeQuotation> {
    return this.http.post<MaritimeQuotation>(this.apiUrl, quotation);
  }

  // PUT update maritime quotation
  update(id: string, quotation: Partial<MaritimeQuotation>): Observable<MaritimeQuotation> {
    return this.http.put<MaritimeQuotation>(`${this.apiUrl}/${id}`, quotation);
  }

  // DELETE maritime quotation
  delete(id: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/${id}`);
  }
}
