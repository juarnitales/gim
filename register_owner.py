import mysql.connector
import bcrypt

# Configuración de la base de datos
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'evolution_gym'
}

# Datos del nuevo dueño
username = input("Ingrese el nombre de usuario del dueño: ")
password = input("Ingrese la contraseña del dueño: ")

# Hashear la contraseña
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Conectar a la base de datos
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Verificar si ya existe un dueño
    cursor.execute("SELECT COUNT(*) FROM owners")
    owner_count = cursor.fetchone()[0]

    if owner_count > 0:
        print("Ya existe un dueño registrado. No se puede agregar otro.")
    else:
        # Insertar el nuevo dueño
        cursor.execute("INSERT INTO owners (username, password) VALUES (%s, %s)",
                       (username, hashed_password))
        conn.commit()
        print("Dueño registrado exitosamente")

except mysql.connector.Error as err:
    print(f"Error al registrar al dueño: {err}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()