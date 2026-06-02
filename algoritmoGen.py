import random
from sqlmodel import Session, select, func
from modelos.entidades import Grupo, Salon, Materia, Inscripcion


class ConfigAlg:

    POBLACION    = 50
    GENERACIONES = 80
    MUTACION     = 0.15
    ELITE        = 10


def CalcularFit(cromosoma: dict, gruposInf: dict, salonesInf: dict) -> int:
 
    penalizacion = 0
    choqueSal:  dict = {}
    choqueProf: dict = {}

    for idGrupo, (idSalon, idSalon2) in cromosoma.items():
        gData = gruposInf.get(idGrupo)
        if not gData:
            continue

        salon = salonesInf.get(idSalon)
        if not salon:
            continue

        if gData["inscritos"] > salon.capacidad:
            penalizacion += 5000
        if gData["facultad"] == "Ciencias Básicas" and "Sala" in salon.nombre:
            penalizacion += 6000
        elif gData["facultad"] == "Sistemas" and "AULA" in salon.nombre:
            penalizacion += 500

        llave_sal1 = (idSalon, gData["dia"], gData["hora"])
        if llave_sal1 in choqueSal:
            penalizacion += 4000
        else:
            choqueSal[llave_sal1] = idGrupo

        if gData["id_profesor"]:
            llave_prof1 = (gData["id_profesor"], gData["dia"], gData["hora"])
            if llave_prof1 in choqueProf:
                penalizacion += 5000
            else:
                choqueProf[llave_prof1] = idGrupo

        if idSalon2 and gData.get("dia2") and gData.get("hora2"):
            salon2 = salonesInf.get(idSalon2)
            if not salon2:
                continue

            if gData["inscritos"] > salon2.capacidad:
                penalizacion += 5000
            if gData["facultad"] == "Ciencias Básicas" and "Sala" in salon2.nombre:
                penalizacion += 6000
            elif gData["facultad"] == "Sistemas" and "AULA" in salon2.nombre:
                penalizacion += 500

            llave_sal2 = (idSalon2, gData["dia2"], gData["hora2"])
            if llave_sal2 in choqueSal:
                penalizacion += 4000
            else:
                choqueSal[llave_sal2] = idGrupo

            if gData["id_profesor"]:
                llave_prof2 = (gData["id_profesor"], gData["dia2"], gData["hora2"])
                if llave_prof2 in choqueProf:
                    penalizacion += 5000
                else:
                    choqueProf[llave_prof2] = idGrupo

    return max(0, 10000 - penalizacion)


def _GenerarPob(gruposIds: list, salonesIdsSis: list, salonesIdsBasic: list,
                gruposInf: dict) -> list:
    pob = []
    for _ in range(ConfigAlg.POBLACION):
        crom = {}
        for idG in gruposIds:
            facultad = gruposInf[idG]["facultad"]
            if facultad == "Sistemas" and salonesIdsSis:
                opciones = salonesIdsSis
            elif facultad == "Ciencias Básicas" and salonesIdsBasic:
                opciones = salonesIdsBasic
            else:
                opciones = salonesIdsSis + salonesIdsBasic
            crom[idG] = (random.choice(opciones), random.choice(opciones))
        pob.append(crom)
    return pob


def _Cruzar(p1: dict, p2: dict, gruposIds: list) -> dict:
    corte = len(gruposIds) // 2
    return {
        idG: (p1[idG][0] if idx < corte else p2[idG][0],
              p1[idG][1] if idx < corte else p2[idG][1])
        for idx, idG in enumerate(gruposIds)
    }


def _Mutar(crom: dict, gruposIds: list, salonesIdsSis: list,
           salonesIdsBasic: list, gruposInf: dict) -> dict:
    idG_mut  = random.choice(gruposIds)
    facultad = gruposInf[idG_mut]["facultad"]
    if facultad == "Sistemas" and salonesIdsSis:
        opciones = salonesIdsSis
    elif facultad == "Ciencias Básicas" and salonesIdsBasic:
        opciones = salonesIdsBasic
    else:
        opciones = salonesIdsSis + salonesIdsBasic
    crom[idG_mut] = (random.choice(opciones), random.choice(opciones))
    return crom


def EjecutarAlg(session: Session) -> dict:

    salones = session.exec(select(Salon)).all()
    grupos  = session.exec(select(Grupo)).all()

    if not salones or not grupos:
        return {"error": "No hay salones o grupos en la base de datos."}

    salonesInf      = {s.id: s for s in salones}
    salonesIdsSis   = [s.id for s in salones if "Sala" in s.nombre]
    salonesIdsBasic = [s.id for s in salones if "AULA" in s.nombre]
    gruposIds       = [g.id for g in grupos]

    gruposInf: dict = {}
    for g in grupos:
        materia   = session.get(Materia, g.id_materia)
        inscritos = session.exec(
            select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
        ).one()
        gruposInf[g.id] = {
            "dia":        g.dia,  "hora":  g.hora,
            "dia2":       g.dia2, "hora2": g.hora2,
            "facultad":   materia.facultad if materia else "Ciencias Básicas",
            "inscritos":  inscritos,
            "id_profesor": g.id_profesor,
        }

    pob = _GenerarPob(gruposIds, salonesIdsSis, salonesIdsBasic, gruposInf)

    for _ in range(ConfigAlg.GENERACIONES):
        pob = sorted(pob, key=lambda c: CalcularFit(c, gruposInf, salonesInf), reverse=True)
        nueva_gen = pob[:ConfigAlg.ELITE]
        while len(nueva_gen) < ConfigAlg.POBLACION:
            p1   = random.choice(pob[:20])
            p2   = random.choice(pob[:20])
            hijo = _Cruzar(p1, p2, gruposIds)
            if random.random() < ConfigAlg.MUTACION:
                hijo = _Mutar(hijo, gruposIds, salonesIdsSis, salonesIdsBasic, gruposInf)
            nueva_gen.append(hijo)
        pob = nueva_gen

    mejor     = max(pob, key=lambda c: CalcularFit(c, gruposInf, salonesInf))
    fit_final = CalcularFit(mejor, gruposInf, salonesInf)

    cambios = 0
    for idGrupo, (idSal1, idSal2) in mejor.items():
        g = session.get(Grupo, idGrupo)
        if g:
            g.id_salon  = idSal1
            g.id_salon2 = idSal2
            session.add(g)
            cambios += 1
    session.commit()

    return {
        "mensaje":            "Optimizacion genetica completada.",
        "fitness":            fit_final,
        "grupos_actualizados": cambios,
        "optimo":             fit_final == 10000,
    }