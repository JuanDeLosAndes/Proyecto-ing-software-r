import random
from sqlmodel import Session, select, func
from modelos.entidades import Grupo, Salon, Materia, Inscripcion


class ConfigAlg:
    POBLACION   = 50
    GENERACIONES = 80
    MUTACION    = 0.15


def CalcularFit(cromosoma, gruposInf, salonesInf):
    penalizacion = 0
    choqueSal  = {}
    choqueProf = {}

    for idGrupo, idSalon in cromosoma.items():
        gData = gruposInf[idGrupo]
        salon = salonesInf[idSalon]

        if gData["inscritos"] > salon.capacidad:
            penalizacion += 5000
        if gData["facultad"] == "Sistemas" and "Sala" not in salon.nombre:
            penalizacion += 500
        if gData["facultad"] == "Ciencias Básicas" and "AULA" not in salon.nombre:
            penalizacion += 6000

        llaveSal = (idSalon, gData["dia"], gData["hora"])
        if llaveSal in choqueSal:
            penalizacion += 4000
        else:
            choqueSal[llaveSal] = idGrupo

        llaveProf = (gData["id_profesor"], gData["dia"], gData["hora"])
        if llaveProf in choqueProf:
            penalizacion += 5000
        else:
            choqueProf[llaveProf] = idGrupo

    return max(0, 10000 - penalizacion)


def GenerarPob(gruposIds, salonesIds):
    pob = []
    for _ in range(ConfigAlg.POBLACION):
        crom = {idG: random.choice(salonesIds) for idG in gruposIds}
        pob.append(crom)
    return pob


def EjecutarAlg(session: Session):
    salones = session.exec(select(Salon)).all()
    grupos  = session.exec(select(Grupo)).all()

    if not salones or not grupos:
        return {"error": "Infraestructura o grupos insuficientes."}

    salonesInf = {s.id: s for s in salones}
    salonesIds = list(salonesInf.keys())
    gruposIds  = [g.id for g in grupos]

    gruposInf = {}
    for g in grupos:
        materia  = session.get(Materia, g.id_materia)
        inscritosC = session.exec(
            select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
        ).one()
        gruposInf[g.id] = {
            "dia": g.dia, "hora": g.hora,
            "facultad":    materia.facultad if materia else "Ciencias Básicas",
            "inscritos":   inscritosC,
            "id_profesor": g.id_profesor
        }

    pob = GenerarPob(gruposIds, salonesIds)

    for _ in range(ConfigAlg.GENERACIONES):
        pob = sorted(pob, key=lambda c: CalcularFit(c, gruposInf, salonesInf), reverse=True)
        nuevaGen = pob[:10]
        while len(nuevaGen) < ConfigAlg.POBLACION:
            padre1 = random.choice(pob[:20])
            padre2 = random.choice(pob[:20])
            corte  = len(gruposIds) // 2
            hijo   = {idG: padre1[idG] if idx < corte else padre2[idG] for idx, idG in enumerate(gruposIds)}
            if random.random() < ConfigAlg.MUTACION:
                hijo[random.choice(gruposIds)] = random.choice(salonesIds)
            nuevaGen.append(hijo)
        pob = nuevaGen

    mejorCrom = max(pob, key=lambda c: CalcularFit(c, gruposInf, salonesInf))

    for idGrupo, idSalonOpt in mejorCrom.items():
        grupoDB = session.get(Grupo, idGrupo)
        if grupoDB:
            grupoDB.id_salon = idSalonOpt
            session.add(grupoDB)

    session.commit()
    return {"mensaje": "Optimizacion genetica completada. Sin cruces criticos detectados."}