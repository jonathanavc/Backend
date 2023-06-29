from openpyxl import Workbook
from datetime import datetime
import random

from __main__ import app, mysql, request, jsonify, send_from_directory

@app.route("/reporte", methods=["GET", "POST"])
def reporte():
    _sexo = ["HOMBRE","MUJER"]
    random.seed(5)
    wb = Workbook()
    ws = wb.active
    ws.append(["ID Persona","Sexo","Edad","Altura(cm)","Peso(kg)","Cantidad al mes(g)","Alimento"])
    cur = mysql.connection.cursor()
    if request.method == "POST":
        preview = []
        reporte = {"regiones": {}, "chile":{"c_personas":0,"prom_peso":0}}
        request_json = request.get_json()
        sexo = ""
        if(request_json[sexo] != ["1","0"]):
            sexo = request_json["sexo"]
            sexo = "sexo = " + sexo + " AND"

        min_edad = request_json["edad"][0]
        max_edad = request_json["edad"][1]
        min_peso = request_json["peso"][0]
        max_peso = request_json["peso"][1]
        alimentos = request_json.get("alimentos")
        contaminantes = []
        cur.execute("SELECT id, nombre, limite_diario FROM Contaminante")
        res = cur.fetchall()
        for contaminante in res:
            contaminantes.append({"id":contaminante[0], "nombre": contaminante[1], "limite_diario": contaminante[2]})

        #print(contaminantes)

        for alimento in alimentos:
            cur.execute("SELECT id FROM Alimento WHERE nombre = %s",[alimento["nombre"]])
            res = cur.fetchall()

            if(res[0] is not None):
                alimento["id"] = res[0][0]
            else:
                return "error: alimento " + alimento["nombre"] + " no encontrado."
            
            for contaminante in contaminantes:
                if not contaminante["nombre"] in alimento:
                    cur.execute("SELECT Avg(cantidad)  FROM  Muestra WHERE id_contaminante=%s AND id_alimento=%s" ,([contaminante["id"]],[alimento["id"]]))
                    res = cur.fetchall()
                    alimento[contaminante["nombre"] ] = res[0][0]
        
        #print(alimentos)

        regiones = []
        cur.execute("SELECT id FROM Region")
        res = cur.fetchall()
        for region in res:
            regiones.append({"id": region[0], "comunas": []})

        #print(regiones)

        for region in regiones:
            cur.execute("SELECT id FROM Comuna WHERE id_region =%s",[region["id"]])
            res = cur.fetchall()
            for comuna in res:
                region["comunas"].append(comuna[0])
    
        #print(regiones)

        sql_alimentos = "Consumo.id_alimento = " + str(alimentos[0]["id"])
        for alimento in alimentos:
            if(alimento == alimentos[0]): 
                continue
            else:
                sql_alimentos+= " OR Consumo.id_alimento = " + str(alimento["id"])
        
        #print(sql_alimentos)

        personas = {}
        for region in regiones:
            reporte_region = {
                "c_personas": 0
            }
            sql_comunas = "comuna_id = " + str(region["comunas"][0])
            for comuna in region["comunas"]:
                if(comuna == region["comunas"][0]): 
                    continue
                else:
                    sql_comunas += " OR comuna_id = " + str(comuna)
            
            #print(sql_comunas)
            
            #print("SELECT p.id, p.peso, Consumo.cantidad_mes, Consumo.id_alimento, p.sexo FROM (SELECT * FROM Persona WHERE "+ sexo +" edad > %s AND edad < %s AND peso > %s AND peso < %s AND " + sql_comunas + " ) AS p INNER JOIN  Consumo ON p.id = Consumo.id_persona WHERE Consumo.cantidad_mes != 0.0 AND "+ sql_alimentos + ";",[min_edad, max_edad, min_peso, max_peso])
            cur.execute("SELECT p.id, p.peso, Consumo.cantidad_mes, Consumo.id_alimento, p.sexo, p.edad, p.altura FROM (SELECT p.id, p.peso, p.sexo, p.altura, p.edad from (SELECT * FROM Comuna WHERE id_region = %s) as r JOIN (SELECT * FROM Persona WHERE "+ sexo +" edad > %s AND edad < %s AND peso > %s AND peso < %s)  as p ON p.comuna_id = r.id) as p JOIN Consumo ON p.id = Consumo.id_persona WHERE Consumo.cantidad_mes != 0.0 AND "+ sql_alimentos + ";",[region["id"],min_edad, max_edad, min_peso, max_peso])
            res = cur.fetchall()

            formula = {}
            avg_peso = 0.0
            avg_contaminantes = {}
            for consumo in res:
                alimento = list(filter(lambda _alimento: _alimento['id'] == consumo[3], alimentos))
                if(len(preview) < 100):
                    preview.append({"edad":consumo[5],"sexo": _sexo[consumo[4]],"altura": consumo[6], "peso": consumo[1],"alimento": alimento[0]["nombre"],"cantidad consumida": consumo[2]})
                ws.append([consumo[0],_sexo[consumo[4]],consumo[5],consumo[6],consumo[1],consumo[2],alimento[0]["nombre"]])
                if not consumo[0] in personas:
                    reporte_region["c_personas"] += 1
                    avg_peso += consumo[1]
                    personas[consumo[0]] = "ok"
                '''
                    personas[consumo[0]] = {
                        "peso": consumo[1],
                        "consumos_mes":{
                            alimento[0]["nombre"]: consumo[2]
                        }
                    }
                else:
                    personas[consumo[0]]["consumos_mes"][alimento[0]["nombre"]] = consumo[2]
                '''

                for contaminante in contaminantes:
                    
                    if not contaminante["nombre"] in avg_contaminantes:
                        avg_contaminantes[contaminante["nombre"]] = 0.0
                    if(alimento[0][contaminante["nombre"]] == None):
                        continue
                    avg_contaminantes[contaminante["nombre"]] += (alimento[0][contaminante["nombre"]] * consumo[2])/(30*1000)

            avg_peso =  avg_peso / reporte_region["c_personas"]
            
            
            for contaminante in contaminantes:
                avg_contaminantes[contaminante["nombre"]] = avg_contaminantes[contaminante["nombre"]]/ reporte_region["c_personas"]
                if contaminante["limite_diario"] == None:
                    formula[contaminante["nombre"]] = "Sin Datos de limite diario"
                else:
                    formula[contaminante["nombre"]] = avg_contaminantes[contaminante["nombre"]] / (avg_peso * contaminante["limite_diario"])

            reporte_region["prom_peso"] = avg_peso
            reporte_region["prom_contaminantes"] = avg_contaminantes
            reporte_region["formula"] = formula

            reporte["regiones"][region["id"]] = reporte_region
            reporte["chile"]["c_personas"] += reporte_region["c_personas"]
            reporte["chile"]["prom_peso"] += avg_peso * reporte_region["c_personas"]
        
        reporte["chile"]["prom_peso"] = reporte["chile"]["prom_peso"] / reporte["chile"]["c_personas"]

        formula = {}
        avg_contaminantes = {}
        for region in regiones:
            for contaminante in contaminantes:
                if not contaminante["nombre"] in avg_contaminantes:
                    avg_contaminantes[contaminante["nombre"]] = 0.0
                avg_contaminantes[contaminante["nombre"]] += reporte["regiones"][region["id"]]["prom_contaminantes"][contaminante["nombre"]] * reporte["regiones"][region["id"]]["c_personas"]

        #print(avg_contaminantes)

        for contaminante in contaminantes:
            avg_contaminantes[contaminante["nombre"]] = avg_contaminantes[contaminante["nombre"]] / reporte["chile"]["c_personas"]
            if contaminante["limite_diario"] == None:
                formula[contaminante["nombre"]] = "Sin Datos de limite diario"
            else:
                formula[contaminante["nombre"]] = avg_contaminantes[contaminante["nombre"]] / (reporte["chile"]["prom_peso"]  * contaminante["limite_diario"])
        
        reporte["chile"]["prom_contaminantes"] = avg_contaminantes
        reporte["chile"]["formula"] = formula

        n_archivo = datetime.now().strftime("reporte_%d.%m.%Y_%H.%M.%S") + str(random.random())
        reporte["metadata"] = "http://152.74.52.7:5001/reporte/get/" + n_archivo
        #reporte["preview"] = preview

        wb.save("data/"+ n_archivo +".xlsx")
        return jsonify(reporte)
    
@app.route("/reporte/get/<string:archivo>", methods=["GET", "POST"])
def get_reporte(archivo):
    try:
        return send_from_directory("data", archivo + ".xlsx", as_attachment=True)
    except FileNotFoundError:
        return "ERROR"