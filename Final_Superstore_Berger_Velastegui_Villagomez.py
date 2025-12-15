# Librerías necesarias

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import os


# CONFIGURACIÓN DE PÁGINA

st.set_page_config(
    page_title="Superstore Analytics – Descuentos vs Rentabilidad",
    page_icon="📊",
    layout="wide"
)


# PALETA CORPORATIVA

CORP = {
    "blue": "#1F4E79",      # Alto profit
    "neutral": "#E5E7E9",   # Cerca de 0
    "red": "#D64541",       # Pérdida
    "teal": "#2E86AB"
}

# Escala semántica: rojo (pérdida) -> neutro -> azul (alto profit)
PROFIT_SCALE = [CORP["red"], CORP["neutral"], CORP["blue"]]

def data_cleaning(df):
    df = df.drop_duplicates()
    # 3.3 Conversión de tipos (intento automático)
    for col in df.columns:
        # intentar convertir a numérico
        if df[col].dtype == object:
            # try numeric
            try:
                df[col] = pd.to_numeric(df[col].str.replace('[$,]', '', regex=True))
                continue
            except Exception:
                pass
            # try datetime
            try:
                df[col] = pd.to_datetime(df[col])
                continue
            except Exception:
                pass
    
    return df

# CARGA DE DATOS
@st.cache_data
def data_loader(nombre_archivo):
    # 1. Definimos dónde empezar a buscar (Carpeta del Usuario)
    ruta_base = Path.home() 
    # 2. os.walk recorre todo el árbol de directorios hacia abajo
    for root, dirs, files in os.walk(ruta_base):
        if nombre_archivo in files:
            ruta_completa = os.path.join(root, nombre_archivo)
            df = data_cleaning(pd.read_csv(ruta_completa, encoding="latin1"))

            if "Order Date" in df.columns:
                df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")

                for col in ["Sales", "Profit", "Discount", "Quantity"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

                for col in ["Region", "State", "City", "Category", "Sub-Category", "Segment", "Customer ID"]:
                    if col in df.columns:
                        df[col] = df[col].astype(str).fillna("Unknown")

                return df
            
    # 3. Si termina el bucle y no lo encontró
    raise FileNotFoundError(f"No se encontró '{nombre_archivo}' en ninguna carpeta dentro de {ruta_base}")

df_full = data_loader("superstore.csv")

# SIDEBAR – FILTROS GLOBALES

st.sidebar.header("Filtros Globales")

regiones = st.sidebar.multiselect(
    "Región",
    options=sorted(df_full["Region"].unique()),
    default=sorted(df_full["Region"].unique())
)

categorias = st.sidebar.multiselect(
    "Categoría",
    options=sorted(df_full["Category"].unique()),
    default=sorted(df_full["Category"].unique())
)

subcats_all = sorted(df_full["Sub-Category"].unique())
subcats = st.sidebar.multiselect(
    "Sub-Categoría",
    options=subcats_all,
    default=subcats_all
)

dmin, dmax = float(df_full["Discount"].min()), float(df_full["Discount"].max())
discount_range = st.sidebar.slider(
    "Rango de descuento",
    min_value=dmin,
    max_value=dmax,
    value=(dmin, dmax),
    step=0.01
)

# DATA FILTRADA

df = df_full[
    (df_full["Region"].isin(regiones)) &
    (df_full["Category"].isin(categorias)) &
    (df_full["Sub-Category"].isin(subcats)) &
    (df_full["Discount"] >= discount_range[0]) &
    (df_full["Discount"] <= discount_range[1])
].copy()

if df.empty:
    st.warning("No hay datos para los filtros seleccionados. Ajusta los filtros en la barra lateral.")
    st.stop()


# TÍTULO + KPIs

st.title("Superstore Analytics: ¿Dónde los descuentos destruyen la rentabilidad?")
st.markdown("---")

total_sales = df["Sales"].sum()
total_profit = df["Profit"].sum()
avg_discount = df["Discount"].mean()
profit_margin = (total_profit / total_sales) if total_sales else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Sales", f"${total_sales:,.0f}")
k2.metric("Total Profit", f"${total_profit:,.0f}")
k3.metric("Avg Discount", f"{avg_discount:.1%}")
k4.metric("Profit Margin", f"{profit_margin:.1%}")

st.markdown("---")

# Escala global centrada en 0
max_abs = max(abs(float(df["Profit"].min())), abs(float(df["Profit"].max())))
if max_abs == 0:
    max_abs = 1.0

# Hallazgo rápido
reg_profit = df.groupby("Region", as_index=False)["Profit"].sum().sort_values("Profit")
worst_region = reg_profit.iloc[0]["Region"]
worst_region_profit = float(reg_profit.iloc[0]["Profit"])

sub_profit = df.groupby("Sub-Category", as_index=False)["Profit"].sum().sort_values("Profit")
worst_sub = sub_profit.iloc[0]["Sub-Category"]
worst_sub_profit = float(sub_profit.iloc[0]["Profit"])

st.info(
    f"📌 Dirección Financiera – Insight prioritario\n\n"
    f"La región Central presenta un deterioro de rentabilidad.\n\n"
    f"• Profit total de la región Central: ${worst_region_profit:,.0f}\n\n"
    f"• Subcategoría con mayor impacto negativo: Tables "
    f"(Profit: ${worst_sub_profit:,.0f})"
)


# TABS

tab1, tab2, tab3 = st.tabs([
    "1) Ventas vs Rentabilidad",
    "2) Descuentos",
    "3) Pérdidas estructurales"
])


# TAB 1 – Diagnóstico

with tab1:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("## Ventas altas no garantizan rentabilidad")
        st.caption("El tamaño muestra ventas; el color revela si esas ventas generan utilidad real.")

        sales_cat = (
            df.groupby("Category", as_index=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
            .sort_values("Sales", ascending=False)
        )

        fig = px.bar(
            sales_cat,
            x="Category",
            y="Sales",
            color="Profit",
            color_continuous_scale=PROFIT_SCALE,
            range_color=(-max_abs, max_abs),
            title="Categorías líderes en ventas pueden destruir margen",
            labels={
            "Category": "Categoría de Producto",
            "Sales": "Total de Ventas ($)"}
        )
        fig.update_layout(template="simple_white", coloraxis_showscale=False, title_x=0.02)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Insight:** si una categoría vende mucho y se tiñe de rojo, el crecimiento está “comprado” con margen.")

    with c2:
        st.markdown("## El profit se concentra en pocas categorías")
        st.caption("Cuando el profit se concentra, cualquier desviación en una categoría clave impacta el total.")

        profit_cat = (
            df.groupby("Category", as_index=False)["Profit"]
            .sum()
            .sort_values("Profit", ascending=False)
        )

        fig = px.bar(
            profit_cat,
            x="Category",
            y="Profit",
            color="Profit",
            color_continuous_scale=PROFIT_SCALE,
            range_color=(-max_abs, max_abs),
            title="Pocas categorías sostienen el margen total",
            labels={
            "Category": "Categoría de Producto",
            "Profit": "Ganancias Totales ($)"}
        )
        fig.update_layout(template="simple_white", coloraxis_showscale=False, title_x=0.02)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Acción:** proteger categorías azules con reglas estrictas de descuento y mix rentable.")


# TAB 2 – Descuentos

with tab2:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("## A mayor descuento, mayor riesgo de pérdida")
        st.caption("Puntos rojos concentrados en descuentos altos señalan deterioro de rentabilidad.")

        fig = px.scatter(
            df,
            x="Discount",
            y="Profit",
            size="Sales",
            color="Profit",
            color_continuous_scale=PROFIT_SCALE,
            range_color=(-max_abs, max_abs),
            hover_data=["Category", "Sub-Category", "Region", "State", "Sales", "Discount"],
            title="Descuentos elevados erosionan el profit",
            labels={
            "Discount": "Descuento  (%)",
            "Profit": "Ganancias Totales ($)"}
        )
        fig.update_layout(template="simple_white", coloraxis_showscale=False, title_x=0.02)
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Acción:** definir techo de descuento por subcategoría y aprobación al superarlo.")

    with c2:
        st.markdown("## Distribución de descuentos")
        st.caption("Si la masa se mueve a descuentos altos, el negocio está financiando volumen.")

        fig = px.histogram(
            df,
            x="Discount",
            nbins=20,
            title="Concentración de descuentos",
            labels={
            "Discount": "Descuento  (%)",
            "Count": "Conteo"}
        )
        fig.update_layout(template="simple_white", title_x=0.02)
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ✅ FIX 2 BONITO: Box + puntos SEMÁNTICOS sin eje numérico raro (y solo en TAB 2)
    st.markdown("## Variabilidad alta de profit = promo / operación inconsistente")
    st.caption("Azul = rentable · Rojo = pérdida · Línea 0 = break-even")

    fig_box = px.box(
        df,
        x="Category",
        y="Profit",
        points=False,
        title="La dispersión del profit por categoría sugiere inconsistencias en descuentos/operación"
    )
    fig_box.add_hline(y=0, line_dash="dash", line_color=CORP["neutral"])

    df_points = df.sample(n=min(2500, len(df)), random_state=42)

    fig_points = px.scatter(
        df_points,
        x="Category",
        y="Profit",
        color="Profit",
        color_continuous_scale=PROFIT_SCALE,
        range_color=(-max_abs, max_abs),
        opacity=0.55,
        hover_data=["Sub-Category", "Region", "State", "Sales", "Discount"],
        labels={
            "Profit": "Ganancias Totales ($)"}
    )
    fig_points.update_traces(marker=dict(size=6))

    for tr in fig_points.data:
        fig_box.add_trace(tr)

    fig_box.update_layout(
        template="simple_white",
        coloraxis_showscale=False,
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="", showgrid=False),
        height=420,
        margin=dict(l=10, r=10, t=60, b=10),
        title_x=0.02
    )

    st.plotly_chart(fig_box, use_container_width=True)
    st.markdown("**Acción:** si ves muchos puntos rojos bajo 0, ese mix requiere reglas y control de excepciones.")


# TAB 3 – Pérdidas estructurales

with tab3:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown("## El margen se drena en pocas subcategorías")
        st.caption("Tamaño = ventas; color = profit. Rojo grande = urgencia gerencial.")

        tree_df = (
            df.groupby(["Category", "Sub-Category"], as_index=False)
            .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"), Discount=("Discount", "mean"))
        )

        fig = px.treemap(
            tree_df,
            path=["Category", "Sub-Category"],
            values="Sales",
            color="Profit",
            color_continuous_scale=PROFIT_SCALE,
            range_color=(-max_abs, max_abs),
            hover_data={"Sales":":,.0f", "Profit":":,.0f", "Discount":":.1%"},
            title="Pocas subcategorías absorben la pérdida: intervenir primero donde estáel rojo",
            labels={
            "Profit": "Utilidad Real ($)"}
        )
        fig.update_layout(template="simple_white", title_x=0.02)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Acción:** top pérdidas → renegociar costos, ajustar precio o limitar descuento.")

    with c2:
        st.markdown("## El rojo se repite por estado: patrón estructural")
        st.caption("Ordenado por peor profit. Se muestran los estados más críticos para lectura ejecutiva.")

        pivot = (
            df.groupby(["State", "Region"])["Profit"]
            .sum()
            .unstack()
            .fillna(0)
        )

        # Ordenar por peor profit total
        pivot["Total"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("Total").drop(columns=["Total"])
        
        # Top N estados para que se vea bien
        MAX_STATES = 25
        if pivot.shape[0] > MAX_STATES:
            pivot = pivot.head(MAX_STATES)
        
        heat_h = max(420, 18 * pivot.shape[0])

        fig = px.imshow(
            pivot,
            color_continuous_scale=PROFIT_SCALE,
            zmin=-max_abs,
            zmax=max_abs,
            aspect="auto"
        )
        fig.update_layout(
            template="simple_white",
            height=heat_h,
            margin=dict(l=10, r=10, t=60, b=10),
            title_x=0.02
        )
        fig.update_xaxes(title="")
        fig.update_yaxes(title="")

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Acción:** en estados rojos: auditar logística, devoluciones y descuentos fuera de política.")


# RESUMEN EJECUTIVO

st.markdown("---")
st.subheader("Resumen Ejecutivo")

st.info(
    f"Hallazgo clave: la pérdida se concentra en **{worst_region}** y en **{worst_sub}**. \n\n"


    f"Recomendación: techo de descuento por subcategoría, aprobación al superarlo y plan de intervención "
    f"en estados con rojo recurrente."
)


