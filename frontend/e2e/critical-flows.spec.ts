import { expect, test, Page, APIRequestContext } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const password = 'DataPulse2026!';
const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

async function login(page: Page, role = 'analista') {
  await page.goto('/login');
  await page.getByLabel('Correo electrónico').fill(role.includes('@') ? role : `${role}@datapulse.com`);
  await page.getByLabel('Contraseña', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Ingresar a DataPulse' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function apiLogin(request: APIRequestContext, role: string) {
  const response = await request.post('/api/auth/login/', {
    data: { email: role.includes('@') ? role : `${role}@datapulse.com`, password },
  });
  expect(response.status()).toBe(200);
  return { Authorization: `Bearer ${(await response.json()).access}` };
}

test('analyst creates, validates, edits and exports a portfolio through the real API', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page);
  const menu = page.getByRole('button', { name: 'Abrir navegación', exact: true });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole('link', { name: 'Mis portafolios', exact: true }).click();
  await page.getByRole('link', { name: 'Crear portafolio' }).click();
  const name = `E2E ${info.project.name} ${Date.now()}`;
  await page.getByLabel('Nombre del portafolio').fill(name);
  await page.getByLabel('Descripción').fill('Portafolio aislado de prueba de navegador.');
  await page.getByRole('button', { name: 'Guardar portafolio' }).click();
  await expect(page).toHaveURL(/\/portafolios\/\d+$/);
  await page.getByRole('button', { name: 'Agregar posición' }).click();
  let dialog = page.getByRole('dialog');
  await dialog.getByLabel('Buscar país').fill('Colombia');
  await page.getByRole('option', { name: /Colombia/ }).click();
  await dialog.getByLabel('Fecha de entrada').fill(yesterday);
  await dialog.getByLabel('Monto de inversión USD').fill('999.99');
  await expect(dialog.getByRole('button', { name: 'Aplicar posición' })).toBeDisabled();
  await dialog.getByLabel('Monto de inversión USD').fill('1,234.56');
  await expect(dialog.getByLabel('Monto de inversión USD')).toHaveValue('1,234.56');
  const created = page.waitForResponse(r => r.request().method() === 'POST' && /\/posiciones\/$/.test(r.url()));
  await dialog.getByRole('button', { name: 'Aplicar posición' }).click();
  const position = await created;
  expect(position.status()).toBe(201);
  expect((await position.json()).monto_inversion_usd).toBe('1234.56');
  const row = page.getByRole('row').filter({ hasText: 'Colombia' });
  await expect(row).toContainText('1.234,56');
  await row.getByRole('button', { name: 'Editar', exact: true }).click();
  dialog = page.getByRole('dialog');
  await expect(dialog.getByLabel('Buscar país')).toBeFocused();
  await dialog.getByLabel('Monto de inversión USD').fill('');
  await dialog.getByLabel('Monto de inversión USD').pressSequentially('2345.67');
  await expect(dialog.getByLabel('Monto de inversión USD')).toHaveValue('2,345.67');
  const updated = page.waitForResponse(r => r.request().method() === 'PUT' && /\/posiciones\/\d+\/$/.test(r.url()));
  await dialog.getByRole('button', { name: 'Aplicar posición' }).click();
  expect((await updated).status()).toBe(200);
  await expect(row).toContainText('2.345,67');
  const downloading = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar PDF' }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  const bytes = await readFile((await download.path())!);
  expect(bytes.subarray(0, 5).toString()).toBe('%PDF-');
  expect(bytes.length).toBeGreaterThan(200);
  await expect(page.locator('app-data-chart[kind="pie"] canvas')).toBeVisible();
  await expect(page.locator('app-data-chart[kind="doughnut"] canvas')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await page.getByRole('button', { name: 'Eliminar portafolio', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Eliminar', exact: true }).click();
  await expect(page).toHaveURL(/\/portafolios$/);
});

test('stale edits show a conflict and require an explicit reviewed resubmission', async ({ page, request }, info) => {
  const analyst = await apiLogin(request, 'analista');
  const admin = await apiLogin(request, 'admin');
  const created = await request.post('/api/portafolios/', {
    headers: analyst, data: { nombre: `Conflicto ${info.project.name} ${Date.now()}`, descripcion: '', es_publico: true },
  });
  expect(created.status()).toBe(201);
  const portfolio = await created.json();
  const path = `/api/portafolios/${portfolio.id}/`;
  try {
    await login(page);
    await page.goto(`/portafolios/${portfolio.id}/editar`);
    await expect(page.getByLabel('Nombre del portafolio')).toHaveValue(portfolio.nombre);
    const external = await request.put(path, { headers: admin, data: {
      nombre: portfolio.nombre, descripcion: 'Cambio externo', es_publico: true, version: portfolio.version,
    } });
    expect(external.status()).toBe(200);
    await page.getByLabel('Descripción').fill('Borrador local');
    const conflicting = page.waitForResponse(r => r.request().method() === 'PUT' && r.url().endsWith(path));
    await page.getByRole('button', { name: 'Guardar portafolio' }).click();
    expect((await conflicting).status()).toBe(409);
    await expect(page.getByText('Otro cambio actualizó este portafolio.', { exact: false })).toBeVisible();
    await expect(page.getByLabel('Descripción')).toHaveValue('Cambio externo');
    const persisted = await request.get(path, { headers: analyst });
    expect((await persisted.json()).descripcion).toBe('Cambio externo');
    await page.getByLabel('Descripción').fill('Revisado después del conflicto');
    await page.getByRole('button', { name: 'Guardar portafolio' }).click();
    await expect(page).toHaveURL(new RegExp(`/portafolios/${portfolio.id}$`));
    await expect(page.getByText('Revisado después del conflicto', { exact: true })).toBeVisible();
  } finally {
    const current = await request.get(path, { headers: analyst });
    if (current.ok()) await request.delete(path, { headers: {
      ...analyst, 'If-Match': `"${(await current.json()).version}"`,
    } });
  }
});

test('viewer cannot write and country flags work under production CSP on both viewports', async ({ page, request }, info) => {
  await login(page, 'viewer');
  await expect(page.locator('.ranking table').getByRole('columnheader')).toHaveText([
    'País', 'IRPC', 'Nivel', 'Variación', 'Tendencia',
  ]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.goto('/portafolios');
  await expect(page.getByRole('link', { name: 'Crear portafolio' })).toHaveCount(0);
  const viewer = await apiLogin(request, 'viewer');
  expect((await request.post('/api/portafolios/', { headers: viewer, data: {} })).status()).toBe(403);
  await page.goto('/portafolios/nuevo');
  await expect(page).toHaveURL(/\/sin-permiso$/);
  await expect(page.getByRole('heading', { name: 'Este espacio requiere otros permisos' })).toBeVisible();
  await page.goto('/paises/CO');
  const flag = page.getByRole('img', { name: 'Bandera de Colombia', exact: true });
  await expect(flag).toBeVisible();
  await expect.poll(() => flag.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  expect(new URL((await flag.getAttribute('src'))!, page.url()).origin).toBe(new URL(page.url()).origin);
  await expect(page.locator('app-data-chart canvas')).toHaveCount(2);
  await expect(page.locator('app-risk-quality')).toContainText('Calidad de datos: requiere revisión');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('country.png'), fullPage: true });
});

test('admin submits a durable background sync and sees partial provider results after reloading', async ({ page }) => {
  await login(page, 'admin');
  const accepted = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/paises/sync-indicadores/'));
  await page.getByRole('button', { name: 'Sincronizar indicadores', exact: true }).click();
  const response = await accepted;
  expect(response.status()).toBe(202);
  const job = await response.json();
  expect(job.estado).toBe('PENDIENTE');
  await page.reload();
  await expect(page.getByText('Ejecución ' + job.id, { exact: false })).toBeVisible();
  await expect(page.getByText('Sincronización: PARCIAL', { exact: true })).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('No se pudieron actualizar los datos;', { exact: false }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sincronizar indicadores', exact: true })).toBeEnabled();
});

test('admin validates names against the foreign portfolio owner before saving', async ({ page, request }, info) => {
  const analyst = await apiLogin(request, 'analista');
  const admin = await apiLogin(request, 'admin');
  const unique = `${info.project.name} ${Date.now()}`;
  const created: { id: number; auth: Record<string, string> }[] = [];
  const create = async (auth: Record<string, string>, nombre: string) => {
    const response = await request.post('/api/portafolios/', { headers: auth, data: { nombre, descripcion: '', es_publico: false } });
    expect(response.status()).toBe(201);
    const item = await response.json();
    created.push({ id: item.id, auth });
    return item;
  };
  try {
    const target = await create(analyst, `Edit ${unique}`);
    const reserved = await create(analyst, `Owner ${unique}`);
    const adminOnly = await create(admin, `Admin ${unique}`);
    await login(page, 'admin');
    await page.goto(`/portafolios/${target.id}/editar`);
    const name = page.getByLabel('Nombre del portafolio');
    await expect(name).toHaveValue(target.nombre);
    await name.fill(reserved.nombre);
    await name.blur();
    await expect(page.getByText('El propietario ya tiene un portafolio con este nombre.', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Guardar portafolio' })).toBeDisabled();
    await name.fill(adminOnly.nombre);
    await expect(page.getByRole('button', { name: 'Guardar portafolio' })).toBeEnabled();
    await page.getByRole('button', { name: 'Guardar portafolio' }).click();
    await expect(page).toHaveURL(new RegExp(`/portafolios/${target.id}$`));
    expect((await (await request.get(`/api/portafolios/${target.id}/`, { headers: analyst })).json()).nombre).toBe(adminOnly.nombre);
  } finally {
    for (const item of created) {
      const current = await request.get(`/api/portafolios/${item.id}/`, { headers: item.auth });
      if (current.ok()) await request.delete(`/api/portafolios/${item.id}/`, {
        headers: { ...item.auth, 'If-Match': `"${(await current.json()).version}"` },
      });
    }
  }
});

test('registration reaches dashboard and irrecoverably expired JWTs return to login', async ({ page, request }, info) => {
  await page.goto('/registro');
  await page.getByLabel('Nombre completo').fill('Usuario E2E');
  await page.getByLabel('Correo electrónico').fill(`registered-${info.project.name}-${Date.now()}@example.test`);
  await page.getByLabel('Contraseña', { exact: true }).fill('Unique-E2E-2026!');
  const signedIn = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/auth/login/'), { timeout: 30000 });
  await page.getByRole('button', { name: 'Crear cuenta', exact: false }).click();
  expect((await signedIn).status()).toBe(200);
  await expect(page).toHaveURL(/\/dashboard$/);
  const tokens = await (await request.get('/fixture/expired-session')).json();
  await page.evaluate(values => {
    localStorage.setItem('datapulse.auth.access', values.access);
    localStorage.setItem('datapulse.auth.refresh', values.refresh);
  }, tokens);
  await page.reload();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByText('Tu sesión venció. Inicia sesión de nuevo.', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('datapulse.auth.access'))).toBeNull();
});

test('alert filters and individual/global read state persist through the real API', async ({ page, request }) => {
  const email = `alerts-${Date.now()}@example.test`;
  const registration = await request.post('/api/auth/register/', { data: { email, password, nombre_completo: 'Alertas E2E' } });
  expect(registration.status()).toBe(201);
  await login(page, email);
  const auth = await apiLogin(request, email);
  await page.goto('/alertas');
  await page.getByLabel('Tipo de alerta', { exact: true }).click();
  await page.getByRole('option', { name: 'Indicador', exact: true }).click();
  await page.getByLabel('Severidad', { exact: true }).click();
  const filtered = page.waitForResponse(r => {
    const url = new URL(r.url());
    return url.pathname === '/api/alertas/' && url.searchParams.get('tipo') === 'INDICADOR' &&
      url.searchParams.get('severidad') === 'CRITICAL';
  });
  await page.getByRole('option', { name: 'Crítica', exact: true }).click();
  const response = await filtered;
  expect(response.status()).toBe(200);
  const records = (await response.json()).results;
  expect(records.length).toBeGreaterThan(0);
  const alerts = page.locator('.alert-row');
  const row = alerts.filter({ has: page.getByRole('heading', { name: records[0].titulo, exact: true }) }).first();
  await expect(row).toBeVisible();
  const reading = page.waitForResponse(r => r.request().method() === 'PUT' && r.url().endsWith(`/alertas/${records[0].id}/leer/`));
  await row.getByRole('button', { name: 'Marcar leída', exact: true }).click();
  expect((await reading).status()).toBe(200);
  await expect(row.getByRole('button', { name: 'Leída', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Marcar todas como leídas', exact: true }).click();
  await expect.poll(async () => (await (await request.get('/api/alertas/resumen/', { headers: auth })).json()).no_leidas).toBe(0);
});

test('total provider outage produces a persisted failure without breaking the dashboard', async ({ page, request }) => {
  await request.post('/fixture/provider-mode?unavailable');
  try {
    await login(page, 'admin');
    await page.getByRole('button', { name: 'Sincronizar indicadores', exact: true }).click();
    await expect(page.getByText('Sincronización: FALLIDA', { exact: true })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('heading', { name: 'Ranking regional', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sincronizar indicadores', exact: true })).toBeEnabled();
    expect((await request.get('/api/ready/')).status()).toBe(200);
  } finally {
    await request.post('/fixture/provider-mode');
  }
});
