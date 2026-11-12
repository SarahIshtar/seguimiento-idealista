import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import spearmanr

# Carpeta donde está este script: ahí se guardan los gráficos
CARPETA = Path(__file__).resolve().parent

#Cargar y revisar el csv
df = pd.read_csv("Seguimiento Idealista.csv", parse_dates=["Fecha"])
#print(df.shape)
#print(df.groupby("Fecha").size())
#print(df.isna().sum())
#print(df[df.isna().any(axis=1)])


# Nombres cortos para trabajar más cómodo
df = df.rename(columns={
    "Alquileres": "n_alq",
    "€/m2 alquiler": "p_alq",
    "Ventas": "n_ven",
    "€/m2 venta": "p_ven",
})


# Ordenar: el primer valor de cada ciudad tiene que ser el del 6-oct
df = df.sort_values(["Ciudad", "Fecha"]).reset_index(drop=True)

metricas = ["n_alq", "p_alq", "n_ven", "p_ven"]
for m in metricas:
    base = df.groupby("Ciudad")[m].transform("first")   # valor del 6-oct de cada ciudad
    df[m + "_idx"] = df[m] / base * 100

# Comprobación 1: el 6-oct todos los índices deben valer 100
print("\n--- Comprobación base (todo debería ser 100) ---")
print(df[df["Fecha"] == "2026-10-06"].filter(like="_idx").describe().round(2))

# Comprobación 2: cómo acaba cada ciudad el 10-nov
print("\n--- Índices a 10-nov (base 6-oct = 100) ---")
ultimo = (
    df[df["Fecha"] == "2026-11-10"]
    .set_index("Ciudad")
    .filter(like="_idx")
    .sort_values("n_alq_idx")
    .round(1)
)
print(ultimo)


# --- Paso 3: tamaño de la muestra de cada ciudad -----------------------------
tamano = df.groupby("Ciudad").agg(
    n_alq_6oct=("n_alq", "first"),
    n_alq_mediana=("n_alq", "median"),
    n_alq_min=("n_alq", "min"),
    n_alq_max=("n_alq", "max"),
    n_ven_6oct=("n_ven", "first"),
)

# Unimos con los índices del 10-nov para verlo todo junto
resumen = ultimo.join(tamano).sort_values("n_alq_6oct")
print("\n--- Índices a 10-nov junto con el tamaño de la muestra ---")
print(resumen)


# --- Paso 4: evolución día a día -------------------------------------------
pequenas = ["Terrassa", "Sabadell", "Móstoles", "Vitoria-Gasteiz", "Badalona"]
df["muestra_pequena"] = df["Ciudad"].isin(pequenas)

grandes = df[~df["muestra_pequena"]]

# Mediana de las 22 ciudades con muestra suficiente, cada día
evolucion = grandes.groupby("Fecha")[["n_alq_idx", "p_alq_idx", "n_ven_idx", "p_ven_idx"]].median().round(1)
print("\n--- Mediana diaria (22 ciudades, base 6-oct = 100) ---")
print(evolucion)

# Gráficos
def grafico(metrica, titulo):
    fig, ax = plt.subplots(figsize=(11, 6))
    for ciudad, g in grandes.groupby("Ciudad"):
        ax.plot(g["Fecha"], g[metrica], color="grey", alpha=0.4, lw=1)
    ax.plot(evolucion.index, evolucion[metrica], color="black", lw=2.5, label="Mediana")
    ax.axhline(100, color="black", lw=0.6)
    ax.axvline(pd.Timestamp("2026-10-08"), color="red", ls="--", lw=1, label="Vigor RDL 29 (8-oct)")
    ax.set_title(f"{titulo} (base 6-oct = 100) — 22 ciudades")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    ruta = CARPETA / f"grafico_{metrica}.png"
    fig.savefig(ruta, dpi=150)
    print(f"Guardado: {ruta}")
    plt.show()
    plt.close(fig)

#grafico("n_alq_idx", "Anuncios de alquiler")
#grafico("n_ven_idx", "Anuncios de venta")
#grafico("p_alq_idx", "€/m² alquiler")
#grafico("p_ven_idx", "€/m² venta")


# --- Paso 6: ¿pasa la oferta de alquiler a venta? -----------------------------
inicio = grandes[grandes["Fecha"] == "2026-10-06"].set_index("Ciudad")
final = grandes[grandes["Fecha"] >= "2026-11-05"].groupby("Ciudad")[["n_alq", "n_ven"]].mean()

cambio = pd.DataFrame({
    "alq_6oct": inicio["n_alq"],
    "alq_final": final["n_alq"].round(0),
    "ven_6oct": inicio["n_ven"],
    "ven_final": final["n_ven"].round(0),
})
cambio["alq_dif"] = cambio["alq_final"] - cambio["alq_6oct"]          # anuncios de alquiler perdidos (negativo)
cambio["ven_dif"] = cambio["ven_final"] - cambio["ven_6oct"]          # anuncios de venta ganados
cambio["alq_%"] = (cambio["alq_final"] / cambio["alq_6oct"] - 1) * 100
cambio["ven_%"] = (cambio["ven_final"] / cambio["ven_6oct"] - 1) * 100

print("\n--- Cambio 6-oct -> media 5/6/10-nov ---")
print(cambio.sort_values("alq_%").round(1))

# ¿Van juntos? Correlación de Spearman (por rangos: no le afectan los valores extremos)
correlacion, p_valor = spearmanr(cambio["alq_%"], cambio["ven_%"])
print(f"\nCorrelación (Spearman) % alquiler vs % venta: {round(correlacion, 2)} (p-valor: {round(p_valor, 4)})")

# Comprobación en la misma escala: por cada 100 anuncios de alquiler iniciales.
# Si hubiera trasvase total, ven_por100 ≈ -alq_por100.
# Ojo: ambas se dividen entre alq_6oct, lo que puede inflar la correlación (municipios con poco alquiler).
cambio["alq_por100"] = cambio["alq_dif"] / cambio["alq_6oct"] * 100   # = alq_%
cambio["ven_por100"] = cambio["ven_dif"] / cambio["alq_6oct"] * 100   # venta ganada por cada 100 alquileres iniciales

rho2, p2 = spearmanr(cambio["alq_por100"], cambio["ven_por100"])
print(f"\nSpearman (misma escala): rho = {rho2:.2f}, p-valor = {p2:.3f}")
print(cambio[["alq_por100", "ven_por100"]].sort_values("alq_por100").round(1))

# Gráfico de dispersión
fig, ax = plt.subplots(figsize=(9, 7.5))
ax.scatter(cambio["alq_%"], cambio["ven_%"])
for ciudad, fila in cambio.iterrows():
    ax.annotate(ciudad, (fila["alq_%"], fila["ven_%"]), fontsize=8, xytext=(3, 3), textcoords="offset points")
ax.axhline(0, color="black", lw=0.6)
ax.axvline(0, color="black", lw=0.6)
ax.set_xlabel("Cambio en anuncios de ALQUILER (%)")
ax.set_ylabel("Cambio en anuncios de VENTA (%)")
ax.set_title("¿Las ciudades que pierden más alquiler ganan más venta?")

# Pie del gráfico: coeficiente de Spearman y p-valor
pie = (f"Correlación de Spearman: ρ = {correlacion:.2f} (p-valor = {p_valor:.3f}, n = {len(cambio)} municipios)\n"
       "Cambio entre el 6-oct y la media del 5, 6 y 10-nov. "
       "Excluidos municipios con <100 anuncios de alquiler.")
fig.text(0.5, 0.01, pie, ha="center", va="bottom", fontsize=9)
fig.tight_layout(rect=[0, 0.07, 1, 1])   # deja hueco abajo para el pie

ruta = CARPETA / "grafico_dispersion_alq_ven.png"
fig.savefig(ruta, dpi=150)               # guardar ANTES de show, si no sale en blanco
print(f"Guardado: {ruta}")
plt.show()
plt.close(fig)


# --- Paso 7: ¿sube el alquiler de verdad o es efecto composición? -------------
# Hipótesis de composición: los pisos baratos se alquilan antes y salen del stock,
# así que el €/m² MEDIO de los que quedan sube aunque nadie cambie su precio.
# Si fuera así, el precio debería subir más donde más cae la oferta -> correlación NEGATIVA.
# Ojo: una subida real por escasez daría el mismo signo; esta prueba no separa ambas.
# Lo que sí indica: si NO hay correlación, la composición pierde fuerza como explicación.

final_p = grandes[grandes["Fecha"] >= "2026-11-05"].groupby("Ciudad")[["p_alq", "p_ven"]].mean()

precio = pd.DataFrame({
    "alq_%": cambio["alq_%"],                     # cambio en nº de anuncios de alquiler (paso 6)
    "p_alq_6oct": inicio["p_alq"],
    "p_alq_final": final_p["p_alq"].round(2),
    "p_ven_6oct": inicio["p_ven"],
    "p_ven_final": final_p["p_ven"].round(0),
})
precio["p_alq_%"] = (precio["p_alq_final"] / precio["p_alq_6oct"] - 1) * 100
precio["p_ven_%"] = (precio["p_ven_final"] / precio["p_ven_6oct"] - 1) * 100   # referencia: el precio de venta

print("\n--- Cambio en oferta y precio de alquiler: 6-oct -> media 5/6/10-nov ---")
print(precio.sort_values("alq_%").round(1))
print(f"\nMunicipios donde sube el €/m² de alquiler: {(precio['p_alq_%'] > 0).sum()} de {len(precio)}")
print(f"Mediana del cambio €/m² alquiler: {precio['p_alq_%'].median():.1f} %  |  "
      f"venta: {precio['p_ven_%'].median():.1f} %")

rho_p, p_p = spearmanr(precio["alq_%"], precio["p_alq_%"])
print(f"\nSpearman % anuncios alquiler vs % €/m² alquiler: rho = {rho_p:.2f}, p-valor = {p_p:.3f}")

# Gráfico de dispersión
fig, ax = plt.subplots(figsize=(9, 7.5))
ax.scatter(precio["alq_%"], precio["p_alq_%"])
for ciudad, fila in precio.iterrows():
    ax.annotate(ciudad, (fila["alq_%"], fila["p_alq_%"]), fontsize=8, xytext=(3, 3), textcoords="offset points")
ax.axhline(0, color="black", lw=0.6)
ax.axvline(0, color="black", lw=0.6)
ax.set_xlabel("Cambio en anuncios de ALQUILER (%)")
ax.set_ylabel("Cambio en €/m² de ALQUILER (%)")
ax.set_title("¿Sube más el precio del alquiler donde más cae la oferta?")

pie = (f"Correlación de Spearman: ρ = {rho_p:.2f} (p-valor = {p_p:.3f}, n = {len(precio)} municipios)\n"
       "Cambio entre el 6-oct y la media del 5, 6 y 10-nov. "
       "Excluidos municipios con <100 anuncios de alquiler.")
fig.text(0.5, 0.01, pie, ha="center", va="bottom", fontsize=9)
fig.tight_layout(rect=[0, 0.07, 1, 1])

ruta = CARPETA / "grafico_dispersion_oferta_precio_alq.png"
fig.savefig(ruta, dpi=150)
print(f"Guardado: {ruta}")
plt.show()
plt.close(fig)
