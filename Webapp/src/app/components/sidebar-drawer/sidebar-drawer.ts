import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { SidebarService } from '../../services/sidebar.service';

@Component({
  selector: 'app-sidebar-drawer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- Backdrop -->
    <div
      *ngIf="isOpen"
      (click)="close()"
      class="fixed inset-0 bg-black/50 z-40 backdrop-blur-[1px]"
      style="animation: fadeIn 0.2s ease"></div>

    <!-- Drawer -->
    <nav
      [class.drawer-open]="isOpen"
      class="fixed top-0 left-0 h-full w-72 bg-[#0b1220] border-r border-white/[0.07]
             flex flex-col z-50 shadow-2xl drawer"
      style="will-change: transform">

      <!-- Brand header -->
      <div class="px-5 py-5 border-b border-white/[0.07] flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-[#050D9E] flex items-center justify-center flex-shrink-0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
            </svg>
          </div>
          <div>
            <p class="text-white font-bold text-sm leading-tight">LogiBotAI</p>
            <p class="text-slate-400 text-[11px] leading-tight">Sistema de Logística</p>
          </div>
        </div>
        <button (click)="close()" class="text-slate-500 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-white/[0.07]">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Menu -->
      <div class="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">

        <!-- LogiBot -->
        <button type="button" (click)="navigate('/chatbot-maritimo')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:bg-white/[0.07] group">
          <div class="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-cyan-500/30 transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/>
              <path d="M12 7v4"/>
              <line x1="8" y1="16" x2="8" y2="16" stroke-width="3" stroke-linecap="round"/>
              <line x1="12" y1="16" x2="12" y2="16" stroke-width="3" stroke-linecap="round"/>
              <line x1="16" y1="16" x2="16" y2="16" stroke-width="3" stroke-linecap="round"/>
            </svg>
          </div>
          <span class="text-slate-100 text-sm font-semibold">LogiBot</span>
        </button>

        <!-- Label Tarifas -->
        <div class="pt-3 pb-1 px-3">
          <p class="text-[10px] text-slate-600 font-semibold uppercase tracking-widest">Tarifas</p>
        </div>

        <!-- Tarifas Terrestres -->
        <div>
          <button type="button" (click)="toggleMenu('terrestres')"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:bg-white/[0.07] group">
            <div class="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-amber-500/30 transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="1" y="3" width="15" height="13" rx="1"/>
                <path d="M16 8h4l3 5v3h-7V8z"/>
                <circle cx="5.5" cy="18.5" r="2.5"/>
                <circle cx="18.5" cy="18.5" r="2.5"/>
              </svg>
            </div>
            <span class="text-slate-300 text-sm font-medium flex-1">Tarifas Terrestres</span>
            <svg [class.rotate-90]="openMenus['terrestres']"
              class="w-4 h-4 text-slate-600 transition-transform duration-200 flex-shrink-0"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <div *ngIf="openMenus['terrestres']" class="mt-0.5 ml-5 pl-3 border-l border-amber-500/25 space-y-0.5">
            <button type="button" (click)="navigate('/tarifas/create')"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] transition-all">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Crear nueva tarifa terrestre
            </button>
            <button type="button" (click)="navigate('/tarifas/list')"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] transition-all">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6" r="1" fill="currentColor" stroke="none"/><circle cx="3" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="3" cy="18" r="1" fill="currentColor" stroke="none"/></svg>
              Ver listado de tarifas terrestres
            </button>
          </div>
        </div>

        <!-- Tarifas Marítimas -->
        <div>
          <button type="button" (click)="toggleMenu('maritimas')"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:bg-white/[0.07] group">
            <div class="w-8 h-8 rounded-lg bg-sky-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-sky-500/30 transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M2 20a2.4 2.4 0 0 0 2 1 2.4 2.4 0 0 0 2-1 2.4 2.4 0 0 1 2-1 2.4 2.4 0 0 1 2 1 2.4 2.4 0 0 0 2 1 2.4 2.4 0 0 0 2-1 2.4 2.4 0 0 1 2-1 2.4 2.4 0 0 1 2 1"/>
                <path d="M4 18 3 8l9-6 9 6-1 10"/>
              </svg>
            </div>
            <span class="text-slate-300 text-sm font-medium flex-1">Tarifas Marítimas</span>
            <svg [class.rotate-90]="openMenus['maritimas']"
              class="w-4 h-4 text-slate-600 transition-transform duration-200 flex-shrink-0"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <div *ngIf="openMenus['maritimas']" class="mt-0.5 ml-5 pl-3 border-l border-sky-500/25 space-y-0.5">
            <button type="button" (click)="navigate('/tarifas/maritimo/create')"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] transition-all">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Nueva tarifa marítima
            </button>
            <button type="button" (click)="navigate('/tarifas/maritimo/list')"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] transition-all">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><circle cx="3" cy="6" r="1" fill="currentColor" stroke="none"/><circle cx="3" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="3" cy="18" r="1" fill="currentColor" stroke="none"/></svg>
              Ver tarifas marítimas
            </button>
          </div>
        </div>

        <!-- Label Cotizaciones -->
        <div class="pt-3 pb-1 px-3">
          <p class="text-[10px] text-slate-600 font-semibold uppercase tracking-widest">Cotizaciones</p>
        </div>

        <!-- Cotizaciones -->
        <div>
          <button type="button" (click)="toggleMenu('cotizaciones')"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:bg-white/[0.07] group">
            <div class="w-8 h-8 rounded-lg bg-[#050D9E]/40 flex items-center justify-center flex-shrink-0 group-hover:bg-[#050D9E]/60 transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="8" y1="13" x2="16" y2="13"/>
                <line x1="8" y1="17" x2="16" y2="17"/>
              </svg>
            </div>
            <span class="text-slate-300 text-sm font-medium flex-1">Cotizaciones</span>
            <svg [class.rotate-90]="openMenus['cotizaciones']"
              class="w-4 h-4 text-slate-600 transition-transform duration-200 flex-shrink-0"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <div *ngIf="openMenus['cotizaciones']" class="mt-0.5 ml-5 pl-3 border-l border-indigo-500/25 space-y-0.5">
            <button type="button" (click)="navigate('/cotizaciones/maritimas')"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] transition-all">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round">
                <path d="M2 20a2.4 2.4 0 0 0 2 1 2.4 2.4 0 0 0 2-1 2.4 2.4 0 0 1 2-1 2.4 2.4 0 0 1 2 1"/>
              </svg>
              Cotizaciones Marítimas
            </button>
            <button type="button" (click)="navigate('/cotizaciones/terrestres')"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] transition-all">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round">
                <rect x="1" y="5" width="12" height="9" rx="1"/>
              </svg>
              Cotizaciones Terrestres
            </button>
          </div>
        </div>

        <!-- Divider -->
        <div class="pt-2 pb-1"><div class="border-t border-white/[0.06]"></div></div>

        <!-- Orden de Compra -->
        <button type="button" (click)="navigate('/cotizaciones/orden-compra')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:bg-white/[0.07] group">
          <div class="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center flex-shrink-0 group-hover:bg-violet-500/30 transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 0 1-8 0"/>
            </svg>
          </div>
          <span class="text-slate-200 text-sm font-semibold">Orden de Compra</span>
        </button>

      </div>

      <!-- Footer -->
      <div class="px-4 py-4 border-t border-white/[0.07]">
        <button type="button" (click)="navigate('/tarifas')"
          class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition-all text-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M9 3v18M3 9h6"/>
          </svg>
          Ir al menú principal
        </button>
      </div>

    </nav>
  `,
  styles: [`
    .drawer {
      transform: translateX(-100%);
      transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .drawer-open {
      transform: translateX(0);
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
  `]
})
export class SidebarDrawerComponent implements OnInit, OnDestroy {
  isOpen = false;
  openMenus: Record<string, boolean> = {
    terrestres: false,
    maritimas: false,
    cotizaciones: false,
  };

  private sub!: Subscription;

  constructor(
    private sidebarService: SidebarService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.sub = this.sidebarService.open$.subscribe(v => (this.isOpen = v));
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  toggleMenu(key: string): void {
    this.openMenus[key] = !this.openMenus[key];
  }

  navigate(path: string): void {
    this.sidebarService.close();
    this.router.navigate([path]);
  }

  close(): void {
    this.sidebarService.close();
  }
}
