# api/process_sales.py
import pandas as pd
import json
import io

def process_sales_data(file_content):
    # Usar io.BytesIO para leer el contenido binario del archivo Excel
    try:
        # pd.read_excel espera un objeto tipo archivo binario
        df = pd.read_excel(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Error al leer el archivo Excel. Asegúrate de que el formato sea correcto y que es un .xlsx válido: {e}")

    # Verificar si las columnas esperadas existen
    if 'Cliente' not in df.columns or 'Productos' not in df.columns:
        raise ValueError("El archivo Excel debe contener las columnas 'Cliente' y 'Productos'.")

    product_counts = {}
    processed_data = []

    # Iterar a través de cada fila para extraer productos y contarlos
    for index, row in df.iterrows():
        customer_name = str(row['Cliente']) # Asegurar que el nombre del cliente sea una cadena
        # Asegurar que la columna de productos sea una cadena, manejando NaN si es necesario
        products_str = str(row['Productos']) if pd.notna(row['Productos']) else ""

        current_row_products = {'Cliente': customer_name}

        # Dividir la cadena de productos en elementos individuales
        # Solo si products_str no está vacío
        product_list = products_str.split(',') if products_str else []

        for product_item in product_list:
            # Limpiar el string del producto (eliminar "1x ", espacios, SKU)
            cleaned_product = product_item.replace('1x ', '').split('(SKU:')[0].strip()

            if cleaned_product:  # Asegurar que el producto limpio no esté vacío
                # Actualizar el recuento total del producto
                product_counts[cleaned_product] = product_counts.get(cleaned_product, 0) + 1

                # Marcar el producto como presente para el cliente actual
                current_row_products[cleaned_product] = 1  # 1 indica presencia

        processed_data.append(current_row_products)

    # Asegurar que todas las columnas de productos estén presentes en todas las filas
    # y rellenar con 0 si un producto no estuvo presente para un cliente
    all_product_names = list(product_counts.keys())
    final_processed_data = []
    for row_data in processed_data:
        new_row = {'Cliente': row_data['Cliente']}
        for product_name in all_product_names:
            new_row[product_name] = row_data.get(product_name, 0) # Usa .get() con valor por defecto 0
        final_processed_data.append(new_row)

    # Crear un nuevo DataFrame a partir de los datos procesados
    products_df = pd.DataFrame(final_processed_data)

    # Reordenar columnas para tener 'Cliente' primero, luego productos
    cols = ['Cliente'] + [col for col in products_df.columns if col != 'Cliente']
    products_df = products_df[cols]

    # Crear un DataFrame para el recuento total de productos
    total_products_df = pd.DataFrame(product_counts.items(), columns=['Producto', 'Cantidad Total'])

    return {
        "productos_por_cliente": products_df.to_dict(orient='records'),
        "recuento_total_productos": total_products_df.to_dict(orient='records')
    }

def handler(request):
    try:
        if request.method == 'POST':
            # Leer el contenido binario del archivo desde el cuerpo de la solicitud
            # Para archivos XLSX, el body debe ser enviado como bytes (raw binary data)
            file_content = request.body # El body de la solicitud ya viene en bytes

            if not file_content:
                return json.dumps({"error": "No se recibió contenido de archivo Excel en el cuerpo de la solicitud."}), 400, {'Content-Type': 'application/json'}

            results = process_sales_data(file_content)

            return json.dumps(results), 200, {'Content-Type': 'application/json'}
        else:
            return json.dumps({"message": "Método no permitido. Por favor, envía una solicitud POST con el contenido del archivo Excel en el cuerpo."}), 405, {'Content-Type': 'application/json'}

    except ValueError as ve:
        # Errores específicos de validación de datos
        return json.dumps({"error": str(ve)}), 400, {'Content-Type': 'application/json'}
    except Exception as e:
        # Otros errores inesperados
        return json.dumps({"error": f"Error interno del servidor: {str(e)}"}), 500, {'Content-Type': 'application/json'}
