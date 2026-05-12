"""
generar_dashboard.py
Lee CRM_PowerBI_BrendaLuna_actualizado.xlsx y Presupuesto_PowerBI_BrendaLuna.xlsx
y regenera index.html con los datos actualizados.
"""

import pandas as pd
import base64, os, json
from datetime import datetime

# ── Cargar datos ──────────────────────────────────────────────────────────────
crm  = pd.read_excel('CRM_PowerBI_BrendaLuna_actualizado.xlsx', sheet_name='CRM_Datos')
pres = pd.read_excel('Presupuesto_PowerBI_BrendaLuna.xlsx', sheet_name='Presupuesto')

def safe_date(s):
    try:
        if pd.isna(s): return None
        return pd.to_datetime(s)
    except:
        return None

crm['creado_dt'] = crm['Fecha_creacion'].apply(safe_date)
crm['cierre_dt'] = crm['Fecha_cierre'].apply(safe_date)

VENDEDOR   = 'Brenda Maria Luna Fontalvo'
HOY        = datetime.today()
MES_ACTUAL = HOY.month
ANO_ACTUAL = HOY.year
SEM_ACTUAL = int(HOY.isocalendar()[1])

brenda       = crm[crm['Vendedor'] == VENDEDOR].copy()
brenda['semana'] = brenda['creado_dt'].apply(lambda d: int(d.isocalendar()[1]) if d else None)
brenda['anio']   = brenda['creado_dt'].apply(lambda d: int(d.year) if d else None)

# ── KPI 1: Cumplimiento presupuesto ──────────────────────────────────────────
brenda_ganado = brenda[brenda['Etapa'] == 'Ganado']
mayo_ganado   = brenda_ganado[brenda_ganado['cierre_dt'].apply(
    lambda d: d is not None and d.month == MES_ACTUAL and d.year == ANO_ACTUAL)]
total_mayo    = int(mayo_ganado['Ingreso_esperado_COP'].sum())
total_ganado  = int(brenda_ganado['Ingreso_esperado_COP'].sum())

pres_mes = pres[(pres['Num_Mes'] == MES_ACTUAL) & (pres['Anio'] == ANO_ACTUAL)]['Presupuesto_COP'].sum()
pres_mes = int(pres_mes) if pres_mes > 0 else 56_000_000
cumplimiento  = round(total_mayo / pres_mes * 100, 1) if pres_mes > 0 else 0
faltan        = max(0, pres_mes - total_mayo)

# ── KPI 2: Leads semanales ───────────────────────────────────────────────────
sem_leads = brenda.groupby(['anio','semana'])['Oportunidad'].count().reset_index()
sem_leads.columns = ['anio','semana','leads']
leads_sem_actual = int(sem_leads[(sem_leads['semana']==SEM_ACTUAL)&(sem_leads['anio']==ANO_ACTUAL)]['leads'].sum())

# Histórico semanas (2025+2026)
semanas_hist = []
for _, row in sem_leads.iterrows():
    label = f"S{int(row['semana'])}" if int(row['anio'])==ANO_ACTUAL else f"S{int(row['semana'])}/{str(int(row['anio']))[2:]}"
    semanas_hist.append({'sem': label, 'n': int(row['leads']), 'actual': int(row['semana'])==SEM_ACTUAL and int(row['anio'])==ANO_ACTUAL})
# Ensure current week appears
if not any(s['actual'] for s in semanas_hist):
    semanas_hist.append({'sem': f'S{SEM_ACTUAL}', 'n': 0, 'actual': True})

semanas_cumplen = sum(1 for s in semanas_hist if s['n'] >= 3)
semanas_total   = len(semanas_hist)

# ── Funnel Brenda ────────────────────────────────────────────────────────────
funnel_counts = brenda['Etapa'].value_counts().to_dict()
funnel_order  = ['Nuevo','Contactado','Seguimiento','Propuesta','Negociación','Ganado','Perdido']
funnel_data   = [{'e': e, 'n': funnel_counts.get(e, 0)} for e in funnel_order]
pipeline      = int(brenda[~brenda['Etapa'].isin(['Perdido','Ganado'])]['Ingreso_esperado_COP'].sum())
conversion    = round(len(brenda_ganado)/len(brenda)*100, 1) if len(brenda) > 0 else 0
total_opps    = len(brenda)
perdidas      = funnel_counts.get('Perdido', 0)
activas       = total_opps - perdidas - len(brenda_ganado)

# ── Vendedores ───────────────────────────────────────────────────────────────
ganado_all = crm[crm['Etapa'] == 'Ganado']
vendors_raw = ganado_all.groupby('Vendedor')['Ingreso_esperado_COP'].sum().sort_values(ascending=False)
vendor_data = [{'name': v.split()[0]+' '+v.split()[1] if len(v.split())>1 else v,
                'val': int(vendors_raw[v])} for v in vendors_raw.index]

# ── Etapas globales ──────────────────────────────────────────────────────────
etapas_global = crm['Etapa'].value_counts().to_dict()
etapa_order   = ['Perdido','Ganado','Contactado','Propuesta','Seguimiento','Nuevo','Negociación']
etapa_labels  = [e for e in etapa_order if e in etapas_global]
etapa_vals    = [etapas_global.get(e,0) for e in etapa_labels]

# ── Presupuesto mensual ──────────────────────────────────────────────────────
meses_es = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
pres_mensual = []
for m in range(1, 13):
    p_val = pres[(pres['Num_Mes']==m)&(pres['Anio']==ANO_ACTUAL)]['Presupuesto_COP'].sum()
    r_val = int(brenda_ganado[brenda_ganado['cierre_dt'].apply(
        lambda d: d is not None and d.month==m and d.year==ANO_ACTUAL)]['Ingreso_esperado_COP'].sum())
    pres_mensual.append({'mes': meses_es[m-1], 'pres': round(float(p_val)/1e6,1), 'real': round(r_val/1e6,1), 'actual': m==MES_ACTUAL})

# ── Logo base64 ──────────────────────────────────────────────────────────────
logo_path = 'Logo_Asertis.png'
logo_b64  = ''
if os.path.exists(logo_path):
    with open(logo_path,'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode()

# ── Helpers de formato ────────────────────────────────────────────────────────
def fmt_cop(val):
    if val >= 1_000_000_000:
        return f'${val/1_000_000_000:.2f}B'
    elif val >= 1_000_000:
        return f'${val/1_000_000:.1f}M'
    return f'${val:,.0f}'

kpi1_val   = fmt_cop(total_mayo)
kpi1_badge_class = 'bd-green' if cumplimiento>=100 else ('bd-amber' if cumplimiento>=50 else 'bd-red')
kpi1_badge_text  = f'{cumplimiento}% · mes actual'
kpi1_color = '#16a34a' if cumplimiento>=100 else ('#ef4444' if cumplimiento>=50 else '#dc2626')
gauge1_pct = min(cumplimiento, 100)
gauge1_grad = '#16a34a,#22c55e' if cumplimiento>=100 else ('#ef4444,#f59e0b' if cumplimiento>=50 else '#dc2626,#ef4444')

kpi2_val   = leads_sem_actual
kpi2_badge_class = 'bd-green' if leads_sem_actual>=3 else ('bd-amber' if leads_sem_actual>=2 else 'bd-red')
kpi2_badge_text  = f'{leads_sem_actual} · sem {SEM_ACTUAL} {"✓" if leads_sem_actual>=3 else "✗"}'
kpi2_color = '#16a34a' if leads_sem_actual>=3 else ('#ef4444' if leads_sem_actual>=2 else '#dc2626')
gauge2_pct = min(leads_sem_actual/3*100, 100)
gauge2_grad = '#16a34a,#22c55e' if leads_sem_actual>=3 else ('#ef4444,#f59e0b' if leads_sem_actual>=2 else '#dc2626,#ef4444')

strip_cumpl_bar  = '#16a34a' if cumplimiento>=100 else ('#ef4444' if cumplimiento>=50 else '#dc2626')
strip_leads_bar  = '#16a34a' if leads_sem_actual>=3 else ('#ef4444' if leads_sem_actual>=2 else '#dc2626')

# ── Generar HTML ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Comercial · Brenda Maria Luna Fontalvo · Asertis BPS</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  :root {{
    --bg:#f4f5f7; --surface:#ffffff; --surface2:#f0f1f4;
    --border:rgba(0,0,0,0.08); --border2:rgba(0,0,0,0.15);
    --text:#111827; --muted:#6b7280; --muted2:#4b5563;
    --accent:#2563eb; --radius:12px; --radius-sm:7px;
  }}
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:16px;line-height:1.5;padding:36px 32px 64px}}
  .header{{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:36px;padding-bottom:28px;border-bottom:1px solid var(--border)}}
  .header-eyebrow{{font-family:'DM Mono',monospace;font-size:12px;letter-spacing:.12em;color:#2563eb;text-transform:uppercase;margin-bottom:8px}}
  .header-title{{font-size:32px;font-weight:600;letter-spacing:-.5px}}
  .header-sub{{font-size:15px;color:var(--muted2);margin-top:4px}}
  .header-date{{font-family:'DM Mono',monospace;font-size:13px;color:var(--muted);text-align:right;line-height:1.8}}
  .update-badge{{display:inline-block;background:#dcfce7;color:#15803d;font-size:11px;font-weight:500;padding:3px 10px;border-radius:20px;margin-top:6px}}
  .kpi-strip{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:22px}}
  .kpi-tile{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px 18px 16px;position:relative;overflow:hidden;transition:border-color .2s}}
  .kpi-tile:hover{{border-color:var(--border2)}}
  .kpi-tile::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent-bar,var(--accent));opacity:.6}}
  .kpi-lbl{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}}
  .kpi-val{{font-size:28px;font-weight:600;letter-spacing:-.5px;line-height:1;margin-bottom:6px}}
  .kpi-note{{font-size:13px;color:var(--muted2)}}
  .badge{{display:inline-block;font-size:12px;font-weight:500;padding:2px 8px;border-radius:20px;vertical-align:middle}}
  .bd-red{{background:#fee2e2;color:#b91c1c}} .bd-green{{background:#dcfce7;color:#15803d}} .bd-amber{{background:#fef3c7;color:#b45309}}
  .main-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px 24px;transition:border-color .2s}}
  .card:hover{{border-color:var(--border2)}}
  .card-title{{font-size:13px;font-weight:500;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin-bottom:20px;display:flex;align-items:center;justify-content:space-between}}
  .kpi-detail-big{{font-size:46px;font-weight:600;letter-spacing:-1px;line-height:1;margin-bottom:6px}}
  .kpi-detail-sub{{font-size:14px;color:var(--muted2);margin-bottom:16px}}
  .gauge-track{{background:rgba(0,0,0,.07);border-radius:4px;height:10px;overflow:hidden;margin-bottom:6px}}
  .gauge-fill{{height:10px;border-radius:4px}}
  .gauge-labels{{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);font-family:'DM Mono',monospace}}
  .divider{{height:1px;background:var(--border);margin:18px 0}}
  .sub-label{{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin-bottom:12px}}
  .legend-row{{display:flex;gap:16px;margin-bottom:12px}}
  .leg{{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted2)}}
  .leg-sq{{width:10px;height:10px;border-radius:2px;flex-shrink:0}}
  .bar-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
  .bar-lbl{{font-size:13px;color:var(--muted2);flex-shrink:0}}
  .bar-track{{flex:1;background:rgba(0,0,0,.06);border-radius:3px;height:9px;position:relative;overflow:visible}}
  .bar-fill{{height:9px;border-radius:3px;position:absolute;top:0;left:0}}
  .bar-meta{{position:absolute;top:-4px;bottom:-4px;width:2px;border-radius:1px;background:#dc2626;z-index:2}}
  .bar-val{{font-size:13px;font-weight:500;color:var(--text);flex-shrink:0;font-family:'DM Mono',monospace}}
  .pill{{display:inline-block;font-size:12px;font-weight:500;padding:3px 8px;border-radius:20px;flex-shrink:0}}
  .p-red{{background:#fee2e2;color:#b91c1c}} .p-green{{background:#dcfce7;color:#15803d}} .p-amber{{background:#fef3c7;color:#b45309}} .p-gray{{background:rgba(0,0,0,.06);color:var(--muted)}}
  .insight{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:var(--radius-sm);padding:12px 15px;margin-top:16px;font-size:13px;color:var(--muted2);line-height:1.6}}
  .insight strong{{color:var(--text);font-weight:500}}
  .chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .footer{{margin-top:36px;padding-top:22px;border-top:1px solid var(--border);display:flex;justify-content:space-between;font-size:13px;color:var(--muted);font-family:'DM Mono',monospace}}
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
  .kpi-tile,.card{{animation:fadeUp .4s ease both}}
  @media(max-width:900px){{.kpi-strip{{grid-template-columns:repeat(3,1fr)}}.main-grid,.chart-grid{{grid-template-columns:1fr}}}}
  @media(max-width:540px){{body{{padding:20px 16px 40px}}.kpi-strip{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    {"<img src='data:image/png;base64," + logo_b64 + "' alt='Asertis BPS' style='height:64px;width:auto;margin-bottom:14px;display:block;'>" if logo_b64 else ""}
    <div class="header-eyebrow">Dashboard Comercial</div>
    <div class="header-title">Brenda Maria Luna Fontalvo</div>
    <div class="header-sub">CRM · Seguimiento de ventas y leads {ANO_ACTUAL}</div>
  </div>
  <div class="header-date">
    Actualizado: {HOY.strftime('%d %b %Y %H:%M')}<br>
    Período: 2025 – {ANO_ACTUAL}<br>
    Fuente: Odoo CRM
    <br><span class="update-badge">🔄 Auto-actualizado</span>
  </div>
</div>

<div class="kpi-strip">
  <div class="kpi-tile" style="--accent-bar:#2563eb;">
    <div class="kpi-lbl">Ventas ganadas</div>
    <div class="kpi-val">{fmt_cop(total_ganado)}</div>
    <div class="kpi-note">COP · {len(brenda_ganado)} negocios cerrados</div>
  </div>
  <div class="kpi-tile" style="--accent-bar:{strip_cumpl_bar};">
    <div class="kpi-lbl">Cumplimiento mayo</div>
    <div class="kpi-val">{cumplimiento}% <span class="badge {kpi1_badge_class}">{'meta ✓' if cumplimiento>=100 else 'en curso' if cumplimiento>=50 else 'alerta'}</span></div>
    <div class="kpi-note">{fmt_cop(total_mayo)} de {fmt_cop(pres_mes)}</div>
  </div>
  <div class="kpi-tile" style="--accent-bar:#0d9488;">
    <div class="kpi-lbl">Pipeline activo</div>
    <div class="kpi-val">{fmt_cop(pipeline)}</div>
    <div class="kpi-note">COP · oportunidades abiertas</div>
  </div>
  <div class="kpi-tile" style="--accent-bar:{strip_leads_bar};">
    <div class="kpi-lbl">Leads nuevos sem {SEM_ACTUAL}</div>
    <div class="kpi-val">{leads_sem_actual} <span class="badge {kpi2_badge_class}">{'cumple ✓' if leads_sem_actual>=3 else 'meta 3'}</span></div>
    <div class="kpi-note">semana actual · meta 3/semana</div>
  </div>
  <div class="kpi-tile" style="--accent-bar:#ef4444;">
    <div class="kpi-lbl">Tasa de conversión</div>
    <div class="kpi-val">{conversion}%</div>
    <div class="kpi-note">{len(brenda_ganado)} ganados / {total_opps} oportunidades</div>
  </div>
  <div class="kpi-tile" style="--accent-bar:#6b7280;">
    <div class="kpi-lbl">Oportunidades totales</div>
    <div class="kpi-val">{total_opps}</div>
    <div class="kpi-note">{perdidas} perdidas · {activas} activas</div>
  </div>
</div>

<div class="main-grid">
  <div class="card">
    <div class="card-title">KPI 1 — Cumplimiento de presupuesto <span class="badge {kpi1_badge_class}">{kpi1_badge_text}</span></div>
    <div class="kpi-detail-big" style="color:{kpi1_color};">{kpi1_val}</div>
    <div class="kpi-detail-sub">de {fmt_cop(pres_mes)} COP presupuestados este mes</div>
    <div class="gauge-track"><div class="gauge-fill" style="width:{gauge1_pct}%;background:linear-gradient(90deg,{gauge1_grad});"></div></div>
    <div class="gauge-labels"><span>{fmt_cop(total_mayo)}</span><span>Meta: {fmt_cop(pres_mes)}</span><span>{cumplimiento}%</span></div>
    <div class="divider"></div>
    <div class="sub-label">Presupuesto vs real mensual {ANO_ACTUAL}</div>
    <div class="legend-row">
      <span class="leg"><span class="leg-sq" style="background:#2563eb;opacity:.35;"></span>Presupuesto</span>
      <span class="leg"><span class="leg-sq" style="background:#16a34a;"></span>Real ganado</span>
      <span class="leg"><span class="leg-sq" style="background:#2563eb;"></span>Mes actual</span>
    </div>
    <div id="pres-bars"></div>
    <div class="insight">
      <strong>{fmt_cop(total_mayo)} COP</strong> cerrados en mayo 2026.
      Cumplimiento del <strong>{cumplimiento}%</strong> sobre la meta de {fmt_cop(pres_mes)}.
      {'✅ Meta alcanzada.' if cumplimiento>=100 else f'Faltan <strong>{fmt_cop(faltan)}</strong> para completar el mes.'}
    </div>
  </div>

  <div class="card">
    <div class="card-title">KPI 2 — Leads nuevos semanales al CRM <span class="badge {kpi2_badge_class}">{kpi2_badge_text}</span></div>
    <div class="kpi-detail-big" style="color:{kpi2_color};">{kpi2_val}</div>
    <div class="kpi-detail-sub">leads nuevos esta semana · meta: 3 por semana</div>
    <div class="gauge-track"><div class="gauge-fill" style="width:{gauge2_pct:.1f}%;background:linear-gradient(90deg,{gauge2_grad});"></div></div>
    <div class="gauge-labels"><span>Sem {SEM_ACTUAL} actual</span><span>Meta: 3 leads</span><span>{'✓ cumple' if leads_sem_actual>=3 else ''}</span></div>
    <div class="divider"></div>
    <div class="sub-label">Histórico semanal 2025–{ANO_ACTUAL}</div>
    <div class="legend-row">
      <span class="leg"><span class="leg-sq" style="background:#2563eb;"></span>Leads nuevos</span>
      <span class="leg"><span class="leg-sq" style="width:4px;height:9px;border-radius:1px;background:#dc2626;"></span>Meta (3)</span>
    </div>
    <div id="week-bars"></div>
    <div class="insight">
      <strong>{semanas_cumplen} de {semanas_total} semanas</strong> han cumplido la meta de 3 leads.
      {'Semana ' + str(SEM_ACTUAL) + ' registra <strong>' + str(leads_sem_actual) + ' leads nuevos</strong> — ✅ cumple.' if leads_sem_actual>=3
       else 'Semana ' + str(SEM_ACTUAL) + ' con <strong>' + str(leads_sem_actual) + ' leads</strong> — aún sin cumplir la meta.'}
    </div>
  </div>
</div>

<div class="main-grid" style="margin-bottom:16px;">
  <div class="card">
    <div class="card-title">Embudo de ventas — Brenda Luna</div>
    <div id="funnel"></div>
  </div>
  <div class="card">
    <div class="card-title">Ventas ganadas por vendedor (COP)</div>
    <div id="vendors"></div>
  </div>
</div>

<div class="chart-grid">
  <div class="card">
    <div class="card-title">Presupuesto mensual {ANO_ACTUAL}</div>
    <div style="position:relative;width:100%;height:210px;"><canvas id="presChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">Distribución por etapa — equipo completo</div>
    <div style="display:flex;align-items:center;gap:20px;">
      <div style="position:relative;width:160px;height:160px;flex-shrink:0;"><canvas id="etapaChart"></canvas></div>
      <div id="etapa-legend" style="flex:1;"></div>
    </div>
  </div>
</div>

<div class="footer">
  <span>Asertis BPS · Dashboard Comercial · Brenda Maria Luna Fontalvo</span>
  <span>Generado: {HOY.strftime('%d/%m/%Y %H:%M')} · Datos: Odoo CRM</span>
</div>

<script>
const presData = {json.dumps(pres_mensual)};
const maxP = Math.max(...presData.map(d=>d.pres));
const presEl = document.getElementById('pres-bars');
presData.forEach(d=>{{
  const bgPct  = maxP>0?(d.pres/maxP*100).toFixed(1):0;
  const realPct= d.pres>0?(d.real/maxP*100).toFixed(1):0;
  const accent = d.actual?'#2563eb':'rgba(37,99,235,0.2)';
  const valLabel = d.pres>0?(d.real>0?`$${{d.real}}M / $${{d.pres}}M`:`$${{d.pres}}M`):'—';
  presEl.innerHTML+=`<div class="bar-row">
    <span class="bar-lbl" style="width:38px;font-family:'DM Mono',monospace;">${{d.mes}}${{d.actual?' ←':''}}</span>
    <div class="bar-track" style="opacity:${{d.pres===0?0.3:1}}">
      <div class="bar-fill" style="width:${{bgPct}}%;background:${{accent}};"></div>
      <div class="bar-fill" style="width:${{realPct}}%;background:#16a34a;"></div>
    </div>
    <span class="bar-val" style="width:90px;font-size:11px;">${{valLabel}}</span>
  </div>`;
}});

const weekData = {json.dumps(semanas_hist)};
const META=3;
const maxW=Math.max(...weekData.map(d=>d.n),META);
const weekEl=document.getElementById('week-bars');
weekData.forEach(d=>{{
  const pct=(d.n/maxW*100).toFixed(1);
  const metaPct=(META/maxW*100).toFixed(1);
  const fillColor=d.n>=META?'#2563eb':(d.n>=2?'#ef4444':'#d1d5db');
  const pc=d.n>=META?'p-green':(d.n>=2?'p-amber':(d.actual?'p-red':'p-gray'));
  const pt=d.n>=META?'cumple':(d.n>=2?'no cumple':(d.actual?'sin datos':'no cumple'));
  weekEl.innerHTML+=`<div class="bar-row">
    <span class="bar-lbl" style="width:62px;font-family:'DM Mono',monospace;">${{d.sem}}${{d.actual?' ←':''}}</span>
    <div class="bar-track">
      <div class="bar-fill" style="width:${{pct}}%;background:${{fillColor}};"></div>
      <div class="bar-meta" style="left:${{metaPct}}%;"></div>
    </div>
    <span class="bar-val" style="width:22px;">${{d.n}}</span>
    <span class="pill ${{pc}}">${{pt}}</span>
  </div>`;
}});

const funnelColors=['rgba(37,99,235,0.2)','rgba(37,99,235,0.35)','rgba(37,99,235,0.5)',
  'rgba(37,99,235,0.65)','rgba(37,99,235,0.85)','#16a34a','rgba(0,0,0,0.1)'];
const funnelData={json.dumps(funnel_data)};
const maxF=Math.max(...funnelData.map(d=>d.n));
const funnelEl=document.getElementById('funnel');
funnelData.forEach((d,i)=>{{
  const pct=(d.n/maxF*100).toFixed(1);
  funnelEl.innerHTML+=`<div class="bar-row">
    <span class="bar-lbl" style="width:86px;">${{d.e}}</span>
    <div class="bar-track"><div class="bar-fill" style="width:${{pct}}%;background:${{funnelColors[i]}};"></div></div>
    <span class="bar-val">${{d.n}}</span>
  </div>`;
}});

const vendorColors=['#2563eb','#0d9488','rgba(37,99,235,0.35)','rgba(37,99,235,0.25)'];
const vendorData={json.dumps(vendor_data)};
const maxV=Math.max(...vendorData.map(d=>d.val));
const vendorEl=document.getElementById('vendors');
vendorData.forEach((d,i)=>{{
  const pct=(d.val/maxV*100).toFixed(1);
  const fmt='$'+(d.val/1000000).toFixed(1)+'M';
  vendorEl.innerHTML+=`<div class="bar-row" style="margin-bottom:14px;">
    <span class="bar-lbl" style="width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{d.name}}</span>
    <div class="bar-track" style="height:9px;"><div class="bar-fill" style="width:${{pct}}%;background:${{vendorColors[i]}};height:9px;"></div></div>
    <span class="bar-val" style="width:80px;">${{fmt}}</span>
  </div>`;
}});

new Chart(document.getElementById('presChart'),{{
  type:'bar',
  data:{{
    labels:{json.dumps([m['mes'] for m in pres_mensual])},
    datasets:[{{
      data:{json.dumps([m['pres'] for m in pres_mensual])},
      backgroundColor:{json.dumps(['#2563eb' if m['actual'] else ('rgba(0,0,0,0.06)' if m['pres']==0 else 'rgba(37,99,235,0.35)') for m in pres_mensual])},
      borderWidth:0,borderRadius:4
    }}]
  }},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#fff',borderColor:'rgba(0,0,0,0.12)',borderWidth:1,
      titleColor:'#6b7280',bodyColor:'#111827',
      callbacks:{{label:ctx=>ctx.parsed.y>0?'$'+ctx.parsed.y+'M COP':'Sin presupuesto'}}}}}},
    scales:{{y:{{ticks:{{callback:v=>v>0?'$'+v+'M':'',color:'#6b7280',font:{{size:12,family:'DM Mono'}}}},
      grid:{{color:'rgba(0,0,0,0.05)'}},border:{{display:false}}}},
      x:{{ticks:{{color:'#6b7280',font:{{size:12}},autoSkip:false,maxRotation:0}},grid:{{display:false}},border:{{display:false}}}}}}}}
}});

const etapaColors=['rgba(0,0,0,0.1)','#16a34a','#2563eb','rgba(37,99,235,0.35)','#0d9488','rgba(37,99,235,0.6)','#ef4444'];
const etapaLabels={json.dumps(etapa_labels)};
const etapaVals={json.dumps(etapa_vals)};
new Chart(document.getElementById('etapaChart'),{{
  type:'doughnut',
  data:{{labels:etapaLabels,datasets:[{{data:etapaVals,backgroundColor:etapaColors,borderWidth:2,borderColor:'#fff'}}]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#fff',borderColor:'rgba(0,0,0,0.12)',borderWidth:1,titleColor:'#6b7280',bodyColor:'#111827'}}}},
    cutout:'62%'}}
}});
const total={sum(etapa_vals)};
const legendEl=document.getElementById('etapa-legend');
etapaLabels.forEach((l,i)=>{{
  const pct=Math.round(etapaVals[i]/total*100);
  legendEl.innerHTML+=`<div style="display:flex;align-items:center;gap:9px;margin-bottom:9px;">
    <span style="width:10px;height:10px;border-radius:50%;background:${{etapaColors[i]}};flex-shrink:0;"></span>
    <span style="font-size:13px;color:#4b5563;flex:1;">${{l}}</span>
    <span style="font-family:'DM Mono',monospace;font-size:13px;color:#111827;">${{etapaVals[i]}}</span>
    <span style="font-size:12px;color:#6b7280;width:34px;text-align:right;">${{pct}}%</span>
  </div>`;
}});
</script>
</body>
</html>"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Dashboard generado: {HOY.strftime('%d/%m/%Y %H:%M')}")
print(f"   KPI1: {fmt_cop(total_mayo)} / {fmt_cop(pres_mes)} = {cumplimiento}%")
print(f"   KPI2: {leads_sem_actual} leads sem {SEM_ACTUAL}")
print(f"   Vendedores: {len(vendor_data)} | Etapas: {len(etapa_labels)}")
