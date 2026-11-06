import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_skymar_2026'

def conectar_bd():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "Mysql@Senatec2026"),
        database=os.environ.get("DB_NAME", "proyecto_skymar"),
        port=int(os.environ.get("DB_PORT", 3306)),
        charset="utf8mb4"
    )

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# --- RUTAS DE SERVICIOS Y LUJO ---
@app.route("/areas-recreativas", methods=["GET"])
def areas_recreativas():
    return render_template("areas_recreativas.html")

@app.route("/buffet", methods=["GET"])
def buffet():
    return render_template("buffet.html")

@app.route("/turismo-extranjeros", methods=["GET"])
def turismo_extranjeros():
    return render_template("turismo_extranjeros.html")

@app.route("/verificar_disponibilidad", methods=["POST"])
def verificar_disponibilidad():
    try:
        nombre = request.form.get("nombreCliente")
        correo = request.form.get("correoCliente")
        telefono = request.form.get("telefonoCliente")
        entrada = request.form.get("entrada")
        salida = request.form.get("salida")
        huespedes = int(request.form.get("huespedes"))
        tipo_habitacion = request.form.get("tipo")

        # Calcular número de noches de estancia
        d_entrada = datetime.strptime(entrada, "%Y-%m-%d")
        d_salida = datetime.strptime(salida, "%Y-%m-%d")
        noches = (d_salida - d_entrada).days

        if noches <= 0:
            flash("La fecha de salida debe ser posterior a la fecha de entrada.", "danger")
            return redirect(url_for('index'))

        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)

        if tipo_habitacion == "Cualquiera":
            cursor.execute("SELECT * FROM habitacion WHERE estado = 'Disponible' AND capacidad >= %s LIMIT 1", (huespedes,))
        else:
            cursor.execute("SELECT * FROM habitacion WHERE tipo = %s AND estado = 'Disponible' AND capacidad >= %s LIMIT 1", (tipo_habitacion, huespedes))
        
        habitacion = cursor.fetchone()
        
        if not habitacion:
            cursor.close()
            conexion.close()
            return render_template("no_disponible.html")

        # Calcular precio total basado en el número de noches
        precio_noche = float(habitacion['precio'])
        total_pagar = precio_noche * noches

        cursor.close()
        conexion.close()

        # Determinar si incluye desayuno automático (Deluxe, Familiar y Suite)
        desayuno_incluido = True if habitacion.get('tipo') in ['Deluxe', 'Familiar', 'Suite'] else False

        # Guardar en sesión para usarlo al confirmar el pago
        session['datos_reserva'] = {
            'nombre': nombre, 'correo': correo, 'telefono': telefono,
            'entrada': entrada, 'salida': salida, 'huespedes': huespedes, 
            'tipo_habitacion': tipo_habitacion, 'noches': noches, 
            'total_pagar': total_pagar, 'desayuno_incluido': desayuno_incluido
        }

        return render_template("disponible.html", habitacion=habitacion, noches=noches, total_pagar=total_pagar, desayuno_incluido=desayuno_incluido)

    except Exception as e:
        flash(f"Error al verificar disponibilidad: {e}", "danger")
        return redirect(url_for('index'))

@app.route("/confirmar_reserva", methods=["POST"])
def confirmar_reserva():
    try:
        metodo_pago = request.form.get("metodo_pago")
        detalle_pago = request.form.get("tarjeta_numero", "N/A")
        id_habitacion = request.form.get("id_habitacion")
        datos = session.get('datos_reserva')

        if not datos:
            flash("La sesión ha expirado o no hay datos de reserva.", "danger")
            return redirect(url_for('index'))

        conexion = conectar_bd()
        cursor = conexion.cursor()

        # 1. Registrar al cliente
        sql_cliente = "INSERT INTO cliente (nombre, telefono, correo) VALUES (%s, %s, %s)"
        cursor.execute(sql_cliente, (datos['nombre'], datos['telefono'], datos['correo']))
        id_cliente = cursor.lastrowid

        # 2. Registrar la reserva con el total y referencia
        sql_reserva = """
            INSERT INTO reserva (fecha_reserva, fecha_entrada, fecha_salida, huespedes, estado, metodo_pago, total_pagar, referencia_pago, id_cliente, id_habitacion)
            VALUES (NOW(), %s, %s, %s, 'Confirmada', %s, %s, %s, %s, %s)
        """
        
        limpio_detalle = detalle_pago.replace(" ", "")
        sufijo = limpio_detalle[-4:] if len(limpio_detalle) >= 4 else limpio_detalle
        referencia = f"{metodo_pago[:3].upper()}-{sufijo}"

        cursor.execute(sql_reserva, (
            datos['entrada'], datos['salida'], datos['huespedes'], 
            metodo_pago, datos['total_pagar'], referencia, id_cliente, id_habitacion
        ))
        
        # GUARDAR ID DE LA ÚLTIMA RESERVA PARA CALIFICACIÓN DIRECTA
        session['id_ultima_reserva'] = cursor.lastrowid

        # 3. Actualizar estado de la habitación a Ocupada
        cursor.execute("UPDATE habitacion SET estado = 'Ocupada' WHERE id_habitacion = %s", (id_habitacion,))

        conexion.commit()
        cursor.close()
        conexion.close()

        return render_template("exito_reserva.html")

    except Exception as e:
        flash(f"Error al confirmar reserva: {e}", "danger")
        return redirect(url_for('index'))

# --- NUEVA RUTA: CALIFICAR DIRECTAMENTE EL SERVICIO DE LA RESERVA RECIÉN HECHA ---
@app.route("/calificar_servicio_actual", methods=["GET", "POST"])
def calificar_servicio_actual():
    id_reserva = session.get('id_ultima_reserva')
    
    if not id_reserva:
        flash("No hay una reserva reciente en la sesión para calificar.", "warning")
        return redirect(url_for('index'))

    if request.method == "POST":
        try:
            atencion = request.form.get("atencion_cliente")
            comida = request.form.get("servicio_comida")
            comentario = request.form.get("comentario")

            conexion = conectar_bd()
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT INTO calificacion (id_reserva, atencion_cliente, servicio_comida, comentario) VALUES (%s, %s, %s, %s)", 
                (id_reserva, atencion, comida, comentario)
            )
            conexion.commit()
            cursor.close()
            conexion.close()

            flash("¡Gracias por calificar el servicio de tu reserva!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error al guardar la calificación: {e}", "danger")
            return redirect(url_for('index'))

    # Obtener detalles de la última reserva para mostrarlos en pantalla
    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.*, c.nombre as cliente_nombre, h.tipo, h.numero_habitacion 
        FROM reserva r 
        JOIN cliente c ON r.id_cliente = c.id_cliente 
        JOIN habitacion h ON r.id_habitacion = h.id_habitacion 
        WHERE r.id_reserva = %s
    """, (id_reserva,))
    reserva = cursor.fetchone()
    cursor.close()
    conexion.close()

    return render_template("calificar_servicio.html", reserva=reserva)

# --- NUEVO FLUJO DE CALIFICACIÓN Y BÚSQUEDA DE RESERVAS ---

@app.route("/calificar", methods=["GET"])
def calificar():
    return render_template("calificar.html", paso="buscar", reservas=None)

@app.route("/buscar_reserva_calificar", methods=["POST"])
def buscar_reserva_calificar():
    try:
        termino = request.form.get("termino_busqueda")
        
        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)
        
        query = """
            SELECT r.*, c.nombre as cliente_nombre, h.tipo, h.numero_habitacion 
            FROM reserva r 
            JOIN cliente c ON r.id_cliente = c.id_cliente 
            JOIN habitacion h ON r.id_habitacion = h.id_habitacion 
            WHERE c.nombre LIKE %s OR r.referencia_pago LIKE %s
        """
        cursor.execute(query, (f"%{termino}%", f"%{termino}%"))
        reservas = cursor.fetchall()
        
        cursor.close()
        conexion.close()

        if not reservas:
            flash("No se encontraron reservas asociadas a ese nombre o referencia.", "warning")
            return redirect(url_for('calificar'))

        return render_template("calificar.html", paso="seleccionar", reservas=reservas)

    except Exception as e:
        flash(f"Error en la búsqueda: {e}", "danger")
        return redirect(url_for('calificar'))

@app.route("/guardar_calificacion_id/<int:id_reserva>", methods=["POST"])
def guardar_calificacion_id(id_reserva):
    try:
        atencion = request.form.get("atencion_cliente")
        comida = request.form.get("servicio_comida")
        comentario = request.form.get("comentario")

        conexion = conectar_bd()
        cursor = conexion.cursor()
        
        cursor.execute(
            "INSERT INTO calificacion (id_reserva, atencion_cliente, servicio_comida, comentario) VALUES (%s, %s, %s, %s)", 
            (id_reserva, atencion, comida, comentario)
        )
        
        conexion.commit()
        cursor.close()
        conexion.close()

        flash("¡Gracias por tu reseña! Ha sido guardada con éxito en la base de datos.", "success")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error al guardar la calificación: {e}", "danger")
        return redirect(url_for('index'))

# --- PANEL DE ADMINISTRADOR Y MULTI-ROLES ---

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("password")

        conexion = conectar_bd()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuario WHERE correo = %s AND password = %s AND rol IN ('admin', 'administrador', 'recepcion', 'conserjeria', 'mantenimiento')", 
            (correo, password)
        )
        usuario = cursor.fetchone()
        cursor.close()
        conexion.close()

        if usuario:
            session['admin_logueado'] = True
            session['usuario_rol'] = usuario['rol']
            session['usuario_nombre'] = usuario.get('nombre', 'Usuario')
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Credenciales incorrectas o rol no autorizado.", "danger")
            return redirect(url_for('admin_login'))

    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('admin_logueado'):
        return redirect(url_for('admin_login'))

    conexion = conectar_bd()
    cursor = conexion.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT r.*, c.nombre as cliente_nombre, c.telefono, c.correo, h.numero_habitacion, h.tipo 
        FROM reserva r 
        JOIN cliente c ON r.id_cliente = c.id_cliente 
        JOIN habitacion h ON r.id_habitacion = h.id_habitacion
    """)
    reservas = cursor.fetchall()

    cursor.execute("SELECT * FROM habitacion")
    habitaciones = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template("admin_dashboard.html", reservas=reservas, habitaciones=habitaciones, rol_actual=session.get('usuario_rol'))

@app.route("/admin/editar_habitacion/<int:id_habitacion>", methods=["POST"])
def editar_habitacion(id_habitacion):
    if not session.get('admin_logueado'):
        return redirect(url_for('admin_login'))

    estado = request.form.get("estado")
    precio = request.form.get("precio")

    conexion = conectar_bd()
    cursor = conexion.cursor()
    cursor.execute("UPDATE habitacion SET estado = %s, precio = %s WHERE id_habitacion = %s", (estado, precio, id_habitacion))
    conexion.commit()
    cursor.close()
    conexion.close()

    flash("Habitación actualizada con éxito.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/eliminar_reserva/<int:id_reserva>", methods=["POST"])
def eliminar_reserva(id_reserva):
    if not session.get('admin_logueado'):
        return redirect(url_for('admin_login'))

    conexion = conectar_bd()
    cursor = conexion.cursor()
    
    # 1. Obtener y liberar la habitación asociada
    cursor.execute("SELECT id_habitacion FROM reserva WHERE id_reserva = %s", (id_reserva,))
    res = cursor.fetchone()
    if res:
        id_hab = res[0]
        cursor.execute("UPDATE habitacion SET estado = 'Disponible' WHERE id_habitacion = %s", (id_hab,))

    # 2. Borrar primero las calificaciones/reseñas vinculadas a esta reserva
    cursor.execute("DELETE FROM calificacion WHERE id_reserva = %s", (id_reserva,))

    # 3. Eliminar la reserva con seguridad
    cursor.execute("DELETE FROM reserva WHERE id_reserva = %s", (id_reserva,))
    
    conexion.commit()
    cursor.close()
    conexion.close()

    flash("Reserva eliminada y habitación liberada correctamente.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logueado', None)
    session.pop('usuario_rol', None)
    session.pop('usuario_nombre', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)