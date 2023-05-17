from flask import Flask, render_template
import psycopg2
import base64
import matplotlib.pyplot as plt
import os


app = Flask(__name__)

# Establecer la conexión con la base de datos
conn = psycopg2.connect(
    host="db.dnhcuemnhgdglyjvslxf.supabase.co",
    database="postgres",
    port= "5432",
    user="postgres",
    password="xAWB2QRSpEHvMegV"
)

@app.route('/')
def hello_world():
    # crear html con los datos de la base de datos
    return 'Hello, World!'


@app.route('/dashboard', methods=['GET'])
def receive_message():
    # Crear un cursor para ejecutar comandos
    cur = conn.cursor()

    # Ejecutar un comando SQL
    cur.execute("SELECT * FROM transactions")

    # Obtener los resultados
    result = cur.fetchall()

    # Preparar los resultados
    data_show = []
    data_show.append(len(result))

    transacciones = []
    envios = 0
    monto_envios = 0
    reversas = 0
    monto_reversas = 0
    for transaction in result:
        data = base64.b64decode(transaction[1])
        data = data.decode('utf-8')
        fecha = transaction[2]
        #Fecha legible
        fecha_legible = fecha.split('T')[0] + ' ' + fecha.split('T')[1].split('.')[0]

        tipo = data[0:4]
        monto = data[48:64]

        if tipo == '2200':
            tipo = 'Envio de fondos'
            envios += 1
            monto_envios += int(monto)
        elif tipo == '2400':
            tipo = 'Reversa de transaccion'
            reversas += 1
            monto_reversas += int(monto)
        

        id = data[4:14]
        banco_origen = data[14:21]
        cuenta_origen = data[21:31]
        banco_destino = data[31:38]
        cuenta_destino = data[38:48]

        # Eliminar los 0 a la izquierda
        id = id.lstrip('0')
        banco_origen = banco_origen.lstrip('0')
        cuenta_origen = cuenta_origen.lstrip('0')
        banco_destino = banco_destino.lstrip('0')
        cuenta_destino = cuenta_destino.lstrip('0')
        monto = int(monto.lstrip('0'))



        #Revisar si ya existe una transaccion con el mismo ID, si existe, no agregarla
        existe = False
        for transaccion in transacciones:
            if transaccion[1] == id:
                existe = True
                break
        if existe:
            continue
        else:
            transacciones.append([
                id,
                tipo,
                banco_origen,
                cuenta_origen,
                banco_destino,
                cuenta_destino,
                monto,
                fecha_legible
            ])

    data_show.append([envios, monto_envios])
    data_show.append([reversas, monto_reversas])

    # Crear conciliacion entre bancos para mostrar en el dashboard
    deuda_origen = {}
    deuda_destino = {}

    # Iterar sobre las transacciones y actualizar los diccionarios de deuda
    for transaccion in transacciones:
        id, tipo, banco_origen, cuenta_origen, banco_destino, cuenta_destino, monto, fecha = transaccion
        if tipo == "Envio de fondos":
            if banco_origen not in deuda_origen:
                deuda_origen[banco_origen] = {}
            if banco_destino not in deuda_destino:
                deuda_destino[banco_destino] = {}
            deuda_origen[banco_origen][banco_destino] = deuda_origen[banco_origen].get(banco_destino, 0) - monto
            deuda_destino[banco_destino][banco_origen] = deuda_destino[banco_destino].get(banco_origen, 0) + monto
        elif tipo == "Reversa de transaccion":
            if banco_destino not in deuda_origen:
                deuda_origen[banco_destino] = {}
            if banco_origen not in deuda_destino:
                deuda_destino[banco_origen] = {}
            deuda_origen[banco_destino][banco_origen] = deuda_origen[banco_destino].get(banco_origen, 0) + monto
            deuda_destino[banco_origen][banco_destino] = deuda_destino[banco_origen].get(banco_destino, 0) - monto

    # Crear lista de saldos para mostrar en el dashboard
    saldos = []
    for banco in deuda_origen:
        for banco2 in deuda_origen[banco]:
            saldo = deuda_origen[banco][banco2]
            if saldo > 0:
                saldos.append([banco, banco2, saldo])
    for banco in deuda_destino:
        for banco2 in deuda_destino[banco]:
            saldo = deuda_destino[banco][banco2]
            if saldo > 0:
                saldos.append([banco, banco2, saldo])

    for saldo in saldos:
        banco_origen_1 = saldo[0]
        banco_destino_1 = saldo[1]
        monto_1 = saldo[2] 
        for saldo2 in saldos:
            banco_origen_2 = saldo2[0]
            banco_destino_2 = saldo2[1]
            monto_2 = saldo2[2]
            if banco_origen_1 == banco_destino_2 and banco_origen_2 == banco_destino_1:
                if monto_1 > monto_2:
                    saldo[2] = monto_1 - monto_2
                    saldos.remove(saldo2)
                elif monto_2 > monto_1:
                    saldo[2] = monto_2 - monto_1
                    saldos.remove(saldo2)
                else:
                    saldos.remove(saldo2)

    # Definir las constantes de los intervalos
    INTERVALOS = [
        ("Menor a $10.000", 0, 10000),
        ("Entre $10.000 y $49.999", 10000, 50000),
        ("Entre $50.000 y $99.999", 50000, 100000),
        ("Entre $100.000 y $499.999", 100000, 500000),
        ("Entre $500.000 y $999.999", 500000, 1000000),
        ("Entre $1.000.000 y $9.999.999", 1000000, 10000000),
        ("Más de $9.999.999", 10000000, float("inf"))
    ]

    def agrupar_transacciones(transacciones):
        grupos = {intervalo[0]: 0 for intervalo in INTERVALOS}
        for transaccion in transacciones:
            monto = transaccion[6]
            for intervalo in INTERVALOS:
                if intervalo[1] <= monto < intervalo[2]:
                    grupos[intervalo[0]] += 1
                    break
        return grupos

    grupos = agrupar_transacciones(transacciones)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(grupos.keys(), grupos.values(), color='lightblue')
    ax.set_title('Cantidad de transacciones por intervalo de monto')
    ax.set_xlabel('Intervalo de monto')
    ax.set_ylabel('Cantidad de transacciones')
    plt.xticks(rotation=90)
    plt.tight_layout()
    # Guardar el gráfico en un archivo
    nombre_archivo = "histograma.png"
    directorio_imagenes = os.path.join(app.root_path, "static")
    nombre_archivo = os.path.join(directorio_imagenes, nombre_archivo)
    plt.savefig(nombre_archivo)


    # Seleccionar las ultimas 100 transacciones
    transacciones = transacciones[-100:]
    data_show.append(transacciones)

    return render_template("dashboard.html", data_show=data_show, saldos=saldos)

if __name__ == '__main__':
    app.run(port=3000, debug=True)
