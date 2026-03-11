import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  {
    path: 'login',
    renderMode: RenderMode.Prerender
  },
  {
    path: 'tarifas/edit/:id',
    renderMode: RenderMode.Client
  },
  {
    path: 'tarifas/view/:id',
    renderMode: RenderMode.Client
  },
  {
    path: 'tarifas/create',
    renderMode: RenderMode.Client
  },
  {
    path: 'tarifas',
    renderMode: RenderMode.Client
  },
  {
    path: 'change-password',
    renderMode: RenderMode.Client
  },
  {
    path: '',
    renderMode: RenderMode.Client
  },
  {
    path: '**',
    renderMode: RenderMode.Client
  }
];
