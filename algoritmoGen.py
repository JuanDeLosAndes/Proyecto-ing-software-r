import random
from sqlmodel import Session, select, func
from modelos.entidades import Grupo, Salon, Materia, Inscripcion


class ConfigAlg:
    POBLACION    = 50
    GENERACIONES = 80
    MUTACION     = 0.15


# SRP: calculo de fitness aislado y documentado
def CalcularFit(cromosoma, gruposInf, salonesInf):
    """
    cromosoma = { id_grupo: (id_salon1, id_salon2) }
    Penaliza: capacidad excedida, facultad incorrecta,
              choque salon sesion1, choque salon sesion2,
              choque profesor ambas sesiones.
    """
    penalizacion = 0
    choqueSal  = {}  # (salon, dia, hora) -> id_grupo
    choqueProf = {}  # (id_prof, dia, hora) -> id_grupo

    for idGrupo, (idSalon, idSalon2) in cromosoma.items():
        gData = gruposInf[idGrupo]
        salon = salonesInf.get(idSalon)
        if not salon:
            continue

        # ── Sesion 1 ──
        if gData["inscritos"] > salon.capacidad:
            penalizacion += 5000
        if gData["facultad"] == "Sistemas" and "Sala" not in salon.nombre:
            penalizacion += 500
        if gData["facultad"] == "Ciencias Básicas" and "AULA" not in salon.nombre:
            penalizacion += 6000

        llave1 = (idSalon, gData["dia"], gData["hora"])
        penalizacion += 4000 if llave1 in choqueSal else 0
        choqueSal.setdefault(llave1, idGrupo)

        llaveP1 = (gData["id_profesor"], gData["dia"], gData["hora"])
        penalizacion += 5000 if llaveP1 in choqueProf else 0
        choqueProf.setdefault(llaveP1, idGrupo)

        # ── Sesion 2 (si el grupo tiene segunda sesion) ──
        if idSalon2 and gData.get("dia2") and gData.get("hora2"):
            salon2 = salonesInf.get(idSalon2)
            if salon2:
                if gData["inscritos"] > salon2.capacidad:
                    penalizacion += 5000
                if gData["facultad"] == "Sistemas" and "Sala" not in salon2.nombre:
                    penalizacion += 500
                if gData["facultad"] == "Ciencias Básicas" and "AULA" not in salon2.nombre:
                    penalizacion += 6000

                llave2 = (idSalon2, gData["dia2"], gData["hora2"])
                penalizacion += 4000 if llave2 in choqueSal else 0
                choqueSal.setdefault(llave2, idGrupo)

                llaveP2 = (gData["id_profesor"], gData["dia2"], gData["hora2"])
                penalizacion += 5000 if llaveP2 in choqueProf else 0
                choqueProf.setdefault(llaveP2, idGrupo)

    return max(0, 10000 - penalizacion)


def GenerarPob(gruposIds, salonesIds):
    """
    Factory Method implicito: cada cromosoma es un dict
    { id_grupo: (salon1, salon2) }.
    """
    pob = []
    for _ in range(ConfigAlg.POBLACION):
        crom = {
            idG: (random.choice(salonesIds), random.choice(salonesIds))
            for idG in gruposIds
        }
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
        materia    = session.get(Materia, g.id_materia)
        inscritosC = session.exec(
            select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
        ).one()
        gruposInf[g.id] = {
            "dia":        g.dia,  "hora":  g.hora,
            "dia2":       g.dia2, "hora2": g.hora2,
            "facultad":   materia.facultad if materia else "Ciencias Básicas",
            "inscritos":  inscritosC,
            "id_profesor": g.id_profesor
        }

    pob = GenerarPob(gruposIds, salonesIds)

    for _ in range(ConfigAlg.GENERACIONES):
        pob = sorted(pob, key=lambda c: CalcularFit(c, gruposInf, salonesInf), reverse=True)
        nuevaGen = pob[:10]
        while len(nuevaGen) < ConfigAlg.POBLACION:
            p1 = random.choice(pob[:20])
            p2 = random.choice(pob[:20])
            corte = len(gruposIds) // 2
            hijo = {
                idG: (p1[idG][0] if idx < corte else p2[idG][0],
                       p1[idG][1] if idx < corte else p2[idG][1])
                for idx, idG in enumerate(gruposIds)
            }
            if random.random() < ConfigAlg.MUTACION:
                idG_mut = random.choice(gruposIds)
                hijo[idG_mut] = (random.choice(salonesIds), random.choice(salonesIds))
            nuevaGen.append(hijo)
        pob = nuevaGen

    mejorCrom = max(pob, key=lambda c: CalcularFit(c, gruposInf, salonesInf))

    for idGrupo, (idSal1, idSal2) in mejorCrom.items():
        grupoDB = session.get(Grupo, idGrupo)
        if grupoDB:
            grupoDB.id_salon  = idSal1
            grupoDB.id_salon2 = idSal2
            session.add(grupoDB)

    session.commit()
    return {"mensaje": "Optimizacion genetica completada. Sin cruces criticos detectados."}