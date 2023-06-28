import openpyxl

from __main__ import app, mysql, request, jsonify

@app.route("/reporte", methods=["GET", "POST"])
def reporte():
    cur = mysql.connection.cursor()
    if request.method == "POST":
        reporte = {}
        request_json = request.get_json()
        sexo = request_json["sexo"]
        s = ""
        if(sexo != 0):
            s = "sexo = " + sexo.to_string() - 1 + " AND"
        min_edad = request_json["edad"][0]
        max_edad = request_json["edad"][1]
        min_peso = request_json["peso"][0]
        max_peso = request_json["peso"][1]
        alimentos = request_json.get("alimentos")
        contaminantes = request_json.get("contaminantes")
        valores_referencia = {}
        id_contaminantes = {}
        for alimento in alimentos:
            cur.execute("SELECT id FROM Alimento WHERE nombre = %s",[alimento["nombre"]])
            res = cur.fetchall()
            if(res[0] is not None):
                alimento["id"] = res[0][0]
            else:
                return "error: alimento " + alimento["nombre"] + " no encontrado."
        
        print(alimentos.to_string())
            
        for contaminante in contaminantes:
            reporte[contaminante] = {}
            reporte[contaminante]["promedio contaminante"] = 0
            cur.execute("SELECT limite_diario, id FROM Contaminante WHERE nombre= %s",[contaminante]) #de momento se trabaja con el cadmio
            res = cur.fetchall()
            if(res[0] is not None):
                valores_referencia[contaminante] = res[0][0]
                id_contaminantes[contaminante] = res[0][1]
        
        for contaminante in contaminantes:
            if(not contaminante in id_contaminantes):
                continue

            reporte[contaminante]["alimento"] = {}
            for alimento in alimentos:

                reporte[contaminante]["alimento"][alimento] = {}
                
                formula = 0.0
                c_personas = 0
                max_formula = 0.0

                if  valores_referencia[contaminante] == None or float(valores_referencia[contaminante]) == 0.0: 
                    continue

                cur.execute("SELECT Avg(cantidad)  FROM  Muestra WHERE id_contaminante=%s AND id_alimento=%s" ,([id_contaminantes[contaminante]],[alimento["id"]]))
                promedio_contaminante = cur.fetchone()[0]

                if(promedio_contaminante == None):
                    promedio_contaminante = 0.0

                cur.execute("SELECT p.id, p.peso, Consumo.cantidad_mes FROM (SELECT * FROM Persona WHERE "+ s +" edad > %s AND edad < %s AND peso > %s AND peso < %s) AS p LEFT JOIN Consumo ON p.id = Consumo.id_persona WHERE Consumo.id_alimento=%s AND Consumo.cantidad_mes != 0.0;",[min_edad, max_edad, min_peso, max_peso, alimento["id"]])

                personas = cur.fetchall()

                for persona in personas:
                    formula_actual = (float(persona[2]/30)/1000.0 * float(promedio_contaminante))/(float(valores_referencia[contaminante]) * float(persona[1]))
                    if(formula_actual  > max_formula):
                        max_formula= formula_actual

                    formula += formula_actual
                    c_personas += 1
                
                if(c_personas != 0):
                    reporte[contaminante]["alimento"][alimento]["peor_caso"] = max_formula
                    reporte[contaminante]["alimento"][alimento]["cantidad_de_personas"] = c_personas
                    reporte[contaminante]["alimento"][alimento]["promedio_alimento"] = (formula/c_personas)
                else:
                    reporte[contaminante]["alimento"][alimento]["peor_caso"] = 0
                    reporte[contaminante]["alimento"][alimento]["cantidad_de_personas"] = c_personas
                    reporte[contaminante]["alimento"][alimento]["promedio_alimento"] = 0
        
        print(str(reporte))

        for contaminante in contaminantes:
            if(not contaminante in id_contaminantes):
                continue
            promedio_contaminante = 0
            for alimento  in alimentos:
                if("promedio_alimento" in reporte[contaminante]["alimento"][alimento]):
                    promedio_contaminante += reporte[contaminante]["alimento"][alimento]["promedio_alimento"]

            reporte[contaminante]["promedio contaminante"] = promedio_contaminante
            
        return jsonify(reporte)
    
    elif request.method == "GET":
        respuesta = {}
        nombre_alimentos = {}
        cur.execute("SELECT * FROM Alimento;")
        alimentos = cur.fetchall()
        for alimento in alimentos:
            nombre_alimentos[alimento[0]] = alimento[1]

        cur.execute("SELECT * FROM Consumo;")
        consumos = cur.fetchall()
        for consumo in consumos:
            if consumo[0] in respuesta:
                if(consumo[3] != 0.0):
                    respuesta[consumo[0]][nombre_alimentos[consumo[1]]] = consumo[3]
            else:
                respuesta[consumo[0]] = {}
                if(consumo[3] != 0.0):
                    respuesta[consumo[0]][nombre_alimentos[consumo[1]]] = consumo[3]
        return jsonify(respuesta)
    
    else:
        return "Error"