import csv
import io
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Comparte la misma base de datos que sistema_compras.py si ambos archivos
# están en la misma carpeta.
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "compras.db"
REPORT_DIR = BASE_DIR / "reportes"

st.set_page_config(page_title="Compras e inventario", page_icon="🛒", layout="wide")


def conectar():
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def iniciar_base():
    REPORT_DIR.mkdir(exist_ok=True)
    with conectar() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                contacto TEXT DEFAULT '', telefono TEXT DEFAULT '', email TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                categoria TEXT DEFAULT '',
                stock REAL NOT NULL DEFAULT 0 CHECK(stock >= 0),
                stock_minimo REAL NOT NULL DEFAULT 0 CHECK(stock_minimo >= 0)
            );
            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                observacion TEXT DEFAULT '',
                FOREIGN KEY(proveedor_id) REFERENCES proveedores(id)
            );
            CREATE TABLE IF NOT EXISTS detalle_compra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compra_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad REAL NOT NULL CHECK(cantidad > 0),
                precio_unitario REAL NOT NULL CHECK(precio_unitario >= 0),
                FOREIGN KEY(compra_id) REFERENCES compras(id),
                FOREIGN KEY(producto_id) REFERENCES productos(id)
            );
        """)
        # Carga este ejemplo ficticio una sola vez, solo si la base está vacía.
        proveedores = db.execute("SELECT COUNT(*) FROM proveedores").fetchone()[0]
        productos = db.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
        compras = db.execute("SELECT COUNT(*) FROM compras").fetchone()[0]
        if proveedores == 0 and productos == 0 and compras == 0:
            distribuidora = db.execute(
                "INSERT INTO proveedores(nombre, contacto, telefono, email) VALUES (?, ?, ?, ?)",
                ("Distribuidora Andina", "Área de ventas", "0990000000", "ventas@andina.example"),
            ).lastrowid
            papeleria = db.execute(
                "INSERT INTO proveedores(nombre, contacto, telefono, email) VALUES (?, ?, ?, ?)",
                ("Papelería Central", "Atención al cliente", "0980000000", "contacto@papeleriacentral.example"),
            ).lastrowid
            papel = db.execute(
                "INSERT INTO productos(nombre, categoria, stock, stock_minimo) VALUES (?, ?, ?, ?)",
                ("Papel bond A4 (resma)", "Papelería", 5, 10),
            ).lastrowid
            toner = db.execute(
                "INSERT INTO productos(nombre, categoria, stock, stock_minimo) VALUES (?, ?, ?, ?)",
                ("Tóner láser", "Suministros de oficina", 0, 3),
            ).lastrowid
            cuaderno = db.execute(
                "INSERT INTO productos(nombre, categoria, stock, stock_minimo) VALUES (?, ?, ?, ?)",
                ("Cuaderno universitario", "Papelería", 0, 8),
            ).lastrowid
            marcadores = db.execute(
                "INSERT INTO productos(nombre, categoria, stock, stock_minimo) VALUES (?, ?, ?, ?)",
                ("Marcadores (paquete)", "Papelería", 3, 5),
            ).lastrowid
            hoy = date.today()
            fecha_mes_anterior = (hoy.replace(day=1) - timedelta(days=1)).replace(day=10)
            fecha_mes_actual = hoy.replace(day=min(5, hoy.day))
            compra_1 = db.execute(
                "INSERT INTO compras(proveedor_id, fecha, observacion) VALUES (?, ?, ?)",
                (distribuidora, fecha_mes_anterior.isoformat(), "Ejemplo: reposición de suministros"),
            ).lastrowid
            db.executemany(
                "INSERT INTO detalle_compra(compra_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                [(compra_1, papel, 15, 5.50), (compra_1, toner, 1, 29.90)],
            )
            db.execute("UPDATE productos SET stock = stock + 15 WHERE id = ?", (papel,))
            db.execute("UPDATE productos SET stock = stock + 1 WHERE id = ?", (toner,))
            compra_2 = db.execute(
                "INSERT INTO compras(proveedor_id, fecha, observacion) VALUES (?, ?, ?)",
                (papeleria, fecha_mes_actual.isoformat(), "Ejemplo: compra mensual de papelería"),
            ).lastrowid
            db.executemany(
                "INSERT INTO detalle_compra(compra_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                [(compra_2, cuaderno, 12, 2.40), (compra_2, marcadores, 10, 1.25)],
            )
            db.execute("UPDATE productos SET stock = stock + 12 WHERE id = ?", (cuaderno,))
            db.execute("UPDATE productos SET stock = stock + 10 WHERE id = ?", (marcadores,))


def consultar(sql, params=()):
    with conectar() as db:
        return [dict(fila) for fila in db.execute(sql, params).fetchall()]


def csv_bytes(rows, columns):
    archivo = io.StringIO()
    writer = csv.writer(archivo)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])
    return archivo.getvalue().encode("utf-8-sig")


def obtener_reportes():
    detalle = consultar("""
        SELECT c.id AS compra, c.fecha, p.nombre AS proveedor, pr.nombre AS producto,
               d.cantidad, d.precio_unitario,
               ROUND(d.cantidad * d.precio_unitario, 2) AS subtotal, c.observacion
        FROM compras c
        JOIN proveedores p ON p.id = c.proveedor_id
        JOIN detalle_compra d ON d.compra_id = c.id
        JOIN productos pr ON pr.id = d.producto_id
        ORDER BY c.fecha DESC, c.id DESC
    """)
    inventario = consultar("SELECT nombre, categoria, stock, stock_minimo FROM productos ORDER BY nombre")
    mensual = consultar("""
        SELECT substr(c.fecha, 1, 7) AS mes, COUNT(DISTINCT c.id) AS numero_compras,
               ROUND(SUM(d.cantidad * d.precio_unitario), 2) AS total
        FROM compras c JOIN detalle_compra d ON d.compra_id = c.id
        GROUP BY substr(c.fecha, 1, 7) ORDER BY mes DESC
    """)
    return detalle, inventario, mensual


def guardar_reportes():
    detalle, inventario, mensual = obtener_reportes()
    definiciones = [
        ("compras_detalle.csv", detalle,
         ["compra", "fecha", "proveedor", "producto", "cantidad", "precio_unitario", "subtotal", "observacion"]),
        ("inventario.csv", inventario, ["nombre", "categoria", "stock", "stock_minimo"]),
        ("resumen_mensual.csv", mensual, ["mes", "numero_compras", "total"]),
    ]
    for nombre, filas, columnas in definiciones:
        (REPORT_DIR / nombre).write_bytes(csv_bytes(filas, columnas))


iniciar_base()
st.title("🛒 Sistema de compras e inventario")
st.caption("Registra compras, controla existencias y consulta reportes desde el navegador.")
st.warning("Demo pública: no ingreses información real ni confidencial. Las personas con acceso al enlace pueden ver y modificar los datos de esta demo; la base local también puede reiniciarse.")

tab_resumen, tab_compra, tab_productos, tab_proveedores, tab_reportes = st.tabs(
    ["📊 Resumen", "🧾 Registrar compra", "📦 Productos", "🏢 Proveedores", "📈 Reportes"]
)

with tab_resumen:
    hoy = date.today()
    mes = hoy.strftime("%Y-%m")
    general = consultar("""
        SELECT COUNT(DISTINCT c.id) AS compras,
               COALESCE(SUM(d.cantidad * d.precio_unitario), 0) AS total
        FROM compras c LEFT JOIN detalle_compra d ON d.compra_id = c.id
    """)[0]
    mensual = consultar("""
        SELECT COUNT(DISTINCT c.id) AS compras,
               COALESCE(SUM(d.cantidad * d.precio_unitario), 0) AS total
        FROM compras c LEFT JOIN detalle_compra d ON d.compra_id = c.id
        WHERE substr(c.fecha, 1, 7) = ?
    """, (mes,))[0]
    stock_bajo = consultar("SELECT nombre, categoria, stock, stock_minimo FROM productos WHERE stock <= stock_minimo ORDER BY nombre")
    c1, c2, c3 = st.columns(3)
    c1.metric("Compras registradas", general["compras"])
    c2.metric("Total acumulado", f"${general['total']:,.2f}")
    c3.metric(f"Total de {mes}", f"${mensual['total']:,.2f}")
    st.subheader("Productos por reponer")
    if stock_bajo:
        st.dataframe(pd.DataFrame(stock_bajo), use_container_width=True, hide_index=True)
    else:
        st.success("No hay productos por debajo del stock mínimo.")
    mensual_rows = obtener_reportes()[2]
    if mensual_rows:
        st.subheader("Compras por mes")
        datos = pd.DataFrame(mensual_rows).sort_values("mes")
        st.bar_chart(datos, x="mes", y="total")

with tab_compra:
    proveedores = consultar("SELECT id, nombre FROM proveedores ORDER BY nombre")
    productos = consultar("SELECT id, nombre, stock FROM productos ORDER BY nombre")
    if not proveedores or not productos:
        st.info("Para registrar compras, primero agrega al menos un proveedor y un producto en sus pestañas.")
    else:
        proveedor_map = {p["nombre"]: p["id"] for p in proveedores}
        producto_map = {f"{p['nombre']} (stock: {p['stock']:g})": p["id"] for p in productos}
        if "carrito_compras" not in st.session_state:
            st.session_state.carrito_compras = []

        st.subheader("Datos de la compra")
        a, b = st.columns(2)
        proveedor_nombre = a.selectbox("Proveedor", list(proveedor_map))
        fecha_compra = b.date_input("Fecha", value=date.today())
        observacion = st.text_input("Observación (opcional)")

        st.subheader("Añadir artículos")
        with st.form("agregar_articulo", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            producto_label = c1.selectbox("Producto", list(producto_map))
            cantidad = c2.number_input("Cantidad", min_value=0.01, value=1.0, step=1.0)
            precio = c3.number_input("Precio unitario ($)", min_value=0.0, value=0.0, step=0.5)
            agregar = st.form_submit_button("Añadir a la compra")
        if agregar:
            st.session_state.carrito_compras.append({
                "producto_id": producto_map[producto_label],
                "producto": producto_label.split(" (stock:")[0],
                "cantidad": float(cantidad),
                "precio_unitario": float(precio),
                "subtotal": float(cantidad) * float(precio),
            })

        carrito = st.session_state.carrito_compras
        if carrito:
            st.dataframe(pd.DataFrame(carrito)[["producto", "cantidad", "precio_unitario", "subtotal"]],
                         use_container_width=True, hide_index=True)
            st.markdown(f"**Total: ${sum(x['subtotal'] for x in carrito):,.2f}**")
            c_guardar, c_vaciar = st.columns(2)
            with c_guardar:
                guardar = st.button("Guardar compra y actualizar inventario", type="primary", use_container_width=True)
            with c_vaciar:
                vaciar = st.button("Vaciar artículos", use_container_width=True)
            if vaciar:
                st.session_state.carrito_compras = []
                st.rerun()
            if guardar:
                try:
                    with conectar() as db:
                        cur = db.execute(
                            "INSERT INTO compras(proveedor_id, fecha, observacion) VALUES (?, ?, ?)",
                            (proveedor_map[proveedor_nombre], fecha_compra.isoformat(), observacion.strip()),
                        )
                        compra_id = cur.lastrowid
                        for item in carrito:
                            db.execute("""INSERT INTO detalle_compra
                                (compra_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)""",
                                (compra_id, item["producto_id"], item["cantidad"], item["precio_unitario"]))
                            db.execute("UPDATE productos SET stock = stock + ? WHERE id = ?",
                                       (item["cantidad"], item["producto_id"]))
                    st.session_state.carrito_compras = []
                    guardar_reportes()
                    st.success(f"Compra #{compra_id} guardada. Inventario y reportes actualizados.")
                    st.rerun()
                except sqlite3.Error as exc:
                    st.error(f"No se pudo guardar la compra: {exc}")

with tab_productos:
    st.subheader("Registrar producto")
    with st.form("nuevo_producto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nombre_producto = c1.text_input("Nombre del producto*")
        categoria = c2.text_input("Categoría")
        c3, c4 = st.columns(2)
        stock_inicial = c3.number_input("Stock inicial", min_value=0.0, value=0.0, step=1.0)
        stock_minimo = c4.number_input("Stock mínimo para alerta", min_value=0.0, value=0.0, step=1.0)
        enviar_producto = st.form_submit_button("Guardar producto")
    if enviar_producto:
        if not nombre_producto.strip():
            st.error("Escribe el nombre del producto.")
        else:
            try:
                with conectar() as db:
                    db.execute("INSERT INTO productos(nombre, categoria, stock, stock_minimo) VALUES (?, ?, ?, ?)",
                               (nombre_producto.strip(), categoria.strip(), stock_inicial, stock_minimo))
                st.success("Producto guardado.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Ya existe un producto con ese nombre.")
    st.subheader("Inventario actual")
    productos_actuales = consultar("SELECT nombre, categoria, stock, stock_minimo FROM productos ORDER BY nombre")
    if productos_actuales:
        st.dataframe(pd.DataFrame(productos_actuales), use_container_width=True, hide_index=True)
    else:
        st.caption("Aún no hay productos registrados.")

with tab_proveedores:
    st.subheader("Registrar proveedor")
    with st.form("nuevo_proveedor", clear_on_submit=True):
        nombre_proveedor = st.text_input("Nombre del proveedor*")
        c1, c2, c3 = st.columns(3)
        contacto = c1.text_input("Persona de contacto")
        telefono = c2.text_input("Teléfono")
        email = c3.text_input("Email")
        enviar_proveedor = st.form_submit_button("Guardar proveedor")
    if enviar_proveedor:
        if not nombre_proveedor.strip():
            st.error("Escribe el nombre del proveedor.")
        else:
            try:
                with conectar() as db:
                    db.execute("INSERT INTO proveedores(nombre, contacto, telefono, email) VALUES (?, ?, ?, ?)",
                               (nombre_proveedor.strip(), contacto.strip(), telefono.strip(), email.strip()))
                st.success("Proveedor guardado.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Ya existe un proveedor con ese nombre.")
    st.subheader("Proveedores registrados")
    proveedores_actuales = consultar("SELECT nombre, contacto, telefono, email FROM proveedores ORDER BY nombre")
    if proveedores_actuales:
        st.dataframe(pd.DataFrame(proveedores_actuales), use_container_width=True, hide_index=True)
    else:
        st.caption("Aún no hay proveedores registrados.")

with tab_reportes:
    detalle, inventario, mensual = obtener_reportes()
    st.subheader("Descargar reportes")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Compras detalladas CSV", csv_bytes(detalle,
        ["compra", "fecha", "proveedor", "producto", "cantidad", "precio_unitario", "subtotal", "observacion"]),
        "compras_detalle.csv", "text/csv", use_container_width=True)
    c2.download_button("Inventario CSV", csv_bytes(inventario,
        ["nombre", "categoria", "stock", "stock_minimo"]),
        "inventario.csv", "text/csv", use_container_width=True)
    c3.download_button("Resumen mensual CSV", csv_bytes(mensual,
        ["mes", "numero_compras", "total"]),
        "resumen_mensual.csv", "text/csv", use_container_width=True)
    st.caption("Los reportes también se guardan en la carpeta reportes al registrar una compra.")
    st.subheader("Historial de compras")
    if detalle:
        st.dataframe(pd.DataFrame(detalle), use_container_width=True, hide_index=True)
    else:
        st.caption("Aún no hay compras registradas.")
