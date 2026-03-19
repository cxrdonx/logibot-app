---
name: project_patterns
description: Angular component conventions, PDF generation pattern, service usage, and template gotchas found in the LogiBotIA codebase
type: project
---

## Component file naming
- Components use no `.component` suffix: `orden-compra.ts`, `orden-compra.html`, `orden-compra.css`
- Selector format: `app-[kebab-name]`
- All components are standalone; use `CommonModule` + `FormsModule` as needed

## PDF generation (jsPDF + jspdf-autotable)
- Always dynamic import: `const { jsPDF } = await import('jspdf')` and `const autoTable = (await import('jspdf-autotable')).default`
- Cast doc: `new (jsPDF as any)({ orientation: 'portrait', unit: 'mm', format: 'a4' })`
- Logo loaded once via `loadImg('/alonso.jpeg')`, reused in header and footer
- Logo header position: `doc.addImage(logoData, 'JPEG', margin, 6, 70, 20)`
- Access finalY after autoTable: `(doc as any).lastAutoTable.finalY`
- Brand blue fillColor: `[5, 13, 158]` (matches `#050D9E`)

## Template gotchas
- `Number(x)` is NOT available in Angular templates — add a `toNum(val)` helper method to the component class
- `*ngFor` items with index use `let i = index`
- `[class.xxx]="condition"` for conditional classes on the same element as `*ngFor`

## CotizacionesService
- `getMaritimas()` and `getTerrestres()` return `Observable<Cotizacion[]>`
- Maritime datos shape: `datos.company.name`, `datos.routing.origin_port/destination_port`, `datos.logistics.shipping_line/transit_time_days`, `datos.commodities[0].container_type`, `datos.line_items[]`, `datos.total_amount`, `datos.currency`
- Terrestrial datos shape: `datos.cliente`, `datos.proveedor`, `datos.ruta.origen/destino`, `datos.unidad.tipo/peso_solicitado/peso_unidad`, `datos.tarifa_base.monto/moneda/rango`, `datos.sobrepeso.aplica/monto/descripcion`, `datos.custodio.tipo/costo_total/cantidad_unidades/costo_unitario`, `datos.costos_adicionales[]`, `datos.resumen_costos.subtotal/total/moneda`

## Routing pattern
- Lazy-loaded routes use `loadComponent` with `.then((m) => m.ComponentClass)`
- All protected routes use `canActivate: [authGuard]`
- Route `cotizaciones/orden-compra` added after terrestres route, before `**` wildcard

## tarifas-selector CSS classes
- Section-label colors defined in `tarifas-selector.css`; add new button class there (e.g. `.btn.orden-compra`)
- CSS is minified single-line style

## ChangeDetectorRef usage
- Components using `subscribe()` call `this.cdr.detectChanges()` after state mutations
- Constructor injection (not `inject()`) is the pattern used in existing components
