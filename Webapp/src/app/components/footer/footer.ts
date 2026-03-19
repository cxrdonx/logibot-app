import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <footer class="bg-white border-t border-gray-200">
      <!-- Quick prompt chips -->
      <div
        *ngIf="!isDisabled"
        style="
          display: flex;
          gap: 6px;
          padding: 8px 12px 4px;
          overflow-x: auto;
          scrollbar-width: none;
          -ms-overflow-style: none;
        "
      >
        <button
          *ngFor="let p of quickPrompts"
          (click)="setQuickPrompt(p.text)"
          style="
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 5px 10px;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 20px;
            font-size: 12px;
            color: #1d4ed8;
            cursor: pointer;
            white-space: nowrap;
            flex-shrink: 0;
            transition: all 0.15s;
          "
          onmouseover="this.style.background='#dbeafe';this.style.borderColor='#93c5fd';this.style.transform='scale(1.04)'"
          onmouseout="this.style.background='#eff6ff';this.style.borderColor='#bfdbfe';this.style.transform='scale(1)'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <rect x="1" y="3" width="15" height="13" rx="1"/>
            <path d="M16 8h4l3 5v3h-7V8z"/>
            <circle cx="5.5" cy="18.5" r="2.5"/>
            <circle cx="18.5" cy="18.5" r="2.5"/>
          </svg>
          {{ p.label }}
        </button>
      </div>

      <!-- Input row -->
      <div class="relative flex items-center gap-2 p-3 pt-1">
        <input
          [(ngModel)]="inputText"
          (keydown.enter)="send()"
          [disabled]="isDisabled"
          type="text"
          placeholder="Ej: A Mixco con Nixon, 23 toneladas..."
          class="w-full bg-slate-100 text-slate-800 text-sm rounded-full pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all placeholder-slate-400 shadow-inner disabled:opacity-60"
        >
        <button
          (click)="send()"
          [disabled]="!inputText.trim() || isDisabled"
          class="absolute right-4 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white p-2 rounded-full transition-all shadow-md flex items-center justify-center aspect-square"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" x2="11" y1="2" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <p class="text-[10px] text-center text-gray-400 mb-2">
      </p>
    </footer>
  `,
  styles: [`
    input:focus {
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    /* hide webkit scrollbar on chips row */
    div::-webkit-scrollbar {
      display: none;
    }
  `]
})
export class FooterComponent {
  @Input() isDisabled: boolean = false;
  @Output() onSendMessage = new EventEmitter<string>();

  inputText: string = '';

  quickPrompts = [
    {
      label: 'Cotizar carga',
      text: '¿Cuánto cuesta enviar <peso_kg> kg desde <origen> hasta <destino>?'
    },
    {
      label: 'Con custodio',
      text: 'Necesito cotización con custodio para <peso_kg> kg de <origen> a <destino>'
    },
    {
      label: 'Cotización marítima',
      text: '¿Puedes generarme una cotización para un contenedor 40HC desde <puerto_origen> hasta <puerto_destino>, con <naviera>?'
    }
  ];

  setQuickPrompt(text: string): void {
    this.inputText = text;
  }

  send(): void {
    if (this.inputText.trim()) {
      this.onSendMessage.emit(this.inputText);
      this.inputText = '';
    }
  }
}
