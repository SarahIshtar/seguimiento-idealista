"""Prioridad 3 – Estacionalidad (parte 1: precio del alquiler en Madrid).

Pregunta: ¿la subida del €/m² de alquiler en Madrid entre el 6-oct y principios de nov de 2026
es mayor de lo que suele subir el precio en otoño?

Fuente histórica: hoja 'Estadísticas' del Excel (informe mensual de Idealista, Madrid municipio).
Ojo:
- El informe mensual NO es lo mismo que la media de los anuncios que recogemos a diario:
  comparamos ritmos de cambio, no niveles de precio.
- El informe redondea a 0,1 €/m² (~0,4 % a 23 €/m²), así que los cambios mensuales
  pequeños salen "a saltos" (0 %, 0,4 %, 0,9 %...).
- Correspondencia aproximada de periodos: el informe de cada mes refleja los anuncios de
  ese mes, así que nuestro periodo (6-oct -> principios de nov) se parece sobre todo
  al cambio septiembre -> octubre (y, en parte, octubre -> noviembre).
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
pd.set_option("display.width", 200)

# --- 1. Serie histórica mensual de Madrid -----------------------------------
est = pd.read_excel(CARPETA / "Seguimiento Idealista.xlsx", sheet_name="Estadísticas", parse_dates=["Mes"])

# "23,4 €/m2" -> 23.4  (el número tiene que empezar por una cifra; lo que no encaje queda vacío)
est["precio"] = pd.to_numeric(
    est["Precio m2"].astype(str)
    .str.extract(r"(\d+(?:[.,]\d+)?)")[0]
    .str.replace(",", "."),
    errors="coerce",
)

no_convertidas = est[est["precio"].isna()]
if len(no_convertidas):
    print(f"--- {len(no_convertidas)} filas sin precio válido (se ignoran) ---")
    print(no_convertidas[["Mes", "Precio m2"]])

serie = est.set_index("Mes")["precio"].sort_index()

# Cambio mensual (%) calculado por nosotros: las columnas de variación del Excel mezclan formatos
# fill_method=None: si falta un mes, el cambio de ese mes y el siguiente queda vacío (no se inventa)
cambio_mensual = serie.pct_change(fill_method=None) * 100

print("--- Serie histórica ---")
print(f"Desde {serie.index.min():%Y-%m} hasta {serie.index.max():%Y-%m} ({len(serie)} meses)")

# --- 2. Cambio de septiembre a octubre y de octubre a noviembre, por año -----
tabla = pd.DataFrame({
    "sep": serie[serie.index.month == 9].set_axis(serie[serie.index.month == 9].index.year),
    "oct": serie[serie.index.month == 10].set_axis(serie[serie.index.month == 10].index.year),
    "nov": serie[serie.index.month == 11].set_axis(serie[serie.index.month == 11].index.year),
})
tabla["sep->oct_%"] = (tabla["oct"] / tabla["sep"] - 1) * 100
tabla["oct->nov_%"] = (tabla["nov"] / tabla["oct"] - 1) * 100
tabla["sep->nov_%"] = (tabla["nov"] / tabla["sep"] - 1) * 100

print("\n--- Madrid: cambio del precio de alquiler en otoño, por año (informe mensual Idealista) ---")
print(tabla.round(2))

historico = tabla.dropna(subset=["sep->oct_%"])
historico = historico[historico.index < 2026]          # 2026 aún no tiene el dato de oct en la hoja
print("\nResumen años anteriores (sep->oct):")
print(historico["sep->oct_%"].describe().round(2))

# Contexto: cuánto se mueve el precio en un mes cualquiera
print(f"\nCambio mensual en cualquier mes (2015+): media {cambio_mensual['2015':].mean():.2f} %, "
      f"sd {cambio_mensual['2015':].std():.2f} %")

# --- 3. Lo observado en 2026 con nuestros datos diarios ----------------------
df = pd.read_csv(CARPETA / "Seguimiento Idealista.csv", parse_dates=["Fecha"])
df = df.rename(columns={"€/m2 alquiler": "p_alq"})
madrid = df[df["Ciudad"] == "Madrid"].set_index("Fecha")["p_alq"]

p_inicio = madrid.loc["2026-10-06"]
p_final = madrid[madrid.index >= "2026-11-05"].mean()   # mismo criterio que en analisis.py
obs_2026 = (p_final / p_inicio - 1) * 100

print(f"\n--- Madrid 2026 (nuestros datos): {p_inicio:.2f} -> {p_final:.2f} €/m²  =  {obs_2026:+.2f} % ---")

# ¿En cuántos otoños anteriores el precio subió tanto o más?
n_iguala = (historico["sep->oct_%"] >= obs_2026).sum()
print(f"Años anteriores con subida sep->oct >= {obs_2026:.1f} %: {n_iguala} de {len(historico)}")

# --- 4. Gráfico ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6.5))
barras = ax.bar(historico.index, historico["sep->oct_%"], color="grey", label="Cambio sep→oct (informe mensual)")

# Valor encima/debajo de cada barra (también los 0,0 %, que si no parecen huecos)
for anio, valor in historico["sep->oct_%"].items():
    ax.annotate(f"{valor:.1f}", (anio, valor), ha="center",
                va="bottom" if valor >= 0 else "top", fontsize=8,
                xytext=(0, 2 if valor >= 0 else -2), textcoords="offset points")
ceros = historico[historico["sep->oct_%"] == 0]
ax.scatter(ceros.index, [0] * len(ceros), color="grey", s=25, zorder=3)

# Un año por marca, sin decimales
ax.set_xticks(historico.index)
ax.set_xticklabels(historico.index, rotation=45)
ax.axhline(obs_2026, color="red", ls="--", lw=1.5,
           label=f"2026: 6-oct → inicio nov (nuestros datos) = {obs_2026:+.1f} %")
ax.axhline(0, color="black", lw=0.6)
ax.set_xlabel("Año")
ax.set_ylabel("Cambio en €/m² de alquiler (%)")
ax.set_title("Madrid: ¿es normal en otoño la subida del alquiler de 2026?")
ax.legend(loc="upper left")

pie = (f"En {n_iguala} de {len(historico)} otoños anteriores el precio subió de septiembre a octubre tanto o más que en 2026.\n"
       "Barras: informe mensual de Idealista (redondeado a 0,1 €/m²). Línea roja: media de anuncios recogidos a diario.\n"
       "Son medidas distintas: compara ritmos de cambio, no niveles.")
fig.text(0.5, 0.01, pie, ha="center", va="bottom", fontsize=9)
fig.tight_layout(rect=[0, 0.1, 1, 1])

ruta = CARPETA / "grafico_estacionalidad_precio_madrid.png"
fig.savefig(ruta, dpi=150)
print(f"Guardado: {ruta}")
plt.show()
plt.close(fig)
