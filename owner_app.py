import flet as ft
from common import CommonApp
import os
from datetime import datetime, timedelta
import logging
import bcrypt
import mysql.connector

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OwnerApp(CommonApp):
    def get_pending_payments(self):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT p.*, u.username FROM payments p JOIN users u ON p.user_id = u.id WHERE p.status = 'pending' ORDER BY p.payment_date DESC")
            payments = self.cursor.fetchall()
            logger.info(f"Pagos pendientes recuperados: {len(payments)}")
            return payments
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener pagos pendientes: {err}")
            return []
    def __init__(self):
        super().__init__()
        self.payment_images_folder = "payment_images"
        self.promotion_images_folder = "promotion_images"
        self.selected_file = None

    async def show_edit_user_dialog(self, page, user):
        membership_type = ft.Dropdown(
            label="Tipo de membresía",
            value=user['membership_type'],
            options=[
                ft.dropdown.Option("normal"),
                ft.dropdown.Option("full"),
            ],
        )
        end_date = ft.TextField(label="Fecha de fin", value=str(user['membership_end_date']))
        remaining_days = ft.TextField(label="Días restantes", value=str(user['remaining_days']))

        async def save_changes(e):
            try:
                success = self.update_user(
                    user['id'],
                    membership_type.value,
                    end_date.value,
                    int(remaining_days.value)
                )
                if success:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Usuario actualizado exitosamente")))
                    dlg.open = False
                    await page.go_async("/manage_users")  # Actualiza la vista de usuarios
                else:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Error al actualizar el usuario")))
            except ValueError:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, ingrese valores válidos")))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Editar usuario: {user['username']}"),
            content=ft.Column([
                membership_type,
                end_date,
                remaining_days,
            ], tight=True),
            actions=[
                ft.ElevatedButton("Guardar", on_click=save_changes),
                ft.ElevatedButton("Cancelar", on_click=lambda _: setattr(dlg, 'open', False)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dlg
        dlg.open = True
        await page.update_async()

    async def edit_user_view(self, page: ft.Page):
        user_id = int(page.route.split('/')[-1])
        user = self.get_user_by_id(user_id)
        if not user:
            return ft.View("/edit_user", [ft.Text("Usuario no encontrado")])

        membership_type = ft.Dropdown(
            label="Tipo de membresía",
            value=user['membership_type'],
            options=[
                ft.dropdown.Option("normal"),
                ft.dropdown.Option("full"),
            ],
        )
        end_date = ft.TextField(label="Fecha de fin", value=str(user['membership_end_date']))
        remaining_days = ft.TextField(label="Días restantes", value=str(user['remaining_days']))

        async def save_changes(e):
            try:
                success = self.update_user(
                    user['id'],
                    membership_type.value,
                    end_date.value,
                    int(remaining_days.value)
                )
                if success:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Usuario actualizado exitosamente")))
                    await page.go_async("/manage_users")
                else:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Error al actualizar el usuario")))
            except ValueError:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, ingrese valores válidos")))

        return ft.View(
            "/edit_user",
            [
                ft.AppBar(title=ft.Text(f"Editar usuario: {user['username']}")),
                ft.Column([
                    membership_type,
                    end_date,
                    remaining_days,
                    ft.ElevatedButton("Guardar", on_click=save_changes),
                    ft.ElevatedButton("Cancelar", on_click=lambda _: page.go("/manage_users")),
                ], tight=True)
            ]
        )


    async def main(self, page: ft.Page):
        self.page = page
        self.connect_to_db()
        page.title = "Evolution Gym - Dueño"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 375
        page.window_height = 812

        async def route_change(route):
            page.views.clear()
            if page.route == "/":
                page.views.append(await self.login_view(page))
            elif page.route == "/dashboard":
                page.views.append(await self.dashboard_view(page))
            elif page.route == "/manage_payments":
                page.views.append(await self.manage_payments_view(page))
            elif page.route == "/manage_users":
                page.views.append(await self.manage_users_view(page))
            elif page.route.startswith("/edit_user/"):
                page.views.append(await self.edit_user_view(page))
            # ... otras rutas ...
                page.views.append(await self.manage_payments_view(page))
            elif page.route == "/upload_promotion":
                page.views.append(await self.upload_promotion_view(page))
            elif page.route == "/manage_users":
                page.views.append(await self.manage_users_view(page))
            elif page.route == "/payment_history":
                page.views.append(await self.payment_history_view(page))
            await page.update_async()

        page.on_route_change = route_change
        await page.go_async("/")

    async def login_view(self, page: ft.Page):
        username = ft.TextField(label="Nombre de usuario", width=300)
        password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)
        login_button = ft.ElevatedButton("Iniciar sesión", width=300)
        async def do_login(e):
            if not username.value or not password.value:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, completa todos los campos")))
                return

            try:
                self.cursor.execute("SELECT * FROM owners WHERE username = %s", (username.value,))
                owner = self.cursor.fetchone()
                logger.info(f"Intento de inicio de sesión para el usuario: {username.value}")
                logger.info(f"Dueño encontrado en la base de datos: {owner is not None}")
                
                if owner and 'password' in owner and bcrypt.checkpw(password.value.encode('utf-8'), owner['password'].encode('utf-8')):
                    self.current_user = owner
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
                ft.AppBar(title=ft.Text("Inicio de sesión del Dueño")),
                ft.Column([
                    username,
                    password,
                    login_button
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ],
        )
    async def dashboard_view(self, page: ft.Page):
        stats = self.get_statistics()

        async def go_to_manage_payments(_):
            await page.go_async("/manage_payments")

        async def go_to_upload_promotion(_):
            await page.go_async("/upload_promotion")

        async def go_to_manage_users(_):
            await page.go_async("/manage_users")

        async def go_to_payment_history(_):
            await page.go_async("/payment_history")

        return ft.View(
            "/dashboard",
            [
                ft.AppBar(title=ft.Text("Panel de Control - Dueño")),
                ft.Column([
                    ft.Text(f"Total de usuarios: {stats['total_users']}"),
                    ft.Text(f"Usuarios activos: {stats['active_users']}"),
                    ft.Text(f"Ingresos totales: {stats.get('total_income', 0.0):.2f}" if stats.get('total_income') is not None else "N/A"),
                    ft.Text(f"Asistencias del último mes: {stats['monthly_attendances']}"),
                    ft.ElevatedButton("Gestionar Pagos", on_click=go_to_manage_payments),
                    ft.ElevatedButton("Subir Promoción", on_click=go_to_upload_promotion),
                    ft.ElevatedButton("Gestionar Usuarios", on_click=go_to_manage_users),
                    ft.ElevatedButton("Historial de Pagos", on_click=go_to_payment_history),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ]
        )

    async def manage_payments_view(self, page: ft.Page):
        pending_payments = self.get_pending_payments()
        logger.info(f"Número de pagos pendientes: {len(pending_payments)}")
        payment_list = ft.Column(scroll=ft.ScrollMode.AUTO)

        if not pending_payments:
            logger.info("No hay pagos pendientes")
            payment_list.controls.append(ft.Text("No hay pagos pendientes"))
        else:
            for payment in pending_payments:
                logger.info(f"Procesando pago: {payment}")
                payment_item = ft.Column([
                    ft.Text(f"Usuario: {payment['username']}"),
                    ft.Text(f"Monto: ${payment['amount']}"),
                    ft.Text(f"Tipo: {payment['payment_type']}"),
                    ft.Text(f"Fecha: {payment['payment_date']}"),
                    self.show_image(payment['image_path']),
                    ft.Row([
                        ft.ElevatedButton("Aprobar", on_click=lambda _, p=payment, pi=payment_item: self.approve_payment(p, pi)),
                        ft.ElevatedButton("Rechazar", on_click=lambda _, p=payment, pi=payment_item: self.reject_payment(p, pi)),
                    ])
                ])
                payment_list.controls.append(payment_item)

        return ft.View(
            "/manage_payments",
            [
                ft.AppBar(title=ft.Text("Gestionar Pagos")),
                payment_list,
                ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
            ]
        )


    async def upload_promotion_view(self, page: ft.Page):
        title = ft.TextField(label="Título de la promoción")
        description = ft.TextField(label="Descripción", multiline=True)
        file_picker = ft.FilePicker(on_result=self.on_file_selected)
        page.overlay.append(file_picker)
        image_preview = ft.Image(width=200, height=200, fit=ft.ImageFit.CONTAIN)

        async def upload_promotion(e):
            if not title.value or not description.value or not self.selected_file:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, completa todos los campos y selecciona una imagen")))
                return

            try:
                destination_path = self.upload_image(self.selected_file, self.promotion_images_folder)
                self.add_promotion(title.value, description.value, destination_path)
                page.show_snack_bar(ft.SnackBar(ft.Text("Promoción subida exitosamente")))
                await page.go_async("/dashboard")
            except Exception as e:
                logger.error(f"Error al subir la promoción: {e}")
                page.show_snack_bar(ft.SnackBar(ft.Text("Error al subir la promoción")))

        return ft.View(
            "/upload_promotion",
            [
                ft.AppBar(title=ft.Text("Subir Promoción")),
                ft.Column([
                    title,
                    description,
                    ft.ElevatedButton("Seleccionar imagen", on_click=lambda _: file_picker.pick_files(allow_multiple=False)),
                    image_preview,
                    ft.ElevatedButton("Subir promoción", on_click=upload_promotion),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
            ]
        )

    async def manage_payments_view(self, page: ft.Page):
        pending_payments = self.get_pending_payments()
        logger.info(f"Número de pagos pendientes: {len(pending_payments)}")
        payment_list = ft.Column(scroll=ft.ScrollMode.AUTO)

        if not pending_payments:
            logger.info("No hay pagos pendientes")
            payment_list.controls.append(ft.Text("No hay pagos pendientes"))
        else:
            for payment in pending_payments:
                logger.info(f"Procesando pago: {payment}")
                
                def create_button(payment, action):
                    async def handle_click(_):
                        if action == "approve":
                            await self.approve_payment(payment, payment_item)
                        else:
                            await self.reject_payment(payment, payment_item)
                    return ft.ElevatedButton(
                        "Aprobar" if action == "approve" else "Rechazar",
                        on_click=handle_click
                    )

                payment_item = ft.Column([
                    ft.Text(f"Usuario: {payment['username']}"),
                    ft.Text(f"Monto: ${payment['amount']}"),
                    ft.Text(f"Tipo: {payment['payment_type']}"),
                    ft.Text(f"Fecha: {payment['payment_date']}"),
                    self.show_image(payment['image_path']),
                    ft.Row([
                        create_button(payment, "approve"),
                        create_button(payment, "reject")
                    ])
                ])
                payment_list.controls.append(payment_item)

        return ft.View(
            "/manage_payments",
            [
                ft.AppBar(title=ft.Text("Gestionar Pagos")),
                payment_list,
                ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
            ]
        )

    async def manage_users_view(self, page: ft.Page):
        try:
            users = self.get_users()
            user_list = ft.Column(scroll=ft.ScrollMode.AUTO)

            for user in users:
                user_item = ft.Column([
                    ft.Text(f"Usuario: {user['username']}"),
                    ft.Text(f"Tipo de membresía: {user['membership_type']}"),
                    ft.Text(f"Fecha de fin: {user['membership_end_date']}"),
                    ft.Text(f"Días restantes: {user['remaining_days']}"),
                    ft.ElevatedButton("Editar", on_click=lambda _, u=user: self.edit_user(page, u)),
                    ft.Divider(),
                ])
                user_list.controls.append(user_item)

            return ft.View(
                "/manage_users",
                [
                    ft.AppBar(title=ft.Text("Gestionar Usuarios")),
                    user_list,
                    ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
                ]
            )
        except Exception as e:
            logger.error(f"Error en manage_users_view: {e}")
            return ft.View(
                "/manage_users",
                [
                    ft.AppBar(title=ft.Text("Error")),
                    ft.Text("Ocurrió un error al cargar la lista de usuarios."),
                    ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
                ]
            )

    def edit_user(self, page, user):
        page.go(f"/edit_user/{user['id']}")


    async def payment_history_view(self, page: ft.Page):
        payments = self.get_payment_history()
        payment_list = ft.Column(scroll=ft.ScrollMode.AUTO)

        for payment in payments:
            payment_item = ft.Column([
                ft.Text(f"Usuario: {payment['username']}"),
                ft.Text(f"Monto: ${payment['amount']}"),
                ft.Text(f"Fecha: {payment['payment_date']}"),
                ft.Text(f"Tipo: {payment['payment_type']}"),
                ft.Text(f"Estado: {payment['status']}"),
                ft.Divider(),
            ])
            payment_list.controls.append(payment_item)

        return ft.View(
            "/payment_history",
            [
                ft.AppBar(title=ft.Text("Historial de Pagos")),
                payment_list,
                ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
            ]
        )


    def on_file_selected(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.selected_file = e.files[0].path
            self.page.get_by_id("image_preview").src = self.selected_file
            self.page.update()

    def get_statistics(self):
        try:
            self.ensure_connection()
            stats = {}

            # Total de usuarios
            self.cursor.execute("SELECT COUNT(*) AS total_users FROM users")
            row = self.cursor.fetchone()
            stats['total_users'] = row.get('total_users', 0)

            # Usuarios activos (con membresía vigente)
            self.cursor.execute("SELECT COUNT(*) AS active_users FROM users WHERE membership_end_date >= CURDATE()")
            row = self.cursor.fetchone()
            stats['active_users'] = row.get('active_users', 0)

            # Total de ingresos (pagos aprobados)
            self.cursor.execute("SELECT SUM(amount) AS total_income FROM payments WHERE status = 'approved'")
            row = self.cursor.fetchone()
            stats['total_income'] = row.get('total_income', 0)

            # Asistencias del último mes
            self.cursor.execute("SELECT COUNT(*) AS monthly_attendances FROM attendances WHERE attendance_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)")
            row = self.cursor.fetchone()
            stats['monthly_attendances'] = row.get('monthly_attendances', 0)

            return stats
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener estadísticas: {err}")
            return {}

    def get_users(self):
        try:
            self.ensure_connection()
            self.cursor.execute("SELECT id, username, membership_type, membership_end_date, remaining_days FROM users")
            users = self.cursor.fetchall()
            logger.info(f"Obtenidos {len(users)} usuarios")
            return users
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener usuarios: {err}")
            return []

    def update_user(self, user_id, membership_type, end_date, remaining_days):
        try:
            self.ensure_connection()
            self.cursor.execute("UPDATE users SET membership_type = %s, membership_end_date = %s, remaining_days = %s WHERE id = %s",
                                (membership_type, end_date, remaining_days, user_id))
            self.conn.commit()
            return True
        except mysql.connector.Error as err:
            logger.error(f"Error al actualizar usuario: {err}")
            return False

    def get_payment_history(self):
        try:
            self.ensure_connection()
            self.cursor.execute("""
                SELECT p.id, u.username, p.amount, p.payment_date, p.payment_type, p.status
                FROM payments p
                JOIN users u ON p.user_id = u.id
                ORDER BY p.payment_date DESC
            """)
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Error al obtener historial de pagos: {err}")
            return []

    async def show_edit_user_dialog(self, page, user):
        membership_type = ft.Dropdown(
            label="Tipo de membresía",
            value=user['membership_type'],
            options=[
                ft.dropdown.Option("normal"),
                ft.dropdown.Option("full"),
            ],
        )
        end_date = ft.TextField(label="Fecha de fin", value=str(user['membership_end_date']))
        remaining_days = ft.TextField(label="Días restantes", value=str(user['remaining_days']))

        async def save_changes(e):
            try:
                success = self.update_user(
                    user['id'],
                    membership_type.value,
                    end_date.value,
                    int(remaining_days.value)
                )
                if success:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Usuario actualizado exitosamente")))
                    dlg.open = False
                    await page.go_async("/manage_users")  # Actualiza la vista de usuarios
                else:
                    page.show_snack_bar(ft.SnackBar(ft.Text("Error al actualizar el usuario")))
            except ValueError:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, ingrese valores válidos")))

        dlg = ft.AlertDialog(
            title=ft.Text(f"Editar usuario: {user['username']}"),
            content=ft.Column([
                membership_type,
                end_date,
                remaining_days,
            ], tight=True),
            actions=[
                ft.ElevatedButton("Guardar", on_click=save_changes),
                ft.ElevatedButton("Cancelar", on_click=lambda _: setattr(dlg, 'open', False)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.dialog = dlg
        dlg.open = True
        await page.update_async()

    async def approve_payment(self, payment, payment_item):
        try:
            logger.info(f"Aprobando pago: {payment['id']}")
            self.update_payment_status(payment['id'], 'approved')
            
            # Convertir los valores a los tipos correctos
            user_id = int(payment['user_id'])
            payment_type = str(payment['payment_type'])
            amount = float(payment['amount'])
            
            self.update_membership(user_id, payment_type, amount)
            
            payment_list = self.page.views[-1].controls[1]
            payment_list.controls.remove(payment_item)
            await self.page.update_async()
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Pago aprobado exitosamente")))
        except Exception as e:
            logger.error(f"Error al aprobar el pago: {e}")
            self.page.show_snack_bar(ft.SnackBar(ft.Text("Error al aprobar el pago")))                    

if __name__ == "__main__":
    ft.app(target=OwnerApp().main)







