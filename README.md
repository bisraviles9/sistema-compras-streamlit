# Sistema de compras e inventario (demo pública)

App en Streamlit para registrar proveedores, productos y compras; controlar inventario y descargar reportes CSV.

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app_streamlit.py
```

La aplicación crea `compras.db` y la carpeta `reportes` junto al programa. No ingreses información real ni confidencial en la demo pública. En Streamlit Community Cloud, el archivo SQLite local es temporal y puede reiniciarse.
