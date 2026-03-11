
export default {
  bootstrap: () => import('./main.server.mjs').then(m => m.default),
  inlineCriticalCss: true,
  baseHref: '/',
  locale: undefined,
  routes: [
  {
    "renderMode": 1,
    "route": "/"
  },
  {
    "renderMode": 2,
    "route": "/login"
  },
  {
    "renderMode": 1,
    "route": "/change-password"
  },
  {
    "renderMode": 1,
    "route": "/tarifas"
  },
  {
    "renderMode": 1,
    "route": "/tarifas/list"
  },
  {
    "renderMode": 1,
    "route": "/tarifas/menu"
  },
  {
    "renderMode": 1,
    "route": "/tarifas/create"
  },
  {
    "renderMode": 1,
    "route": "/tarifas/edit/*"
  },
  {
    "renderMode": 1,
    "route": "/tarifas/view/*"
  },
  {
    "renderMode": 1,
    "preload": [
      "chunk-VJUBRNAZ.js"
    ],
    "route": "/tarifas/maritimo/create"
  },
  {
    "renderMode": 1,
    "redirectTo": "/login",
    "route": "/**"
  }
],
  entryPointToBrowserMapping: undefined,
  assets: {
    'index.csr.html': {size: 12112, hash: 'fb00207abec4c9053d79b79202a1969581834d1303e9366c2bdf0159d040e1ad', text: () => import('./assets-chunks/index_csr_html.mjs').then(m => m.default)},
    'index.server.html': {size: 12116, hash: '8b10864ae1774caa282d04dec50376fee19df2935acdbfb831e0ec4c912e899f', text: () => import('./assets-chunks/index_server_html.mjs').then(m => m.default)},
    'login/index.html': {size: 17105, hash: '860a6fcd16b1e1f280e36f38fbefeb5d7352bdff2a2d2df1838ffec00e2499ef', text: () => import('./assets-chunks/login_index_html.mjs').then(m => m.default)},
    'styles-25XO3FHF.css': {size: 384, hash: 'w2dzDxc5BT8', text: () => import('./assets-chunks/styles-25XO3FHF_css.mjs').then(m => m.default)}
  },
};
