from sqlmodel import SQLModel, create_engine, Session, select, func
from models import Salon, Materia, Rol, Usuario, Estudiante, Profesor, Administrador, ConfiguracionFront, Grupo, Inscripcion
import random

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        inicializar_sistema_completo(session)
        sembrar_datos_prueba(session)

def get_session():
    with Session(engine) as session:
        yield session

def sembrar_datos_prueba(session: Session):
    if session.exec(select(Inscripcion)).first():
        return

    print("Sembrando inscripciones masivas respetando aforos de la universidad...")
    estudiantes = session.exec(select(Estudiante)).all()
    materias = session.exec(select(Materia)).all()
    
    if estudiantes and materias:
        for est in estudiantes:
            materias_aleatorias = random.sample(materias, 4) if len(materias) >= 4 else materias
            for materia in materias_aleatorias:
                limite_cupo = 30 if materia.facultad == "Sistemas" else 35
                grupos_materia = session.exec(select(Grupo).where(Grupo.id_materia == materia.id)).all()
                
                grupo_asignado = None
                for g in grupos_materia:
                    inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one()
                    if inscritos < limite_cupo:
                        grupo_asignado = g
                        break
                
                if not grupo_asignado:
                    ultimo_grupo = grupos_materia[-1] if grupos_materia else None
                    if ultimo_grupo:
                        nuevo_grupo = Grupo(
                            num_grupo=len(grupos_materia) + 1,
                            id_materia=materia.id,
                            id_salon=ultimo_grupo.id_salon, 
                            id_profesor=ultimo_grupo.id_profesor,
                            dia=ultimo_grupo.dia,
                            hora=ultimo_grupo.hora
                        )
                        session.add(nuevo_grupo)
                        session.commit()
                        session.refresh(nuevo_grupo)
                        grupo_asignado = nuevo_grupo

                if grupo_asignado:
                    insc = Inscripcion(id_estudiante=est.id, id_materia=materia.id, id_grupo=grupo_asignado.id, estado="Activo")
                    session.add(insc)
                    
        session.commit()
        print(f"Se han matriculado {len(estudiantes)} estudiantes, creando los grupos necesarios para no exceder los límites.")

def inicializar_sistema_completo(session: Session):
    if session.exec(select(Salon)).first(): return

    rol_est = Rol(nombre_rol="Estudiante")
    rol_prof = Rol(nombre_rol="Profesor")
    rol_admin = Rol(nombre_rol="Administrador")
    session.add_all([rol_est, rol_prof, rol_admin])
    session.commit()

    config_inicial = ConfiguracionFront(
        mensaje_1="BIENVENIDO AL PORTAL UNIVERSITARIO",
        mensaje_2="Verifique sus horarios y salones asignados con anticipación para los próximos parciales.",
        mensaje_3="INFORMACIÓN IMPORTANTE",
        mensaje_4="Recuerde realizar la evaluación docente desde su portal antes del cierre del semestre.",
        url_img_1="https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=600",
        url_img_2="https://images.unsplash.com/photo-1562774053-701939374585?q=80&w=600",
        url_img_3="https://images.unsplash.com/photo-1541339907198-e08756dedf3f?q=80&w=600"
    )
    session.add(config_inicial)

    salas = [Salon(nombre=f"Sala de Computo {i}", capacidad=30) for i in range(1, 8)]
    aulas = [Salon(nombre=f"AULA-{301 + i}", capacidad=35) for i in range(14)]
    session.add_all(salas + aulas)
    session.commit()

    materias_sistemas = ["Algoritmia y programacion", "Estructuras de Datos", "Bases de Datos", "Redes computacionales"]
    materias_mate = ["Fundamentacion matematica", "Calculo diferencial", "Fisica I", "Fisica II"]

    lista_materias = []
    for m in materias_sistemas:
        mat = Materia(nombre=m, creditos=3, facultad="Sistemas", semestre=1)
        session.add(mat)
        lista_materias.append(mat)
    for m in materias_mate:
        mat = Materia(nombre=m, creditos=3, facultad="Ciencias Básicas", semestre=1)
        session.add(mat)
        lista_materias.append(mat)
    session.commit()

    print("Generando 140 estudiantes y profesores de prueba con nuevas reglas de ID...")
    usuarios_estudiantes = []
    for i in range(1, 141):
        # 6700 + 4 dígitos (Ej: 67001001) -> Total 8 dígitos
        u = Usuario(codigo=f"6700{1000+i}", contrasena="123", id_rol=rol_est.id)
        session.add(u)
        usuarios_estudiantes.append(u)

    # Profesores: 10 dígitos sin empezar en 6700 ni 9900
    u_prof1 = Usuario(codigo="1000000001", contrasena="123", id_rol=rol_prof.id) 
    u_prof2 = Usuario(codigo="1000000002", contrasena="4321", id_rol=rol_prof.id)     
    
    # Admin: 9900 + 4 dígitos -> Total 8 dígitos
    u_adm = Usuario(codigo="99001111", contrasena="123", id_rol=rol_admin.id)
    
    session.add_all([u_prof1, u_prof2, u_adm])
    session.commit()

    for i, u in enumerate(usuarios_estudiantes):
        perfil = Estudiante(nombre=f"Estudiante {u.codigo}", id_usuario=u.id)
        session.add(perfil)

    perfil_prof1 = Profesor(nombre="Carlos Mendoza", especialidad="Ingeniería de Sistemas", id_usuario=u_prof1.id)
    perfil_prof2 = Profesor(nombre="Juan", especialidad="Ciencias Básicas", id_usuario=u_prof2.id)
    perfil_adm = Administrador(nombre="UI Admin Global", codigo_admin="ADM-01", id_usuario=u_adm.id)
    
    session.add_all([perfil_prof1, perfil_prof2, perfil_adm])
    session.commit()

    g_s1 = Grupo(num_grupo=1, id_materia=lista_materias[0].id, id_salon=salas[0].id, id_profesor=perfil_prof1.id, dia="Lunes", hora="7:00")
    g_s2 = Grupo(num_grupo=1, id_materia=lista_materias[1].id, id_salon=salas[1].id, id_profesor=perfil_prof1.id, dia="Martes", hora="9:00")
    g_s3 = Grupo(num_grupo=1, id_materia=lista_materias[2].id, id_salon=salas[2].id, id_profesor=perfil_prof1.id, dia="Miercoles", hora="11:00")
    g_s4 = Grupo(num_grupo=1, id_materia=lista_materias[3].id, id_salon=salas[3].id, id_profesor=perfil_prof1.id, dia="Jueves", hora="13:00")

    g_c1 = Grupo(num_grupo=1, id_materia=lista_materias[4].id, id_salon=aulas[0].id, id_profesor=perfil_prof2.id, dia="Lunes", hora="9:00")
    g_c2 = Grupo(num_grupo=1, id_materia=lista_materias[5].id, id_salon=aulas[1].id, id_profesor=perfil_prof2.id, dia="Martes", hora="11:00")
    g_c3 = Grupo(num_grupo=1, id_materia=lista_materias[6].id, id_salon=aulas[2].id, id_profesor=perfil_prof2.id, dia="Miercoles", hora="14:00")
    g_c4 = Grupo(num_grupo=1, id_materia=lista_materias[7].id, id_salon=aulas[3].id, id_profesor=perfil_prof2.id, dia="Viernes", hora="7:00")
    
    session.add_all([g_s1, g_s2, g_s3, g_s4, g_c1, g_c2, g_c3, g_c4])
    session.commit()