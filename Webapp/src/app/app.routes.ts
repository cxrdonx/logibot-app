import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login';
import { ChatContainerComponent } from './components/chat-container/chat-container';
import { ChangePasswordComponent } from './components/change-password/change-password';
import { TarifasMenuComponent } from './components/tarifas-menu/tarifas-menu';
import { TarifasListComponent } from './components/tarifas/tarifas-list';
import { TarifasFormComponent } from './components/tarifas/tarifas-form';
import { TarifasSelectorComponent } from './components/tarifas-selector/tarifas-selector';
import { TarifasMaritimasListComponent } from './components/tarifas-maritimas/tarifas-maritimas-list';
import { authGuard } from './services/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: 'change-password',
    component: ChangePasswordComponent
  },
  {
    path: 'tarifas',
    component: TarifasSelectorComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/list',
    component: TarifasListComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/menu',
    component: TarifasMenuComponent,
    canActivate: [authGuard]
  },
  {
    path: '',
    component: ChatContainerComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/create',
    component: TarifasFormComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/edit/:id',
    component: TarifasFormComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/view/:id',
    component: TarifasFormComponent,
    canActivate: [authGuard]
  },
  // Maritime quotation routes
  {
    path: 'tarifas/maritimo/create',
    loadComponent: () =>
      import('./components/tarifas-maritimas/tarifas-maritimas-form').then(
        (m) => m.TarifasMaritimasFormComponent
      ),
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/maritimo/list',
    component: TarifasMaritimasListComponent,
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/maritimo/edit/:id',
    loadComponent: () =>
      import('./components/tarifas-maritimas/tarifas-maritimas-form').then(
        (m) => m.TarifasMaritimasFormComponent
      ),
    canActivate: [authGuard]
  },
  {
    path: 'tarifas/maritimo/view/:id',
    loadComponent: () =>
      import('./components/tarifas-maritimas/tarifas-maritimas-form').then(
        (m) => m.TarifasMaritimasFormComponent
      ),
    canActivate: [authGuard]
  },
  // Maritime chatbot route - redirected to unified central chatbot
  {
    path: 'chatbot-maritimo',
    redirectTo: '/'
  },
  // Cotizaciones marítimas management view
  {
    path: 'cotizaciones/maritimas',
    loadComponent: () =>
      import('./components/cotizaciones-maritimas/cotizaciones-maritimas').then(
        (m) => m.CotizacionesMaritimasComponent
      ),
    canActivate: [authGuard]
  },
  // Cotizaciones terrestres management view
  {
    path: 'cotizaciones/terrestres',
    loadComponent: () =>
      import('./components/cotizaciones-terrestres/cotizaciones-terrestres').then(
        (m) => m.CotizacionesTerrestresComponent
      ),
    canActivate: [authGuard]
  },
  // Purchase Order — consolidates maritime and terrestrial quotations
  {
    path: 'cotizaciones/orden-compra',
    loadComponent: () =>
      import('./components/orden-compra/orden-compra').then(
        (m) => m.OrdenCompraComponent
      ),
    canActivate: [authGuard]
  },
  {
    path: '**',
    redirectTo: 'login'
  }
];
