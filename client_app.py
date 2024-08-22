import flet as ft
from common import CommonApp
import os
from datetime import datetime, timedelta
import logging
import bcrypt

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientApp(CommonApp):
    def __init__(self):
        super().__init__()
        self.payment_images_folder = "payment_images"
        self.selected_file = None

    async def main(self, page: ft.Page):
        self.page = page
        self.connect_to_db()
        page.title = "Evolution Gym - Cliente"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 375
        page.window_height = 812

        async def route_change(route):
            page.views.clear()
            if page.route == "/":
                page.views.append(await self.home_view(page))
            elif page.route == "/login":
                page.views.append(await self.login_view(page))
            elif page.route == "/register":
                page.views.append(await self.register_view(page))
            elif page.route == "/dashboard":
                page.views.append(await self.dashboard_view(page))
            elif page.route == "/upload_payment":
                page.views.append(await self.upload_payment_view(page))
            elif page.route == "/view_promotions":
                page.views.append(await self.view_promotions(page))
            elif page.route.startswith("/image/"):
                image_type = page.route.split("/")[-1]
                page.views.append(self.show_image_view(image_type))
            await page.update_async()

        page.on_route_change = route_change
        await page.go_async("/")

    async def home_view(self, page: ft.Page):
        logo = self.show_image("logo.png")
        return ft.View(
            "/",
            [
                ft.AppBar(title=ft.Text("Evolution Gym")),
                logo,
                ft.Column([
                    ft.ElevatedButton("Iniciar sesión", on_click=lambda _: page.go("/login")),
                    ft.ElevatedButton("Registrarse", on_click=lambda _: page.go("/register")),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ]
        )

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
            except Exception as err:
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
                    login_button,
                    ft.TextButton("¿No tienes una cuenta? Regístrate", on_click=lambda _: page.go("/register"))
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
            except Exception as err:
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
                    register_button,
                    ft.TextButton("¿Ya tienes una cuenta? Inicia sesión", on_click=lambda _: page.go("/login"))
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ],
        )

    async def dashboard_view(self, page: ft.Page):
        if not self.current_user:
            return await self.login_view(page)

        ad_banner = ft.Image(src="superior.png", height=120, fit=ft.ImageFit.FIT_WIDTH)

        days_left = self.get_remaining_days(self.current_user['id'])
        membership_counter = ft.Text(f"Días restantes de membresía: {days_left}")

        gym_name = ft.Text("Evolution Gym", style="headlineMedium", color=ft.colors.BLACK)
        gym_description = ft.Text("Tu centro de entrenamiento de confianza, ofreciendo equipos de última generación y entrenadores profesionales para ayudarte a alcanzar tus metas de fitness.", color=ft.colors.BLACK)

        def create_product_image(src, url):
            return ft.GestureDetector(
                on_tap=lambda _: page.launch_url(url),
                content=ft.Image(src=src, width=100, height=100)
            )

        product_images = [
            create_product_image(f"{i}.png", f"https://wa.me/593967984432=link{j}")
            for i, j in zip(["uno", "dos", "tres", "cuatro", "cinco", "seis"], [1, 2, 3, 1, 2, 3])
        ]

        image_grid = ft.Column([
            ft.Row(product_images[:3], alignment="center"),
            ft.Row(product_images[3:], alignment="center")
        ])

     

        sidebar = self.create_sidebar()
        sidebar.visible = False  # Inicialmente oculta

        footer_links = self.create_footer_links()

        async def go_to_upload_payment(e):
            await page.go_async("/upload_payment")

        async def go_to_view_promotions(e):
            await page.go_async("/view_promotions")

        # Obtener las notificaciones pendientes del usuario
        notifications = self.get_unread_notifications(self.current_user['id'])

        notification_list = ft.Column(scroll=ft.ScrollMode.AUTO)
        for notification in notifications:
            notification_item = ft.Column([
                ft.Text(notification['message']),
                ft.Text(notification['sent_at'].strftime("%Y-%m-%d %H:%M:%S")),
                ft.ElevatedButton("Marcar como leída", on_click=lambda _, n_id=notification['id']: self.mark_notification_as_read(n_id))
            ])
            notification_list.controls.append(notification_item)

        # Obtener el historial de asistencias del usuario
        attendance_history = self.get_attendance_history(self.current_user['id'])
        attendance_list = ft.Column(scroll=ft.ScrollMode.AUTO)
        for attendance in attendance_history:
            attendance_item = ft.Column([
                ft.Text(attendance['attendance_date'].strftime("%Y-%m-%d"))
            ])
            attendance_list.controls.append(attendance_item)

        toggle_sidebar_button = ft.IconButton(
            icon=ft.icons.MENU,
            tooltip="Toggle Sidebar",
            on_click=self.toggle_sidebar
        )

        return ft.View(
            "/dashboard",
            [
                ft.AppBar(title=ft.Text("Panel de usuario"), actions=[toggle_sidebar_button]),
                ft.Row(
                    [
                        sidebar,
                        ft.VerticalDivider(visible=False),  # Oculto inicialmente
                        ft.Column([
                            ad_banner,
                            ft.Text(f"Bienvenido, {self.current_user['username']}"),
                            membership_counter,
                            gym_name,
                            gym_description,
                            ft.Container(padding=10),
                            ft.Text("Productos", style="headlineSmall", weight=ft.FontWeight.BOLD),
                            image_grid,
                            ft.Container(height=20),
                            ft.ElevatedButton("Subir Comprobante de Pago", on_click=go_to_upload_payment),
                            ft.ElevatedButton("Ver Promociones", on_click=go_to_view_promotions),
                            ft.Divider(),
                            ft.Text("Notificaciones", style="headlineSmall", weight=ft.FontWeight.BOLD),
                            notification_list,
                            ft.Divider(),
                            ft.Text("Historial de Asistencias", style="headlineSmall", weight=ft.FontWeight.BOLD),
                            attendance_list,
                            footer_links
                        ], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ],
                    expand=True
                ),
            ]
        )


    
    def create_sidebar(self):
        todo_app = TodoApp()

        def show_image(image_type):
            self.page.go(f"/image/{image_type}")

        return ft.Container(
            ft.Column(
                [
                    
                    ft.Divider(),
                    ft.Text("Rutinas de entrenamiento", weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Espalda", on_click=lambda _: show_image("espalda")),
                    ft.ElevatedButton("Hombros", on_click=lambda _: show_image("hombros")),
                    ft.ElevatedButton("Pecho", on_click=lambda _: show_image("pecho")),
                    ft.ElevatedButton("Tríceps", on_click=lambda _: show_image("triceps")),
                ]
            ),
            width=200,
            bgcolor=ft.colors.LIGHT_BLUE_50,
            padding=10,
            visible=True  # Cambiado a True para que sea visible por defecto
        )

    def create_footer_links(self):
        def create_icon_button(image_name, url):
            return ft.GestureDetector(
                on_tap=lambda _: self.page.launch_url(url),
                content=ft.Image(src=f"{image_name}.png", width=20, height=20,)
            )
        return ft.Row(
            [
                create_icon_button("facebook", "https://www.facebook.com/profile.php?id=100054296540587&sk=about"),
                create_icon_button("ubicacion", "https://maps.app.goo.gl/UWadHp4nLwSVikRe9"),
                create_icon_button("social", "https://wa.me/593967984432")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20
        )
    def toggle_sidebar(self, e):
        sidebar = self.page.views[-1].controls[1].controls[0]
        divider = self.page.views[-1].controls[1].controls[1]
        sidebar.visible = not sidebar.visible
        divider.visible = sidebar.visible
        self.page.update()



    async def upload_payment_view(self, page: ft.Page):
        amount = ft.TextField(label="Monto pagado")
        payment_type = ft.Dropdown(
            label="Tipo de pago",
            options=[
                ft.dropdown.Option("normal"),
                ft.dropdown.Option("full"),
            ],
        )
        file_picker = ft.FilePicker(on_result=self.on_file_selected)
        page.overlay.append(file_picker)
        image_preview = ft.Image(width=200, height=200, fit=ft.ImageFit.CONTAIN)

        async def upload_payment(e):
            if not amount.value or not payment_type.value or not self.selected_file:
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, completa todos los campos y selecciona una imagen")))
                return

            if not self.selected_file.lower().endswith('.png'):
                page.show_snack_bar(ft.SnackBar(ft.Text("Por favor, selecciona una imagen en formato PNG")))
                return

            try:
                destination_path = self.upload_image(self.selected_file, self.payment_images_folder)
                self.add_payment(self.current_user['id'], float(amount.value), payment_type.value, destination_path)
                page.show_snack_bar(ft.SnackBar(ft.Text("Comprobante subido exitosamente")))
                await page.go_async("/dashboard")
            except Exception as e:
                logger.error(f"Error al subir el pago: {e}")
                page.show_snack_bar(ft.SnackBar(ft.Text("Error al subir el comprobante. Por favor, intenta de nuevo.")))

        return ft.View(
            "/upload_payment",
            [
                ft.AppBar(title=ft.Text("Subir Comprobante de Pago")),
                ft.Column([
                    amount,
                    payment_type,
                    ft.ElevatedButton("Seleccionar imagen", on_click=lambda _: file_picker.pick_files(allowed_extensions=["png"])),
                    image_preview,
                    ft.ElevatedButton("Subir comprobante", on_click=upload_payment),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
            ]
        )


    def on_file_selected(self, e: ft.FilePickerResultEvent):
                if e.files:
                    self.selected_file = e.files[0].path
                    self.page.get_by_id("image_preview").src = self.selected_file
                    self.page.update()

    async def view_promotions(self, page: ft.Page):
        promotions = self.get_promotions()
        promotion_list = ft.Column(scroll=ft.ScrollMode.AUTO)

        for promotion in promotions:
            promotion_item = ft.Column([
                ft.Text(promotion['title'], size=20, weight=ft.FontWeight.BOLD),
                ft.Text(promotion['description']),
                self.show_image(promotion['image_path']),
                ft.Divider(),
            ])
            promotion_list.controls.append(promotion_item)

        return ft.View(
            "/view_promotions",
            [
                ft.AppBar(title=ft.Text("Promociones")),
                promotion_list,
                ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))
            ]
        )

    def show_image_view(self, image_type):
                    image_name = f"{image_type}.png"
                    image_view = self.show_image(image_name)
                    return ft.View(
                        f"/image/{image_type}",
                        [
                            ft.AppBar(title=ft.Text(f"Imagen {image_type.capitalize()}")),
                            image_view,
                            ft.ElevatedButton("Volver", on_click=lambda _: self.page.go("/dashboard"))
                        ]
                    )
class TodoApp(ft.UserControl):
    def build(self):
        self.new_task = ft.TextField(hint_text="Nueva tarea", expand=True, color=ft.colors.BLACK)
        self.tasks = ft.Column()

        return ft.Column(
            [
                ft.Row(
                    [
                        self.new_task,
                        ft.ElevatedButton("Agregar", on_click=self.add_clicked),
                    ]
                ),
                self.tasks,
            ]
        )

    def add_clicked(self, e):
        task = ft.Checkbox(label=self.new_task.value)
        self.tasks.controls.append(task)
        self.new_task.value = ""
        self.update()

if __name__ == "__main__":
    ft.app(target=ClientApp().main)