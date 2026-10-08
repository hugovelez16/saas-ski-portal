// Graba el video de presentacion recorriendo la app con datos de ./bin/seed-demo.
// Uso: BASE_URL=http://localhost:8322 npm run grabar   (desde scripts/demo)
// Genera videos/demo-presentacion.webm y videos/demo-presentacion.zoom.json
// (eventos de zoom que consume editar-zoom.mjs).
import { chromium } from 'playwright';
import { mkdirSync, renameSync, writeFileSync } from 'node:fs';

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:8080';
const EMAIL = process.env.DEMO_MANAGER_EMAIL ?? 'demo@nievesur.es';
const PASSWORD = process.env.DEMO_PASSWORD ?? 'Demo2026!';
const OUT_DIR = process.env.OUT_DIR ?? 'videos';
const SIZE = { width: 1920, height: 1080 };

const pausa = (page, ms) => page.waitForTimeout(ms);
const rand = (a, b) => a + Math.random() * (b - a);
const suavizar = (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2); // ease in-out

// Cursor rojo visible en el video
const CURSOR_SCRIPT = `
  window.addEventListener('DOMContentLoaded', () => {
    const c = document.createElement('div');
    c.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;border-radius:50%;'
      + 'background:rgba(220,38,38,.55);border:2px solid #fff;pointer-events:none;'
      + 'transform:translate(-50%,-50%);left:-50px;top:-50px';
    document.body.appendChild(c);
    document.addEventListener('mousemove', (e) => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });

    // Marcador de sincronia: 4x4 px magenta en la esquina mientras haya algun dialogo abierto.
    // editar-zoom.mjs lo detecta en el video para colocar los zooms con exactitud.
    const m = document.createElement('div');
    m.style.cssText = 'position:fixed;z-index:2147483647;left:0;top:0;width:4px;height:4px;pointer-events:none;background:transparent';
    document.body.appendChild(m);
    const actualizar = () => {
      const abierto = !!document.querySelector('[role="dialog"][data-state="open"]');
      m.style.background = abierto ? '#ff00ff' : 'transparent';
    };
    new MutationObserver(actualizar).observe(document.documentElement, {
      subtree: true, childList: true, attributes: true, attributeFilter: ['data-state'],
    });
  });
`;

// El entorno dev hace auto-login como admin; se desactiva para que entre el usuario demo.
const sinBypass = (ctx) =>
  ctx.route('**/api/auth/dev-status', (route) =>
    route.fulfill({ json: { dev_bypass: false, email: null } }),
  );

// --- Linea de tiempo de zoom (ms desde el inicio del video) ---
let t0 = 0;
const zoomEventos = [];
const ahora = () => Date.now() - t0;

async function zoomA(locator, maxZoom = 1.6) {
  const box = await locator.boundingBox();
  if (!box) return;
  const z = Math.min(maxZoom, (SIZE.height * 0.92) / box.height);
  zoomEventos.push({
    tipo: 'in',
    t: ahora(),
    cx: Math.round(box.x + box.width / 2),
    cy: Math.round(box.y + box.height / 2),
    z: Number(z.toFixed(2)),
  });
}
const zoomFuera = () => zoomEventos.push({ tipo: 'out', t: ahora() });

// --- Movimiento suave, calculado por tiempo (independiente de la latencia de cada paso) ---
let cursor = { x: 960, y: 540 };

async function moverSuave(page, x, y, ms = 650) {
  const { x: x0, y: y0 } = cursor;
  const inicio = performance.now();
  for (;;) {
    const p = Math.min(1, (performance.now() - inicio) / ms);
    const e = suavizar(p);
    await page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e);
    if (p >= 1) break;
    await pausa(page, 8);
  }
  cursor = { x, y };
}

// Espera sin quedarse quieto: el cursor deriva lentamente por la zona
async function vagar(page, ms) {
  const fin = performance.now() + ms;
  while (performance.now() < fin) {
    const restante = fin - performance.now();
    const dur = Math.min(restante, rand(700, 1100));
    await moverSuave(
      page,
      Math.min(1800, Math.max(60, cursor.x + rand(-90, 90))),
      Math.min(1000, Math.max(60, cursor.y + rand(-60, 60))),
      dur,
    );
  }
}

// Scroll con rueda a velocidad suave y constante-ish (ease in-out), en px totales durante ms
async function scrollSuave(page, total, ms) {
  if (cursor.x < 400) await moverSuave(page, 1100, cursor.y, 500);
  const inicio = performance.now();
  let enviado = 0;
  for (;;) {
    const p = Math.min(1, (performance.now() - inicio) / ms);
    const objetivo = Math.round(total * suavizar(p));
    const delta = objetivo - enviado;
    if (delta !== 0) {
      await page.mouse.wheel(0, delta);
      enviado = objetivo;
    }
    if (p >= 1) break;
    await pausa(page, 16);
  }
}

// Baja y vuelve a subir, moviendo el cursor por el contenido mientras tanto
async function recorrer(page, { bajada = 900, msBajada = 3800, msSubida = 2800 } = {}) {
  await moverSuave(page, rand(900, 1500), rand(350, 650), 700);
  await Promise.all([scrollSuave(page, bajada, msBajada), vagar(page, msBajada)]);
  await Promise.all([scrollSuave(page, -bajada, msSubida), vagar(page, msSubida)]);
}

async function centro(locator) {
  const box = await locator.boundingBox();
  return box ? [box.x + box.width / 2, box.y + box.height / 2] : [960, 540];
}

async function clic(page, locator) {
  const box = await locator.boundingBox();
  if (box) await moverSuave(page, box.x + box.width / 2, box.y + box.height / 2);
  await locator.click();
}

// Navega con clic en el menu (conserva la empresa seleccionada, a diferencia de page.goto)
async function irA(page, texto) {
  await clic(page, page.getByRole('link', { name: texto, exact: true }));
  await page.waitForLoadState('networkidle');
}

async function login(page, tecleo) {
  await page.goto(`${BASE_URL}/login`);
  if (tecleo) await vagar(page, 1500);
  else await pausa(page, 300);
  const email = page.locator('#email');
  const clave = page.locator('#password');
  if (tecleo) await moverSuave(page, ...(await centro(email)), 900);
  await email.click();
  await email.pressSequentially(EMAIL, { delay: tecleo ? 95 : 0 });
  if (tecleo) await moverSuave(page, ...(await centro(clave)), 700);
  await clave.click();
  await clave.pressSequentially(PASSWORD, { delay: tecleo ? 95 : 0 });
  if (tecleo) await vagar(page, 900);
  else await pausa(page, 100);
  await page.keyboard.press('Enter');
  await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 30000 });
}

// Abre "Anadir Registro", lo rellena con zoom al dialogo y lo guarda
async function anadirRegistro(page, { usuario, tipo, inicio, fin, descripcion }) {
  await clic(page, page.getByRole('button', { name: /Añadir Registro/ }).first());
  const dialogo = page.getByRole('dialog');
  await dialogo.waitFor();
  await vagar(page, 450); // animacion de apertura
  await zoomA(dialogo);
  await vagar(page, 600);

  await clic(page, dialogo.getByLabel(usuario, { exact: false }).first());
  await vagar(page, 300);
  await clic(page, dialogo.getByLabel(tipo, { exact: true }));
  await vagar(page, 300);
  await clic(page, dialogo.getByRole('button', { name: /Elige una fecha/ }));
  const hoy = String(new Date().getDate());
  const dia = page
    .locator('[role="gridcell"] [role="button"]:not([data-outside-month])')
    .getByText(new RegExp(`^${hoy}$`));
  await dia.first().waitFor();
  await vagar(page, 450);
  await clic(page, dia.first());
  await vagar(page, 300);
  await clic(page, dialogo.locator('#startTime'));
  await dialogo.locator('#startTime').fill(inicio);
  await clic(page, dialogo.locator('#endTime'));
  await dialogo.locator('#endTime').fill(fin);
  await clic(page, dialogo.locator('#description'));
  await dialogo.locator('#description').pressSequentially(descripcion, { delay: 30 });
  await vagar(page, 400);

  await clic(page, dialogo.getByRole('button', { name: 'Guardar' }));
  await dialogo.waitFor({ state: 'hidden', timeout: 15000 });
  zoomFuera();
  await vagar(page, 800);
}

// Abre el detalle de una fila de la tabla, lo deja leer, hace scroll dentro y lo cierra
async function verDetalleFila(page, textoFila) {
  await clic(page, page.locator('tbody tr', { hasText: textoFila }).first());
  const dialogo = page.getByRole('dialog');
  await dialogo.waitFor();
  await vagar(page, 350);
  await zoomA(dialogo, 1.45);
  const box = await dialogo.boundingBox();
  if (box) await moverSuave(page, box.x + box.width / 2, box.y + box.height / 2, 700);
  await Promise.all([scrollSuave(page, 320, 1600), vagar(page, 1600)]);
  await vagar(page, 500); // lectura del desglose, con el cursor en movimiento
  await Promise.all([scrollSuave(page, -320, 800), vagar(page, 800)]);
  await page.keyboard.press('Escape');
  await dialogo.waitFor({ state: 'hidden', timeout: 10000 });
  zoomFuera();
  await vagar(page, 500);
}

// --- Secuencia ---
const TOUR_CALENTAMIENTO = ['Dashboard', 'Calendario', 'Turnos', 'Usuarios', 'Facturación'];

mkdirSync(OUT_DIR, { recursive: true });
const browser = await chromium.launch({ headless: true });

// Calentamiento sin video: compila las rutas de Next dev y evita el aviso "Compiling"
{
  const warm = await browser.newContext({ viewport: SIZE });
  await sinBypass(warm);
  const wp = await warm.newPage();
  await login(wp, false);
  for (const link of TOUR_CALENTAMIENTO) await irA(wp, link);
  await clic(wp, wp.locator('tbody tr').first()); // compila la ficha de usuario
  await wp.waitForLoadState('networkidle');
  await warm.close();
}
cursor = { x: 960, y: 540 };

const context = await browser.newContext({
  viewport: SIZE,
  recordVideo: { dir: OUT_DIR, size: SIZE },
  locale: 'es-ES',
  timezoneId: 'Europe/Madrid',
});
await sinBypass(context);
await context.addInitScript(CURSOR_SCRIPT);
const page = await context.newPage();
t0 = Date.now();

// 1. Login
await moverSuave(page, 960, 400, 500);
await login(page, true);
await vagar(page, 400);

// 2. Dashboard: baja para ver lo que cambia con los filtros y los pulsa; despues alta de registro
await irA(page, 'Dashboard');
await Promise.all([scrollSuave(page, 430, 2200), vagar(page, 2200)]);
for (const periodo of ['Esta Semana', 'Temporada', 'Hoy', 'Este Mes']) {
  await clic(page, page.getByText(periodo, { exact: true }).first());
  await vagar(page, 1500);
}
await Promise.all([scrollSuave(page, 450, 2400), vagar(page, 2400)]);
await Promise.all([scrollSuave(page, -880, 2600), vagar(page, 2600)]);
await anadirRegistro(page, {
  usuario: 'Javier Molina Cano',
  tipo: 'Clase Particular',
  inicio: '10:00',
  fin: '12:00',
  descripcion: 'Clase privada, nivel intermedio',
});

// 3. Calendario y alta de un segundo registro
await irA(page, 'Calendario');
await moverSuave(page, 1300, 520, 900);
await vagar(page, 1100);
await anadirRegistro(page, {
  usuario: 'Lucia Ferrer Bosch',
  tipo: 'Clase Colectiva',
  inicio: '15:00',
  fin: '17:00',
  descripcion: 'Grupo infantil, iniciacion',
});

// 4. Turnos: detalle de dos registros de distinto tipo (calculo del pago)
await irA(page, 'Turnos');
await vagar(page, 700);
await verDetalleFila(page, 'Particular');
await verDetalleFila(page, 'Colectiva');
await recorrer(page, { bajada: 500, msBajada: 2400, msSubida: 1600 });

// 5. Usuarios: ficha de un usuario con su configuracion de horas y tarifas
await irA(page, 'Usuarios');
await vagar(page, 600);
await clic(page, page.locator('tbody tr', { hasText: 'Javier Molina Cano' }).first());
await page.waitForLoadState('networkidle');
await vagar(page, 700);
await Promise.all([scrollSuave(page, 450, 2200), vagar(page, 2200)]); // resumen del usuario
await Promise.all([scrollSuave(page, -450, 1400), vagar(page, 1400)]);
await clic(page, page.getByRole('button', { name: 'Rates', exact: true })); // tarifas por turno y ajustes
await vagar(page, 900);
await Promise.all([scrollSuave(page, 1300, 6000), vagar(page, 6000)]);
await Promise.all([scrollSuave(page, -1300, 2500), vagar(page, 2500)]);

// 6. Facturacion
await irA(page, 'Facturación');
await recorrer(page, { bajada: 500, msBajada: 2600, msSubida: 1800 });
await vagar(page, 500);

const totalMs = ahora();
const videoPath = await page.video().path();
await context.close(); // escribe el fichero de video
await browser.close();

const final = `${OUT_DIR}/demo-presentacion.webm`;
renameSync(videoPath, final);
writeFileSync(`${OUT_DIR}/demo-presentacion.zoom.json`, JSON.stringify({ totalMs, eventos: zoomEventos }, null, 2));
console.log(`OK video en ${final}, ${zoomEventos.length} eventos de zoom en demo-presentacion.zoom.json`);
