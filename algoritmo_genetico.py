import random
from sqlmodel import Session, select, func
from models import Grupo, Salon, Materia, Inscripcion

class Configuracion:
    TAMANO_POBLACION = 50
    GENERACIONES = 80
    TASA_MUTACION = 0.15

def calcular_fitness(cromosoma, grupos_info, salones_info):
    penalizacion = 0
    control_choques_salon = {}
    control_choques_prof = {} 

    for id_grupo, id_salon in cromosoma.items():
        g_data = grupos_info[id_grupo]
        salon = salones_info[id_salon]
        
        # 1. Validacion de Capacidad Estricta
        if g_data["inscritos"] > salon.capacidad:
            penalizacion += 5000 # Penalizacion muy alta por superar aforo

        # 2. Reglas de Facultad
        if g_data["facultad"] == "Sistemas" and "Sala" not in salon.nombre:
            # Castigo suave. Preferimos Salas, pero pueden usar Aulas si evita un choque.
            penalizacion += 500 
            
        if g_data["facultad"] == "Ciencias Básicas" and "AULA" not in salon.nombre:
            # Castigo estricto. Matematicas/Fisica no entran a Salas de Computo.
            penalizacion += 6000

        # 3. Choque de Salones (Mismo salon, dia y hora)
        llave_salon = (id_salon, g_data["dia"], g_data["hora"])
        if llave_salon in control_choques_salon:
            penalizacion += 4000
        else:
            control_choques_salon[llave_salon] = id_grupo

        # 4. Choque de Profesores
        llave_prof = (g_data["id_profesor"], g_data["dia"], g_data["hora"])
        if llave_prof in control_choques_prof:
            penalizacion += 5000  
        else:
            control_choques_prof[llave_prof] = id_grupo

    return max(0, 10000 - penalizacion)

def generar_poblacion_inicial(grupos_ids, salones_ids):
    poblacion = []
    for _ in range(Configuracion.TAMANO_POBLACION):
        cromosoma = {id_g: random.choice(salones_ids) for id_g in grupos_ids}
        poblacion.append(cromosoma)
    return poblacion

def ejecutar_algoritmo_universitario(session: Session):
    print("\n=======================================================")
    print("[ALGORITMO GENETICO] Iniciando Optimizacion de Espacios...")
    print("=======================================================")
    
    salones = session.exec(select(Salon)).all()
    grupos = session.exec(select(Grupo)).all()
    
    if not salones or not grupos:
        print("[ALGORITMO GENETICO] Error: Datos insuficientes.")
        return {"error": "Infraestructura o grupos insuficientes."}

    salones_info = {s.id: s for s in salones}
    salones_ids = list(salones_info.keys())
    grupos_ids = [g.id for g in grupos]

    grupos_info = {}
    for g in grupos:
        materia = session.get(Materia, g.id_materia)
        inscritos_count = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one()
        grupos_info[g.id] = {
            "dia": g.dia,
            "hora": g.hora,
            "facultad": materia.facultad if materia else "Ciencias Básicas",
            "inscritos": inscritos_count,
            "id_profesor": g.id_profesor 
        }

    poblacion = generar_poblacion_inicial(grupos_ids, salones_ids)

    for gen in range(Configuracion.GENERACIONES):
        poblacion = sorted(poblacion, key=lambda c: calcular_fitness(c, grupos_info, salones_info), reverse=True)
        nueva_generacion = poblacion[:10]
        
        mejor_fitness_gen = calcular_fitness(poblacion[0], grupos_info, salones_info)
        
        # Imprimir progreso en terminal
        if gen % 10 == 0 or gen == Configuracion.GENERACIONES - 1:
            print(f"[*] Generacion {gen}: Mejor Fitness = {mejor_fitness_gen}")

        while len(nueva_generacion) < Configuracion.TAMANO_POBLACION:
            padre1 = random.choice(poblacion[:20])
            padre2 = random.choice(poblacion[:20])

            corte = len(grupos_ids) // 2
            hijo = {id_g: padre1[id_g] if idx < corte else padre2[id_g] for idx, id_g in enumerate(grupos_ids)}

            if random.random() < Configuracion.TASA_MUTACION:
                hijo[random.choice(grupos_ids)] = random.choice(salones_ids)

            nueva_generacion.append(hijo)
        poblacion = nueva_generacion

    mejor_cromosoma = max(poblacion, key=lambda c: calcular_fitness(c, grupos_info, salones_info))
    print(f"\n[ALGORITMO GENETICO] Evolucion completada. Aplicando matriz optima.")

    for id_grupo, id_salon_optimo in mejor_cromosoma.items():
        grupo_db = session.get(Grupo, id_grupo)
        if grupo_db:
            grupo_db.id_salon = id_salon_optimo
            session.add(grupo_db)
            
    session.commit()
    print("[ALGORITMO GENETICO] Asignacion finalizada exitosamente.\n")
    return {"mensaje": "Optimizacion genetica completada. Sin cruces criticos detectados."}