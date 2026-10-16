

# Datos de ejemplo para el proyecto: se cargan una sola vez si la base está vacía.
# Los nombres, teléfonos, productos e importes son ficticios.
if not consultar("SELECT COUNT(*) AS total FROM compras")[0]["total"] and not consultar("SELECT COUNT(*) AS total FROM proveedores")[0]["total"]:
    from datetime import timedelta

    with conectar() as db:
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
        fecha_anterior = (hoy.replace(day=1) - timedelta(days=1)).replace(day=10).isoformat()
        fecha_actual = hoy.replace(day=min(5, hoy.day)).isoformat()
        compra_1 = db.execute(
            "INSERT INTO compras(proveedor_id, fecha, observacion) VALUES (?, ?, ?)",
            (distribuidora, fecha_anterior, "Ejemplo: reposición de suministros"),
        ).lastrowid
        db.executemany(
            "INSERT INTO detalle_compra(compra_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
            [(compra_1, papel, 15, 5.50), (compra_1, toner, 1, 29.90)],
        )
        db.execute("UPDATE productos SET stock = stock + 15 WHERE id = ?", (papel,))
        db.execute("UPDATE productos SET stock = stock + 1 WHERE id = ?", (toner,))
        compra_2 = db.execute(
            "INSERT INTO compras(proveedor_id, fecha, observacion) VALUES (?, ?, ?)",
            (papeleria, fecha_actual, "Ejemplo: compra mensual de papelería"),
        ).lastrowid
        db.executemany(
            "INSERT INTO detalle_compra(compra_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
            [(compra_2, cuaderno, 12, 2.40), (compra_2, marcadores, 10, 1.25)],
        )
        db.execute("UPDATE productos SET stock = stock + 12 WHERE id = ?", (cuaderno,))
        db.execute("UPDATE productos SET stock = stock + 10 WHERE id = ?", (marcadores,))
    st.rerun()
