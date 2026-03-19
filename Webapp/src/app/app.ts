import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarDrawerComponent } from './components/sidebar-drawer/sidebar-drawer';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, SidebarDrawerComponent],
  template: `
    <app-sidebar-drawer />
    <router-outlet />
  `
})
export class AppComponent {}
