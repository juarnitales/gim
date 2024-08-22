import flet as ft
import mysql.connector
from datetime import datetime, timedelta
import base64
import os
import bcrypt
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de la base de datos
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'evolution_gym'
}

class CommonApp:
    def __init__(self):
        self.current_user = None
        self.conn = None
        self.cursor = None

    def connect_to_db(self):
        try:
            if self.conn is None or not self.conn.is_connected():
                self.conn = mysql.connector.connect(**db_config)
                self.cursor = self.conn.cursor(dictionary=True)
                logger.info("Conexión a la base de datos establecida con éxito.")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Error de conexión a la base de datos: {err}")
            return False

    def ensure_connection(self):
        if not self.connect_to_db():
            raise Exception("No se pudo establecer la conexión con la base de datos.")

    def close_db_connection(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Conexión a la base de datos cerrada.")

    def bytes_to_base64(self, bytes_data):
        return base64.b64encode(bytes_data).decode('utf-8')

    def show_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                return ft.Image(src_base64=self.bytes_to_base64(image_data))
        except FileNotFoundError:
            logger.warning(f"Imagen no encontrada: {image_path}")
            return ft.Text(f"Imagen no encontrada: {image_path}")

    async def login_view(self, page: ft.Page):
        username = ft.TextField(label="Nombre de usuario", width=300)
        password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)
        login_button = ft.ElevatedButton("Iniciar sesión", width=300)

        async def do_login(e):
            if not username.value or not password.value:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, completa todos los campos")))
                return

            try:
                self.ensure_connection()
                self.cursor.execute("SELECT * FROM users WHERE username = %s", (username.value,))
                user = self.cursor.fetchone()
                if user and bcrypt.checkpw(password.value.encode('utf-8'), user['password'].encode('utf-8')):
                    self.current_user = user
                    await page.go_async("/dashboard")
                else:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Credenciales incorrectas")))
            except mysql.connector.Error as err:
                logger.error(f"Error en el inicio de sesión: {err}")
                page.show_snack_bar(ft.SnackBar(ft.Text("Error en el inicio de sesión. Por favor, intenta de nuevo.")))

        login_button.on_click = do_login

        return ft.View(
            "/login",
            [
                ft.AppBar(title=ft.Text("Inicio de sesión")),
                ft.Column([
                    username,
                    password,
                    login_button
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ],
        )

    async def register_view(self, page: ft.Page):
        username = ft.TextField(label="Nombre de usuario", width=300)
        password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)
        confirm_password = ft.TextField(label="Confirmar contraseña", password=True, can_reveal_password=True, width=300)
        register_button = ft.ElevatedButton("Registrarse", width=300)

        async def do_register(e):
            if not username.value or not password.value or not confirm_password.value:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, completa todos los campos")))
                return

            if password.value != confirm_password.value:
                page.show_snack_bar(ft.SnackBar(ft.Text("Las contraseñas no coinciden")))
                return

            try:
                self.ensure_connection()
                hashed_password = bcrypt.hashpw(password.value.encode('utf-8'), bcrypt.gensalt())
                self.cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                                    (username.value, hashed_password))
                self.conn.commit()
                page.show_snack_bar(ft.SnackBar(ft.Text("Registro exitoso")))
                await page.go_async("/login")
            except mysql.connector.Error as err:
                logger.error(f"Error en el registro: {err}")
                page.show_snack_bar(ft.SnackBar(ft.Text("Error en el registro. Por favor, intenta de nuevo.")))

        register_button.on_click = do_register

        return ft.View(
            "/register",
            [
                ft.AppBar(title=ft.Text("Registro")),
                ft.Column([
                    username,
                    password,
                    confirm_password,
                    register_button
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ],
        )

    def upload_image(self, image_path, destination_folder):
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        
        file_name = os.path.basename(image_path)
        destination_path = os.path.join(destination_folder, file_name)
        
        try:
            with open(image_path, 'rb') as src_file, open(destination_path, 'wb') as dst_file:
                dst_file.write(src_file.read())
            logger.info(f"Imagen subida exitosamente: {destination_path}")
            return destination_path
        except IOError as e:
            logger.error(f"Error al subir la imagen: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al subir la imagen: {e}")
            return None

    def get_remaining_days(self, user_id):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT remaining_days, membership_end_date FROM users WHERE id = %s", (user_id,))
            result = self.cursor.fetchone()
            if result:
                remaining_days = result['remaining_days']
                end_date = result['membership_end_date']
                if end_date:
                    days_until_end = (end_date - datetime.now().date()).days
                    return min(remaining_days, max(0, days_until_end))
                return remaining_days
            return 0
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener los días restantes: {err}")
            return 0

    def update_remaining_days(self, user_id, days_to_subtract=1):
        try:
            self.ensure_connection()
            remaining_days = self.get_remaining_days(user_id)
            new_remaining_days = max(0, remaining_days - days_to_subtract)
            self.cursor.execute("UPDATE users SET remaining_days = %s WHERE id = %s", (new_remaining_days, user_id))
            self.conn.commit()
            logger.info(f"Días restantes actualizados para el usuario {user_id}: {new_remaining_days}")
        except mysql.connector.Error as err:
            logger.error(f"Error al actualizar los días restantes: {err}")
            self.conn.rollback()

    def record_attendance(self, user_id):
        try:
            self.ensure_connection()
            today = datetime.now().date()
            self.cursor.execute("INSERT INTO attendances (user_id, attendance_date) VALUES (%s, %s)", (user_id, today))
            self.conn.commit()
            self.update_remaining_days(user_id)
            logger.info(f"Asistencia registrada para el usuario {user_id}")
        except mysql.connector.Error as err:
            logger.error(f"Error al registrar la asistencia: {err}")
            self.conn.rollback()

    def get_promotions(self):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT * FROM promotions ORDER BY created_at DESC")
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener las promociones: {err}")
            return []

    def add_promotion(self, title, description, image_path):
        try:
            self.ensure_connection()
            self.cursor.execute("INSERT INTO promotions (title, description, image_path) VALUES (%s, %s, %s)",
                                (title, description, image_path))
            self.conn.commit()
            logger.info(f"Nueva promoción añadida: {title}")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Error al añadir la promoción: {err}")
            self.conn.rollback()
            return False

    def get_pending_payments(self):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT * FROM payments WHERE status = 'pending' ORDER BY payment_date DESC")
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener pagos pendientes: {err}")
            return []
        
    def update_payment_status(self, payment_id, new_status):
        try:
            self.ensure_connection()
            self.cursor.execute("UPDATE payments SET status = %s WHERE id = %s", (new_status, payment_id))
            self.conn.commit()
            logger.info(f"Estado de pago actualizado: ID {payment_id}, Nuevo estado: {new_status}")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Error al actualizar el estado del pago: {err}")
            self.conn.rollback()
            return False

    from decimal import Decimal

    def update_membership(self, user_id, membership_type, payment_amount):
        try:
            self.ensure_connection()
            start_date = datetime.now().date()
            
            # Determinar la duración basada en el tipo de membresía
            if membership_type == "normal":
                duration_days = 15
            elif membership_type == "full":
                duration_days = 30
            else:
                raise ValueError("Tipo de membresía no válido")
            
            # Asegurarse de que duration_days sea un entero
            duration_days = int(duration_days)
            
            # Convertir user_id a entero si es necesario
            user_id = int(user_id)
            
            end_date = start_date + timedelta(days=duration_days)
            
            self.cursor.execute("""
                UPDATE users 
                SET membership_type = %s, 
                    membership_start_date = %s, 
                    membership_end_date = %s, 
                    remaining_days = %s 
                WHERE id = %s
            """, (membership_type, start_date, end_date, duration_days, user_id))
            
            self.conn.commit()
            
            # Crear una notificación de expiración de membresía
            expiration_date = end_date.strftime("%Y-%m-%d")
            notification_message = f"Tu membresía {membership_type} expira el {expiration_date}"
            self.create_notification(user_id, notification_message, datetime.now())
            
            logger.info(f"Membresía actualizada: Usuario {user_id}, Tipo {membership_type}, Duración {duration_days} días")
            return True
        except Exception as e:
            logger.error(f"Error al actualizar la membresía: {e}")
            self.conn.rollback()
            return False


    def add_payment(self, user_id, amount, payment_type, image_path):
        try:
            self.ensure_connection()
            self.cursor.execute("INSERT INTO payments (user_id, amount, payment_date, payment_type, image_path, status) VALUES (%s, %s, %s, %s, %s, 'pending')",
                                (user_id, amount, datetime.now().date(), payment_type, image_path))
            self.conn.commit()
            logger.info(f"Nuevo pago añadido: Usuario {user_id}, Monto {amount}, Tipo {payment_type}")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Error al añadir el pago: {err}")
            self.conn.rollback()
            return False

    def update_membership(self, user_id, membership_type, duration_days):
        try:
            self.ensure_connection()
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=duration_days)
            self.cursor.execute("UPDATE users SET membership_type = %s, membership_start_date = %s, membership_end_date = %s, remaining_days = %s WHERE id = %s",
                            (membership_type, start_date, end_date, duration_days, user_id))
            self.conn.commit()
            
            # Crear una notificación de expiración de membresía
            expiration_date = end_date.strftime("%Y-%m-%d")
            notification_message = f"Tu membresía expira el {expiration_date}"
            self.create_notification(user_id, notification_message, datetime.now())
            
            logger.info(f"Membresía actualizada: Usuario {user_id}, Tipo {membership_type}, Duración {duration_days} días")
            return True
        except mysql.connector.Error as err:
            logger.error(f"Error al actualizar la membresía: {err}")
            self.conn.rollback()
            return False

    def create_notification(self, user_id, message, sent_at):
            try:
                self.ensure_connection()
                self.cursor.execute("INSERT INTO notifications (user_id, message, sent_at) VALUES (%s, %s, %s)", (user_id, message, sent_at))
                self.conn.commit()
                logger.info(f"Nueva notificación creada para el usuario {user_id}: {message}")
            except mysql.connector.Error as err:
                logger.error(f"Error al crear la notificación: {err}")
                self.conn.rollback()

    def get_unread_notifications(self, user_id):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT * FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY sent_at DESC", (user_id,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener notificaciones: {err}")
            return []

    def mark_notification_as_read(self, notification_id):
        try:
            self.ensure_connection()
            self.cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notification_id,))
            self.conn.commit()
            logger.info(f"Notificación {notification_id} marcada como leída")
        except mysql.connector.Error as err:
            logger.error(f"Error al marcar la notificación como leída: {err}")
            self.conn.rollback()
    
    def get_attendance_history(self, user_id):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT * FROM attendances WHERE user_id = %s ORDER BY attendance_date DESC", (user_id,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener el historial de asistencias: {err}")
            return []
        
    def get_unread_notifications(self, user_id):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT * FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY sent_at DESC", (user_id,))
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener notificaciones: {err}")
            return []

    def mark_notification_as_read(self, notification_id):
        try:
            self.ensure_connection()
            self.cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (notification_id,))
            self.conn.commit()
            logger.info(f"Notificación {notification_id} marcada como leída")
        except mysql.connector.Error as err:
            logger.error(f"Error al marcar la notificación como leída: {err}")
            self.conn.rollback()
    def get_user_by_id(self, user_id):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return self.cursor.fetchone()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener usuario por ID: {err}")
            return None