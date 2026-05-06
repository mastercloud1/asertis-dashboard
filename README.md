# Dashboard Comercial · Asertis BPS

Dashboard de seguimiento comercial para Brenda Maria Luna Fontalvo.

## 🔄 Actualización automática

El dashboard se regenera automáticamente cada vez que se sube un archivo Excel actualizado.

## 🚀 Configuración inicial (solo una vez)

### 1. Crear repositorio en GitHub
1. Ve a [github.com](https://github.com) → **New repository**
2. Nombre: `asertis-dashboard`
3. Visibilidad: **Private** (los Excel quedan privados)
4. Clic en **Create repository**

### 2. Subir archivos
Sube todos estos archivos al repositorio:
- `generar_dashboard.py`
- `CRM_PowerBI_BrendaLuna_actualizado.xlsx`
- `Presupuesto_PowerBI_BrendaLuna.xlsx`
- `Logo_Asertis.png`
- `.github/workflows/actualizar_dashboard.yml`
- `README.md`

### 3. Activar GitHub Pages
1. Ve a **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `gh-pages` → `/root`
4. Clic en **Save**

### 4. Primera ejecución
1. Ve a la pestaña **Actions**
2. Clic en **Actualizar Dashboard** → **Run workflow**
3. Espera ~1 minuto

Tu dashboard quedará en:
```
https://TU_USUARIO.github.io/asertis-dashboard/
```

---

## 📤 Cómo actualizar los datos

Cada vez que exportes nuevos datos del CRM:

1. Ve a tu repositorio en GitHub
2. Clic en `CRM_PowerBI_BrendaLuna_actualizado.xlsx`
3. Clic en el ícono de lápiz ✏️ o sube el archivo nuevo
4. **Commit changes**

GitHub Actions detecta el cambio, ejecuta `generar_dashboard.py` y publica el nuevo HTML automáticamente en ~1 minuto.

---

## 📊 KPIs del dashboard

| KPI | Descripción | Meta |
|-----|-------------|------|
| Cumplimiento presupuesto | Ventas ganadas vs presupuesto del mes | 100% |
| Leads nuevos semanales | Oportunidades creadas en la semana | 3/semana |

---

*Asertis BPS · Una marca Fenalco Valle*
