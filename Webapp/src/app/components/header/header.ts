import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { Conversation } from '../../models/types';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <header class="bg-slate-900 text-white p-4 shadow-md z-10">
      <div class="flex justify-between items-center mb-2">
        <div class="flex gap-3 items-center flex-1">
          <div class="bg-blue-600 p-2 rounded-lg shadow-lg shadow-blue-900/50">
            <!-- Icono Bot -->
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
          </div>
          <div class="flex-1">
            <h1 class="font-bold text-lg leading-tight">LogiBotAI Alonso Forwarding</h1>
            <div class="flex items-center gap-1">
              <span class="w-2 h-2 rounded-full" [ngClass]="isOnline ? 'bg-green-400 animate-pulse' : 'bg-red-500'"></span>
              <p class="text-[10px] text-blue-200 uppercase tracking-wider">
                {{ isOnline ? 'Cotizador' : 'Offline' }}
              </p>
            </div>
          </div>
        </div>
        <div class="flex gap-2">
          <button (click)="navigateToTarifas()" class="text-gray-400 hover:text-white transition-colors" title="Gestión de Tarifas">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
          </button>
          <button (click)="toggleConversations()" class="text-gray-400 hover:text-white transition-colors relative" title="Conversaciones">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <span *ngIf="conversations.length > 1" class="absolute -top-1 -right-1 bg-[#050D9E] text-white text-[8px] w-4 h-4 rounded-full flex items-center justify-center">
              {{conversations.length}}
            </span>
          </button>
          <button (click)="onReset.emit()" class="text-gray-400 hover:text-white transition-colors" title="Reiniciar">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
          </button>
          <button (click)="handleLogout()" class="text-gray-400 hover:text-red-400 transition-colors" title="Cerrar Sesión">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </div>
      
      <!-- Dropdown de conversaciones -->
      <div *ngIf="showConversations" class="mt-3 bg-slate-800 rounded-lg shadow-lg overflow-hidden">
        <div class="p-2 border-b border-slate-700 flex justify-between items-center">
          <span class="text-xs font-semibold text-gray-300">Conversaciones</span>
          <button (click)="onNewConversation.emit()" class="text-xs bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded transition-colors flex items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Nueva
          </button>
        </div>
        <div class="max-h-64 overflow-y-auto">
          <div *ngFor="let conv of conversations" 
               (click)="onSelectConversation.emit(conv.id)"
               class="p-3 hover:bg-slate-700 cursor-pointer transition-colors border-b border-slate-700/50 flex justify-between items-start"
               [ngClass]="{'bg-slate-700': conv.id === currentConversationId}">
            <div class="flex-1">
              <p class="text-sm font-medium text-white">{{conv.name}}</p>
              <p class="text-[10px] text-gray-400 mt-1">
                {{conv.messages.length}} mensajes • {{formatDate(conv.updatedAt)}}
              </p>
            </div>
            <button (click)="onDeleteConversation.emit(conv.id); $event.stopPropagation()" 
                    class="text-gray-500 hover:text-red-400 transition-colors ml-2"
                    title="Eliminar">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      </div>
      <!--
      <nav class="flex gap-4 items-center">
        <a routerLink="/" class="text-gray-400 hover:text-white transition-colors px-3 py-1 rounded hover:bg-slate-700">Chat</a>
        <a routerLink="/tarifas" class="text-gray-400 hover:text-white transition-colors px-3 py-1 rounded hover:bg-slate-700">Tarifas</a>
      </nav>
      <div class="flex gap-2 items-center">
        <button (click)="onReset.emit()" class="text-gray-400 hover:text-white transition-colors" title="Reiniciar">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
        </button>
        <button (click)="onLogout.emit()" class="text-gray-400 hover:text-white transition-colors px-3 py-1 rounded hover:bg-slate-700" title="Logout">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
        </button>
      </div>
      !-->
    </header>
  `,
  styles: [`
    .max-h-64::-webkit-scrollbar {
      width: 4px;
    }
    .max-h-64::-webkit-scrollbar-track {
      background: #1e293b;
    }
    .max-h-64::-webkit-scrollbar-thumb {
      background-color: #475569;
      border-radius: 20px;
    }
  `]
})
export class HeaderComponent {
  @Input() isOnline: boolean = true;
  @Input() conversations: Conversation[] = [];
  @Input() currentConversationId: string = '';
  
  @Output() onReset = new EventEmitter<void>();
  @Output() onNewConversation = new EventEmitter<void>();
  @Output() onSelectConversation = new EventEmitter<string>();
  @Output() onDeleteConversation = new EventEmitter<string>();
  @Output() onLogout = new EventEmitter<void>();

  showConversations = false;

  constructor(private router: Router) {}

  toggleConversations() {
    this.showConversations = !this.showConversations;
  }

  navigateToTarifas() {
    this.router.navigate(['/tarifas']);
  }

  handleLogout() {
    // Limpiar localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('id_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_email');
    
    // Emitir evento de logout si es necesario
    this.onLogout.emit();
    
    // Redirigir al login
    this.router.navigate(['/login']);
  }

  formatDate(date: Date): string {
    const d = new Date(date);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 1) return 'Hace un momento';
    if (hours < 24) return `Hace ${hours}h`;
    if (hours < 48) return 'Ayer';
    
    return d.toLocaleDateString('es-GT', { day: '2-digit', month: 'short' });
  }
}

