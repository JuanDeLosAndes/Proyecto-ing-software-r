import random
from sqlmodel import Session, select, func
from models import Grupo, Salon, Materia, Inscripcion

class Configuracion:
    TAMANO_POBLACION = 50
    GENERACIONES = 80
    TASA_MUTACION = 0.15

def calcular_fitness(cromosoma, grupos_info, salones_info):
    """
    cromosoma es un diccionario: {id_grupo: id_salon}
    Evalúa las restricciones universitarias reales. El fitness máximo ideal es 10000.
    """
    penalizacion = 0
    # Estructura de ocupación: {(id_salon, dia, hora): id_grupo}
    control_choques = {}

    for id_grupo, id_salon in cromosoma.items():
        g_data = grupos_info[id_grupo]
        salon = salones_info[id_salon]
        
        # 1. Validación de Capacidad de Aforo (Alumnos inscritos vs Capacidad del Salón)
        if g_data["inscritos"] > salon.capacidad:
            penalizacion += 2000  # Castigo severo por sobrecupo

        # 2. Validación de Segregación de Infraestructura Física
        if g_data["facultad"] == "Sistemas" and "Sala" not in salon.nombre:
            penalizacion += 3000  # Castigo crítico: Sistemas exige Sala de Cómputo
            
        if g_data["facultad"] == "Ciencias Básicas" and "AULA" not in salon.nombre:
            penalizacion += 3000  # Castigo crítico: Matemáticas exige Aulas Teóricas

        # 3. Validación de Choques de Horarios (Mismo Salón, Mismo Día, Misma Hora)
        llave_tiempo = (id_salon, g_data["dia"], g_data["hora"])
        if llave_tiempo in control_choques:
            penalizacion += 4000  # Colisión horaria en infraestructura
        else:
            control_choques[llave_tiempo] = id_grupo

    return max(0, 10000 - penalizacion)

def generar_poblacion_inicial(grupos_ids, salones_ids):
    poblacion = []
    for _ in range(Configuracion.TAMANO_POBLACION):
        cromosoma = {id_g: random.choice(salones_ids) for id_g in grupos_ids}
        poblacion.append(cromosoma)
    return poblacion

def ejecutar_algoritmo_universitario(session: Session):
    """
    Optimiza de forma genética la asignación de salones persistiendo 
    los resultados en la base de datos real.
    """
    # 1. Extraer infraestructura y asignaciones de la BD
    salones = session.exec(select(Salon)).all()
    grupos = session.exec(select(Grupo)).all()
    
    if not salones or not grupos:
        return {"error": "Infraestructura o grupos insuficientes en la Base de Datos para optimizar."}

    salones_info = {s.id: s for s in salones}
    salones_ids = list(salones_info.keys())
    grupos_ids = [g.id for g in grupos]

    # Pre-cargar en memoria la información cruzada para acelerar el procesamiento genético (Optimización de Rendimiento)
    grupos_info = {}
    for g in grupos:
        materia = session.get(Materia, g.id_materia)
        inscritos_count = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one()
        grupos_info[g.id] = {
            "dia": g.dia,
            "hora": g.hora,
            "facultad": materia.facultad if materia else "Ciencias Básicas",
            "inscritos": inscritos_count
        }

    # 2. Inicializar Población
    poblacion = generar_poblacion_inicial(grupos_ids, salones_ids)

    # 3. Ciclo Evolutivo
    for _ in range(Configuracion.GENERACIONES):
        # Evaluar aptitud y ordenar de mayor a menor fitness
        poblacion = sorted(poblacion, key=lambda c: calcular_fitness(c, grupos_info, salones_info), reverse=True)
        
        # Selección Elitista (Preservamos los 10 mejores cromosomas)
        nueva_generacion = poblacion[:10]

        # Cruce y Mutación para completar la población restante
        while len(nueva_generacion) < Configuracion.TAMANO_POBLACION:
            padre1 = random.choice(poblacion[:20])
            padre2 = random.choice(poblacion[:20])

            # Crossover de un punto
            corte = len(grupos_ids) // 2
            hijo = {}
            for idx, id_g in enumerate(grupos_ids):
                hijo[id_g] = padre1[id_g] if idx < corte else padre2[id_g]

            # Mutación Aleatoria
            if random.random() < Configuracion.TASA_MUTACION:
                grupo_mutar = random.choice(grupos_ids)
                hijo[grupo_mutar] = random.choice(salones_ids)

            nueva_generacion.append(hijo)

        poblacion = nueva_generacion

    # 4. Obtener la solución óptima absoluta
    mejor_cromosoma = max(poblacion, key=lambda c: calcular_fitness(c, grupos_info, salones_info))

    # 5. AGREGAR PERSISTENCIA: Aplicar y guardar los salones optimizados en la DB real
    for id_grupo, id_salon_optimo in mejor_cromosoma.items():
        grupo_db = session.get(Grupo, id_grupo)
        if grupo_db:
            grupo_db.id_salon = id_salon_optimo
            session.add(grupo_db)
            
    session.commit()
    return {"mensaje": "Asignación de infraestructura resuelta exitosamente mediante optimización genética."}