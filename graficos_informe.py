# -*- coding: utf-8 -*-
"""
graficos_informe.py

Genera los cuatro gráficos del informe de seguimiento de Idealista y la tabla
de cifras para comprobar si el texto del informe sigue siendo correcto:

  G1. Líneas: índice de anuncios y de €/m² de alquiler (mediana de 22 ciudades).
  G2. Dispersión: variación de anuncios de alquiler frente a variación del precio.
  G3. Dispersión: variación de anuncios de alquiler frente a la de venta.
  G4. Barras: Madrid, cambio de septiembre a octubre de 2007 a 2025 frente a 2026.

Todo se guarda en la carpeta informe_actualizado/.
Los cálculos siguen a analisis.py y estacionalidad.py (incluido su redondeo).

Uso (en la misma carpeta que el CSV y el Excel):
    python graficos_informe.py
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from scipy.stats import spearmanr


# ============================================================
# 1. CONFIGURACIÓN (normalmente solo hay que tocar esto)
# ============================================================

# Carpeta donde está este script: de ahí se leen los datos
CARPETA = Path(__file__).resolve().parent

RUTA_CSV = CARPETA / "Seguimiento Idealista.csv"    # lo crea convert_to_csv.py
RUTA_EXCEL = CARPETA / "Seguimiento Idealista.xlsx"  # para el G4 (hoja Estadísticas)
SEPARADOR = ","             # pon ";" si tu CSV usa punto y coma
DECIMAL = "."               # pon "," si los decimales vienen con coma
CODIFICACION = "utf-8-sig"  # si da error de caracteres, prueba "latin-1"

# Carpeta de salida
SALIDA = CARPETA / "informe_actualizado"
SALIDA_GRAFICOS = SALIDA / "graficos"

FECHA_BASE = "2026-10-06"    # línea base: índice = 100
FECHA_VIGOR = "2026-10-08"   # entrada en vigor del RDL 29/2026
INICIO_FINAL = "2026-11-05"  # el "final" es la media desde este día

# Municipios con menos de 100 anuncios de alquiler (se excluyen)
EXCLUIDAS = ["Terrassa", "Sabadell", "Móstoles", "Vitoria-Gasteiz", "Badalona"]

# Ciudades que se destacan en negrita en los gráficos 2 y 3 (las del texto).
# Tienen que estar escritas exactamente igual que en el CSV.
DESTACADAS = ["A Coruña", "Gijón", "Granada", "Madrid", "Barcelona",
              "Palma de Mallorca"]

# Cómo se escribe cada ciudad en las etiquetas, si es distinto del CSV
NOMBRE_ETIQUETA = {
    "Jerez de la frontera": "Jerez de la Frontera",
    "Palma de Mallorca": "Palma",
    "Las Palmas de Gran Canaria": "Las Palmas de G. C.",
    "Santa Cruz de Tenerife": "S. C. de Tenerife",
}

# Si alguna etiqueta se pisa con otra, cámbiala de sitio aquí.
# Por defecto va a la derecha del círculo. Opciones:
# "derecha", "izquierda", "arriba" o "abajo".
POSICION_G2 = {
    "Jerez de la frontera": "arriba",
    "Sevilla": "arriba",
    "Bilbao": "izquierda",
    "Murcia": "izquierda",
}
POSICION_G3 = {
    "Valencia": "izquierda",
    "Zaragoza": "abajo",
}

# Colores: cámbialos por los de la guía de estilo de Newtral
COLOR_ANUNCIOS = "#1F5FA8"
COLOR_PRECIO = "#E07B00"
COLOR_GRIS = "#9A9A9A"
COLOR_TEXTO = "#222222"

# True añade al gráfico 1 las líneas de venta, en gris y discontinuas
INCLUIR_VENTA = False

FUENTE = "Fuente: elaboración propia con datos de Idealista"

# Valores del informe para la comprobación de Spearman del G2
RHO_INFORME, P_INFORME = -0.31, 0.16


# ============================================================
# 2. FUNCIONES PEQUEÑAS DE FORMATO
# ============================================================

MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def numero_es(valor, decimales=1, signo=False):
    """Escribe un número a la española: coma decimal y signo menos tipográfico.
    Con signo=True, los positivos llevan '+' delante."""
    texto = f"{valor:+.{decimales}f}" if signo else f"{valor:.{decimales}f}"
    return texto.replace(".", ",").replace("-", "−")


def miles_es(valor):
    """Escribe un entero con punto de miles: 3420 -> '3.420'."""
    return f"{valor:,.0f}".replace(",", ".").replace("-", "−")


def fecha_es(x, pos=None):
    """Convierte una fecha del eje en un texto como '12 oct'."""
    fecha = mdates.num2date(x)
    return f"{fecha.day} {MESES[fecha.month - 1]}"


def lista_dias(fechas):
    """Convierte una lista de fechas en un texto como '5, 6, 10 y 11 de noviembre'.
    Si hay varios meses: '30 de octubre y 3 y 4 de noviembre'."""
    fechas = sorted(fechas)
    partes = []
    for mes in sorted({f.month for f in fechas}):
        dias = [str(f.day) for f in fechas if f.month == mes]
        texto = dias[0] if len(dias) == 1 else ", ".join(dias[:-1]) + " y " + dias[-1]
        partes.append(f"{texto} de {MESES_LARGOS[mes - 1]}")
    return " y ".join(partes)


def poner_titulos(fig, titulo, subtitulo, nota=""):
    """Título y subtítulo arriba a la izquierda; nota y fuente abajo."""
    fig.text(0.02, 0.97, titulo, fontsize=15, fontweight="bold",
             color=COLOR_TEXTO, ha="left", va="top")
    fig.text(0.02, 0.91, subtitulo, fontsize=10.5,
             color="#555555", ha="left", va="top")
    pie = (nota + "\n" + FUENTE) if nota else FUENTE
    fig.text(0.02, 0.02, pie, fontsize=8.5, color="#777777",
             ha="left", va="bottom", linespacing=1.5)


def limpiar_ejes(ax, rejilla="y"):
    """Quita bordes innecesarios y deja una rejilla suave."""
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#BBBBBB")
    ax.grid(axis=rejilla, color="#E6E6E6", linewidth=0.8)
    ax.tick_params(axis="both", colors="#555555", length=0)
    ax.set_axisbelow(True)


def guardar_csv(tabla, nombre):
    """Guarda un CSV listo para Datawrapper: ';' separador y ',' decimal."""
    tabla.to_csv(SALIDA / nombre, sep=";", decimal=",", encoding="utf-8-sig")
    print(f"Guardado: {nombre}")


# ============================================================
# 3. LEER Y PREPARAR LOS DATOS DIARIOS
# ============================================================

SALIDA_GRAFICOS.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RUTA_CSV, sep=SEPARADOR, decimal=DECIMAL,
                 encoding=CODIFICACION)

# Nombres cortos para trabajar más cómodo
df = df.rename(columns={
    "Alquileres": "anuncios_alq",
    "€/m2 alquiler": "precio_alq",
    "Ventas": "anuncios_venta",
    "€/m2 venta": "precio_venta",
})
METRICAS = ["anuncios_alq", "precio_alq", "anuncios_venta", "precio_venta"]

# Comprobación: las cuatro métricas tienen que haberse leído como números
for col in METRICAS:
    if not pd.api.types.is_numeric_dtype(df[col]):
        raise ValueError(
            f"La columna '{col}' no se ha leído como número. "
            "Revisa SEPARADOR y DECIMAL al principio del script."
        )

# Fechas: si vienen como 2026-10-06 se leen así; si vienen como 06/10/2026,
# se indica que el día va primero. (Mezclar las dos formas confunde día y mes.)
texto_fecha = df["Fecha"].astype(str)
if texto_fecha.str.match(r"^\d{4}-").all():
    df["Fecha"] = pd.to_datetime(texto_fecha, format="ISO8601")
else:
    df["Fecha"] = pd.to_datetime(texto_fecha, dayfirst=True)

ULTIMA_FECHA = df["Fecha"].max()
print(f"Fechas leídas: del {df['Fecha'].min():%d/%m/%Y} "
      f"al {ULTIMA_FECHA:%d/%m/%Y} ({df['Fecha'].nunique()} días)")
if pd.Timestamp(FECHA_BASE) not in set(df["Fecha"]):
    raise ValueError("No encuentro el día base en los datos. Revisa las fechas.")

# Quitamos los municipios con muestra pequeña
df = df[~df["Ciudad"].isin(EXCLUIDAS)].copy()
ciudades = sorted(df["Ciudad"].unique())
N_CIUDADES = len(ciudades)
print(f"Ciudades en el análisis: {N_CIUDADES}")
if N_CIUDADES != 22:
    print("¡Ojo! No salen 22. Revisa cómo están escritos los nombres "
          "en EXCLUIDAS. Estas son las ciudades que quedan:")
    print(ciudades)
for c in DESTACADAS:
    if c not in ciudades:
        print(f"¡Ojo! '{c}' (en DESTACADAS) no aparece en el CSV.")

# Días que forman el "final" del periodo (se usan en los pies de los gráficos)
DIAS_FINAL = sorted(df.loc[df["Fecha"] >= pd.Timestamp(INICIO_FINAL), "Fecha"].unique())
DIAS_FINAL = [pd.Timestamp(d) for d in DIAS_FINAL]
TEXTO_FINAL = lista_dias(DIAS_FINAL)
print(f"Final del periodo = media del {TEXTO_FINAL}")

TEXTO_ULTIMO = f"{ULTIMA_FECHA.day} de {MESES_LARGOS[ULTIMA_FECHA.month - 1]}"


# ============================================================
# 4. ÍNDICES DIARIOS (6 de octubre = 100) -> G1
# ============================================================

# Valores de cada ciudad el día base
base = df[df["Fecha"] == pd.Timestamp(FECHA_BASE)].set_index("Ciudad")[METRICAS]

# Índice = valor del día / valor del día base * 100
for col in METRICAS:
    df["ind_" + col] = df[col] / df["Ciudad"].map(base[col]) * 100

# Mediana diaria de las 22 ciudades (los valores vacíos se ignoran)
columnas_indice = ["ind_" + c for c in METRICAS]
mediana = df.groupby("Fecha")[columnas_indice].median()


# ============================================================
# 5. CAMBIO DE CADA CIUDAD: 6 oct -> final (como analisis.py)
# ============================================================

# "Final" = media de los días desde INICIO_FINAL.
# Igual que en analisis.py: los anuncios finales se redondean a enteros,
# el €/m² de alquiler a 2 decimales y el €/m² de venta a enteros.
final = (df[df["Fecha"] >= pd.Timestamp(INICIO_FINAL)]
         .groupby("Ciudad")[METRICAS].mean())
final["anuncios_alq"] = final["anuncios_alq"].round(0)
final["anuncios_venta"] = final["anuncios_venta"].round(0)
final["precio_alq"] = final["precio_alq"].round(2)
final["precio_venta"] = final["precio_venta"].round(0)

tabla = pd.DataFrame({
    "anuncios_alq_6oct": base["anuncios_alq"],
    "anuncios_alq_final": final["anuncios_alq"],
    "anuncios_venta_6oct": base["anuncios_venta"],
    "anuncios_venta_final": final["anuncios_venta"],
}).loc[ciudades]

tabla["dif_anuncios_alq"] = tabla["anuncios_alq_final"] - tabla["anuncios_alq_6oct"]
tabla["dif_anuncios_venta"] = tabla["anuncios_venta_final"] - tabla["anuncios_venta_6oct"]
tabla["var_anuncios_alq"] = (final["anuncios_alq"] / base["anuncios_alq"] - 1) * 100
tabla["var_anuncios_venta"] = (final["anuncios_venta"] / base["anuncios_venta"] - 1) * 100
tabla["var_precio_alq"] = (final["precio_alq"] / base["precio_alq"] - 1) * 100
tabla["var_precio_venta"] = (final["precio_venta"] / base["precio_venta"] - 1) * 100
# Venta ganada (o perdida) por cada 100 anuncios iniciales de alquiler
tabla["venta_por100_alq"] = tabla["dif_anuncios_venta"] / tabla["anuncios_alq_6oct"] * 100

# Correlaciones de Spearman
rho_precio, p_precio = spearmanr(tabla["var_anuncios_alq"], tabla["var_precio_alq"])
rho_venta, p_venta = spearmanr(tabla["var_anuncios_alq"], tabla["var_anuncios_venta"])
rho_por100, p_por100 = spearmanr(tabla["var_anuncios_alq"], tabla["venta_por100_alq"])

# Comprobación: la correlación del G2 debe coincidir con la del informe
print(f"Spearman anuncios-precio: rho = {rho_precio:.2f}, p = {p_precio:.2f} "
      f"(en el informe: {numero_es(RHO_INFORME, 2)} y {numero_es(P_INFORME, 2)})")
if round(rho_precio, 2) != RHO_INFORME or round(p_precio, 2) != P_INFORME:
    print("¡Ojo! La correlación no coincide con la del informe. "
          "Puede deberse a días nuevos en los datos: revisa cifras_informe.csv.")


# ============================================================
# 6. GRÁFICO 1: anuncios y precio del alquiler
# ============================================================

fig, ax = plt.subplots(figsize=(10, 6))
fig.subplots_adjust(left=0.07, right=0.80, top=0.82, bottom=0.15)

# Línea de referencia en 100
ax.axhline(100, color="#BBBBBB", linewidth=1)

# Líneas de venta (opcionales), en gris para que no compitan
if INCLUIR_VENTA:
    ax.plot(mediana.index, mediana["ind_anuncios_venta"],
            color=COLOR_GRIS, linewidth=1.5, linestyle="--")
    ax.plot(mediana.index, mediana["ind_precio_venta"],
            color=COLOR_GRIS, linewidth=1.5, linestyle=":")

# Las dos líneas protagonistas
ax.plot(mediana.index, mediana["ind_anuncios_alq"],
        color=COLOR_ANUNCIOS, linewidth=2.8)
ax.plot(mediana.index, mediana["ind_precio_alq"],
        color=COLOR_PRECIO, linewidth=2.8)

# Etiquetas directas al final de cada línea (en vez de leyenda)
ultima_fecha = mediana.index[-1]
etiquetas = [
    ("ind_anuncios_alq", "Anuncios de alquiler", COLOR_ANUNCIOS, "bold"),
    ("ind_precio_alq", "Precio del alquiler (€/m²)", COLOR_PRECIO, "bold"),
]
if INCLUIR_VENTA:
    etiquetas += [
        ("ind_anuncios_venta", "Anuncios de venta", COLOR_GRIS, "normal"),
        ("ind_precio_venta", "Precio de venta (€/m²)", COLOR_GRIS, "normal"),
    ]
for col, texto, color, peso in etiquetas:
    valor = mediana[col].iloc[-1]
    ax.annotate(f"{texto}\n{numero_es(valor)}",
                xy=(ultima_fecha, valor), xytext=(10, 0),
                textcoords="offset points", va="center",
                color=color, fontweight=peso, fontsize=10,
                annotation_clip=False)

# Línea vertical en la entrada en vigor del decreto
vigor = pd.Timestamp(FECHA_VIGOR)
ax.axvline(vigor, color="#777777", linewidth=1, linestyle="--")
ax.annotate("Entra en vigor\nel RDL 29/2026", xy=(vigor, 1),
            xycoords=("data", "axes fraction"), xytext=(6, -4),
            textcoords="offset points", va="top", fontsize=9,
            color="#555555")

# Ejes
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
ax.xaxis.set_major_formatter(mticker.FuncFormatter(fecha_es))
ax.yaxis.set_major_locator(mticker.MultipleLocator(5))  # marcas cada 5 puntos
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda y, pos: numero_es(y, 0)))
ax.set_xlim(mediana.index[0] - pd.Timedelta(hours=12),
            ultima_fecha + pd.Timedelta(days=1))
limpiar_ejes(ax)

poner_titulos(fig,
              "Los anuncios de alquiler caen mientras su precio sube",
              f"Índice, 6 de octubre = 100. Mediana de {N_CIUDADES} municipios",
              nota=f"Datos de cada día laborable hasta el {TEXTO_ULTIMO}.")

fig.savefig(SALIDA_GRAFICOS / "g1_alquiler_anuncios_precio.png", dpi=200)
plt.close(fig)
print("Guardado: g1_alquiler_anuncios_precio.png")

# Datos del gráfico 1 para Datawrapper
serie = mediana.round(1).rename(columns={
    "ind_anuncios_alq": "Anuncios de alquiler",
    "ind_precio_alq": "Precio del alquiler (€/m²)",
    "ind_anuncios_venta": "Anuncios de venta",
    "ind_precio_venta": "Precio de venta (€/m²)",
})
serie.index = serie.index.strftime("%Y-%m-%d")
guardar_csv(serie, "datos_g1.csv")


# ============================================================
# 7. FUNCIÓN COMÚN PARA LOS GRÁFICOS DE DISPERSIÓN (G2 y G3)
# ============================================================

# Tamaño de los círculos: el área es proporcional a los anuncios del 6 oct
TAMANO_MAXIMO = 1600
escala = TAMANO_MAXIMO / tabla["anuncios_alq_6oct"].max()
tamanos = tabla["anuncios_alq_6oct"] * escala


def dispersion(col_x, col_y, etiqueta_x, etiqueta_y, posiciones, titulo,
               nota, archivo, linea_vertical=False):
    """Dibuja un gráfico de burbujas de las 22 ciudades y lo guarda."""
    fig, ax = plt.subplots(figsize=(10, 7.5))
    fig.subplots_adjust(left=0.09, right=0.96, top=0.84, bottom=0.17)

    ax.axhline(0, color="#BBBBBB", linewidth=1)
    if linea_vertical:
        ax.axvline(0, color="#BBBBBB", linewidth=1)
    ax.scatter(tabla[col_x], tabla[col_y],
               s=tamanos, color=COLOR_ANUNCIOS, alpha=0.55,
               edgecolor="white", linewidth=1, zorder=2)

    # Una etiqueta por ciudad, a la derecha de su círculo (o donde diga posiciones)
    for ciudad, fila in tabla.iterrows():
        radio = (tamanos[ciudad] / 3.1416) ** 0.5  # radio del círculo, en puntos
        posicion = posiciones.get(ciudad, "derecha")
        # (desplazamiento x, desplazamiento y, alineación horizontal, vertical)
        if posicion == "izquierda":
            dx, dy, ha, va = -radio - 3, 0, "right", "center"
        elif posicion == "arriba":
            dx, dy, ha, va = 0, radio + 2, "center", "bottom"
        elif posicion == "abajo":
            dx, dy, ha, va = 0, -radio - 2, "center", "top"
        else:
            dx, dy, ha, va = radio + 3, 0, "left", "center"
        destacada = ciudad in DESTACADAS
        ax.annotate(NOMBRE_ETIQUETA.get(ciudad, ciudad),
                    xy=(fila[col_x], fila[col_y]),
                    xytext=(dx, dy), textcoords="offset points",
                    ha=ha, va=va,
                    fontsize=9.5 if destacada else 8.5,
                    fontweight="bold" if destacada else "normal",
                    color=COLOR_TEXTO if destacada else "#666666", zorder=3)

    # Leyenda del tamaño con dos círculos de referencia
    for n in [1000, 5000]:
        ax.scatter([], [], s=n * escala, color=COLOR_ANUNCIOS, alpha=0.55,
                   edgecolor="white", label=f"{miles_es(n)} anuncios")
    ax.legend(title="Anuncios de alquiler el 6 oct", loc="lower left",
              frameon=False, labelspacing=1.8, borderpad=1.2,
              title_fontsize=9, fontsize=9)

    # Ejes
    formato_pct = mticker.FuncFormatter(lambda v, pos: numero_es(v, 0) + " %")
    ax.xaxis.set_major_formatter(formato_pct)
    ax.yaxis.set_major_formatter(formato_pct)
    ax.set_xlabel(etiqueta_x, color="#555555")
    ax.set_ylabel(etiqueta_y, color="#555555")
    ax.margins(x=0.12, y=0.15)
    limpiar_ejes(ax, rejilla="both")

    poner_titulos(fig, titulo,
                  f"Variación entre el 6 de octubre y la media del {TEXTO_FINAL}.\n"
                  "El tamaño del círculo indica los anuncios de alquiler "
                  "de cada ciudad el 6 de octubre",
                  nota=nota)

    fig.savefig(SALIDA_GRAFICOS / archivo, dpi=200)
    plt.close(fig)
    print(f"Guardado: {archivo}")


# ============================================================
# 8. GRÁFICO 2: anuncios de alquiler frente a su precio
# ============================================================

dispersion("var_anuncios_alq", "var_precio_alq",
           "Variación de los anuncios de alquiler",
           "Variación del precio del alquiler (€/m²)",
           POSICION_G2,
           "La oferta de alquiler cae en todas las ciudades, "
           "pero no al mismo ritmo",
           f"Correlación de Spearman: ρ = {numero_es(rho_precio, 2)} "
           f"(p = {numero_es(p_precio, 2)}; n = {N_CIUDADES} municipios).",
           "g2_ciudades_anuncios_precio.png")


# ============================================================
# 9. GRÁFICO 3: anuncios de alquiler frente a anuncios de venta
# ============================================================

dispersion("var_anuncios_alq", "var_anuncios_venta",
           "Variación de los anuncios de alquiler",
           "Variación de los anuncios de venta",
           POSICION_G3,
           "Ciudad a ciudad, alquiler y venta no van de la mano",
           f"Correlación de Spearman: ρ = {numero_es(rho_venta, 2)} "
           f"(p = {numero_es(p_venta, 2)}; n = {N_CIUDADES} municipios).",
           "g3_alquiler_vs_venta.png")

# Datos de los gráficos 2 y 3 para Datawrapper
datos_ciudades = tabla[["anuncios_alq_6oct", "var_anuncios_alq",
                        "var_precio_alq", "var_anuncios_venta"]].round(1)
datos_ciudades.index = [NOMBRE_ETIQUETA.get(c, c) for c in datos_ciudades.index]
datos_ciudades.index.name = "Ciudad"
datos_ciudades = datos_ciudades.rename(columns={
    "anuncios_alq_6oct": "Anuncios de alquiler el 6 oct",
    "var_anuncios_alq": "Variación de anuncios de alquiler (%)",
    "var_precio_alq": "Variación del precio del alquiler (%)",
    "var_anuncios_venta": "Variación de anuncios de venta (%)",
})
guardar_csv(datos_ciudades.drop(columns="Variación de anuncios de venta (%)"),
            "datos_g2.csv")
guardar_csv(datos_ciudades.drop(columns="Variación del precio del alquiler (%)"),
            "datos_g3.csv")


# ============================================================
# 10. GRÁFICO 4: Madrid, 2026 frente a otros otoños
# ============================================================

# Serie mensual de Madrid (hoja Estadísticas), como en estacionalidad.py
est = pd.read_excel(RUTA_EXCEL, sheet_name="Estadísticas", parse_dates=["Mes"])

# "23,4 €/m2" -> 23.4 ; los "n.d." quedan vacíos y se ignoran
est["precio"] = pd.to_numeric(
    est["Precio m2"].astype(str)
    .str.extract(r"(\d+(?:[.,]\d+)?)")[0]
    .str.replace(",", "."),
    errors="coerce",
)
mensual = est.dropna(subset=["precio"]).set_index("Mes")["precio"].sort_index()

# Precio de septiembre y de octubre de cada año
septiembre = mensual[mensual.index.month == 9]
octubre = mensual[mensual.index.month == 10]
septiembre.index = septiembre.index.year
octubre.index = octubre.index.year

otonos = ((octubre / septiembre - 1) * 100).dropna()
otonos = otonos[(otonos.index >= 2007) & (otonos.index <= 2025)]
print(f"G4: {len(otonos)} otoños ({otonos.index.min()}-{otonos.index.max()})")

# 2026 con nuestros datos diarios (ya calculado arriba, con el mismo redondeo)
madrid_inicio = base.loc["Madrid", "precio_alq"]
madrid_final = final.loc["Madrid", "precio_alq"]
madrid_2026 = (madrid_final / madrid_inicio - 1) * 100

fig, ax = plt.subplots(figsize=(10, 6))
fig.subplots_adjust(left=0.08, right=0.97, top=0.82, bottom=0.22)

ax.bar(otonos.index, otonos.values, color=COLOR_GRIS, width=0.7, zorder=2)
ax.axhline(0, color="#BBBBBB", linewidth=1)

# Los años con un cambio de 0,0 % no tienen barra: un punto para que no
# parezca que falta el dato
ceros = otonos[otonos == 0]
ax.scatter(ceros.index, [0] * len(ceros), color="#666666", s=22, zorder=3)

# Línea horizontal de 2026, con etiqueta directa encima, a la izquierda
ax.axhline(madrid_2026, color=COLOR_PRECIO, linewidth=2.2, zorder=3)
ax.annotate(f"2026: {numero_es(madrid_2026, signo=True)} % "
            f"(6 de octubre → media del {TEXTO_FINAL})",
            xy=(0, madrid_2026), xycoords=("axes fraction", "data"),
            xytext=(4, 5), textcoords="offset points", va="bottom",
            color=COLOR_PRECIO, fontweight="bold", fontsize=9.5)

# Eje X con años enteros (una marca por año)
ax.set_xticks(otonos.index)
ax.set_xticklabels(otonos.index, rotation=45)
ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda v, pos: numero_es(v, 0) + " %"))
ax.set_xlim(otonos.index.min() - 0.6, otonos.index.max() + 0.6)
limpiar_ejes(ax)

poner_titulos(fig,
              "Madrid: la subida de 2026 frente al cambio de septiembre "
              "a octubre de 2007 a 2025",
              "Variación del precio del alquiler (€/m²). Barras: informe mensual "
              "de Idealista. Línea: nuestros datos diarios",
              nota="El informe mensual y nuestra media de anuncios diarios son "
                   "medidas distintas: se comparan ritmos de cambio, no niveles.\n"
                   "El informe redondea a 0,1 €/m². Los puntos marcan los años "
                   "con un cambio del 0,0 %.")
# El título del G4 es largo: un poco más pequeño para que quepa
fig.texts[0].set_fontsize(13.5)

fig.savefig(SALIDA_GRAFICOS / "g4_madrid_otonos.png", dpi=200)
plt.close(fig)
print("Guardado: g4_madrid_otonos.png")

datos_g4 = pd.DataFrame({
    "Precio septiembre (€/m²)": septiembre,
    "Precio octubre (€/m²)": octubre,
    "Cambio septiembre-octubre (%)": otonos.round(1),
}).loc[otonos.index]
datos_g4.index.name = "Año"
datos_g4.loc["2026 (datos diarios)"] = [madrid_inicio, madrid_final,
                                        round(madrid_2026, 1)]
guardar_csv(datos_g4, "datos_g4.csv")


# ============================================================
# 11. CIFRAS DEL INFORME: valor anterior y valor nuevo
# ============================================================

# Cada fila: (apartado, cifra, valor del informe, valor nuevo, decimales que usa el informe)
# Una cifra "cambia" si, redondeada como en el informe, se mueve más de 0,1.
# Los índices "al final" del informe son la mediana del último día
# (el mismo valor que aparece al final de las líneas del G1)
ind_alq = mediana["ind_anuncios_alq"].iloc[-1]
ind_venta = mediana["ind_anuncios_venta"].iloc[-1]
suben_precio = int((tabla["var_precio_alq"] > 0).sum())
# "Venta: entre +2 % y +7 % en la mayoría" se refiere a los anuncios de venta
venta_2_7 = int(tabla["var_anuncios_venta"].between(2, 7).sum())


def v(ciudad, col):
    return tabla.loc[ciudad, col]


cifras = [
    ("General", "Índice de anuncios de alquiler el último día", 84.5, ind_alq, 1),
    ("General", "Variación del €/m² de alquiler (mediana, %)", 2.4,
     tabla["var_precio_alq"].median(), 1),
    ("General", f"Ciudades donde sube el €/m² de alquiler (de {N_CIUDADES})",
     19, suben_precio, 0),
    ("General", "Índice de anuncios de venta el último día", 104, ind_venta, 0),
    ("General", "Variación del €/m² de venta (mediana, %)", -0.1,
     tabla["var_precio_venta"].median(), 1),
    ("Anuncios de alquiler (%)", "A Coruña", -32, v("A Coruña", "var_anuncios_alq"), 0),
    ("Anuncios de alquiler (%)", "Gijón", -28, v("Gijón", "var_anuncios_alq"), 0),
    ("Anuncios de alquiler (%)", "Granada", -25, v("Granada", "var_anuncios_alq"), 0),
    ("Anuncios de alquiler (%)", "Madrid", -10.5, v("Madrid", "var_anuncios_alq"), 1),
    ("Anuncios de alquiler (%)", "Barcelona", -6, v("Barcelona", "var_anuncios_alq"), 0),
    ("Anuncios de alquiler (%)", "Palma", -1, v("Palma de Mallorca", "var_anuncios_alq"), 0),
    ("€/m² de alquiler (%)", "A Coruña", 7.8, v("A Coruña", "var_precio_alq"), 1),
    ("€/m² de alquiler (%)", "Valladolid", 6.9, v("Valladolid", "var_precio_alq"), 1),
    ("€/m² de alquiler (%)", "Barcelona", -2.1, v("Barcelona", "var_precio_alq"), 1),
    ("€/m² de alquiler (%)", "Palma", -3.8, v("Palma de Mallorca", "var_precio_alq"), 1),
    ("€/m² de alquiler (%)", "Córdoba (el informe dice: baja ligeramente)", None,
     v("Córdoba", "var_precio_alq"), 1),
    ("Venta", f"Ciudades con anuncios de venta entre +2 % y +7 % (de {N_CIUDADES}; "
     "el informe dice: la mayoría)", None, venta_2_7, 0),
    ("Totales 22 ciudades", "Anuncios de alquiler (diferencia)", -3420,
     tabla["dif_anuncios_alq"].sum(), 0),
    ("Totales 22 ciudades", "Anuncios de venta (diferencia)", 3405,
     tabla["dif_anuncios_venta"].sum(), 0),
    ("Madrid", "Anuncios de alquiler (diferencia)", -963, v("Madrid", "dif_anuncios_alq"), 0),
    ("Madrid", "Anuncios de alquiler (%)", -10.5, v("Madrid", "var_anuncios_alq"), 1),
    ("Madrid", "Anuncios de venta (diferencia)", 1016, v("Madrid", "dif_anuncios_venta"), 0),
    ("Madrid", "Anuncios de venta (%)", 5.4, v("Madrid", "var_anuncios_venta"), 1),
    ("Spearman", "Alquiler frente a venta, en % (ρ)", 0.07, rho_venta, 2),
    ("Spearman", "Alquiler frente a venta, en % (p)", 0.77, p_venta, 2),
    ("Spearman", "Alquiler frente a venta por cada 100 anuncios iniciales (ρ)",
     0.25, rho_por100, 2),
    ("Spearman", "Alquiler frente a venta por cada 100 anuncios iniciales (p)",
     0.26, p_por100, 2),
    ("Spearman", "Anuncios de alquiler frente a €/m² de alquiler (ρ)",
     RHO_INFORME, rho_precio, 2),
    ("Spearman", "Anuncios de alquiler frente a €/m² de alquiler (p)",
     P_INFORME, p_precio, 2),
    ("Madrid otoños", "2026: €/m² el 6 oct", 29.43, madrid_inicio, 2),
    ("Madrid otoños", "2026: €/m² al final", 30.32, madrid_final, 2),
    ("Madrid otoños", "2026: variación (%)", 3.0, madrid_2026, 1),
    ("Madrid otoños", "2007-2025: cambio mínimo sep-oct (%)", -1.9, otonos.min(), 1),
    ("Madrid otoños", "2007-2025: cambio máximo sep-oct (%)", 1.1, otonos.max(), 1),
    ("Madrid otoños", "2007-2025: mediana sep-oct (%)", 0.0, otonos.median(), 1),
    ("Madrid otoños", "Número de otoños", 19, len(otonos), 0),
]

filas = []
for apartado, cifra, anterior, nuevo, decimales in cifras:
    nuevo_redondeado = round(float(nuevo), decimales)
    if anterior is None:
        cambia = "revisar a mano"
    elif abs(nuevo_redondeado - anterior) > 0.1 + 1e-9:
        cambia = "SÍ"
    else:
        cambia = "no"
    filas.append({
        "Apartado": apartado,
        "Cifra": cifra,
        "Valor anterior": anterior,
        "Valor nuevo": nuevo_redondeado,
        "Valor nuevo sin redondear": round(float(nuevo), 4),
        "Cambia más de 0,1": cambia,
    })

cifras_df = pd.DataFrame(filas).set_index("Apartado")
guardar_csv(cifras_df, "cifras_informe.csv")

print("\n--- Cifras del informe ---")
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)
print(cifras_df.to_string())
print(f"\nFinal del periodo usado: media del {TEXTO_FINAL}")
