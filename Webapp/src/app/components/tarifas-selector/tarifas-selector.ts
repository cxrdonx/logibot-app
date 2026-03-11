import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HeaderComponent } from '../header/header';

@Component({
  selector: 'app-tarifas-selector',
  standalone: true,
  imports: [CommonModule, HeaderComponent],
  templateUrl: './tarifas-selector.html',
  styleUrls: ['./tarifas-selector.css']
})
export class TarifasSelectorComponent {
  constructor(private router: Router) {}

  goTerrestre(): void {
    this.router.navigate(['/tarifas/create']);
  }

  goMaritimo(): void {
    this.router.navigate(['/tarifas/maritimo/create']);
  }

  goList(): void {
    this.router.navigate(['/tarifas/list']);
  }

  goMaritimoList(): void {
    this.router.navigate(['/tarifas/maritimo/list']);
  }

  goChatbotMaritimo(): void {
    this.router.navigate(['/chatbot-maritimo']);
  }

  goMenu(): void {
    this.router.navigate(['/tarifas/menu']);
  }
}
