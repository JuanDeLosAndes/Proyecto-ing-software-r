from sqlmodel import SQLModel, create_engine, Session, select
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

    print("Sembrando inscripciones aleatorias masivas para estresar la IA...")
    estudiantes = session.exec(select(Estudiante)).all()
    grupos = session.exec(select(Grupo)).all()
    
    if estudiantes and grupos:
        for est in estudiantes:
            grupos_aleatorios = random.sample(grupos, 4) if len(grupos) >= 4 else grupos
            for grupo in grupos_aleatorios:
                insc = Inscripcion(id_estudiante=est.id, id_materia=grupo.id_materia, id_grupo=grupo.id, estado="Activo")
                session.add(insc)
        session.commit()
        print(f"Se han matriculado {len(estudiantes)} estudiantes automaticamente en 4 materias cada uno.")

def inicializar_sistema_completo(session: Session):
    if session.exec(select(Salon)).first(): return

    rol_est = Rol(nombre_rol="Estudiante")
    rol_prof = Rol(nombre_rol="Profesor")
    rol_admin = Rol(nombre_rol="Administrador")
    session.add_all([rol_est, rol_prof, rol_admin])
    session.commit()

    # =========================================================================
    # NUEVOS MENSAJES INSTITUCIONALES (Sin emojis y con temática universitaria)
    # =========================================================================
    config_inicial = ConfiguracionFront(
        mensaje_superior="AVISO INSTITUCIONAL: Se acercan los examenes parciales. Por favor, verifiquen sus horarios y salones asignados con anticipacion para evitar contratiempos de ultima hora.",
        mensaje_inferior="INFORMACION: Recuerde realizar la evaluacion docente desde su portal antes del cierre del semestre. Su opinion es vital para mantener la alta calidad de la universidad.",
        url_imagen="https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=600"
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

    print("Generando 140 estudiantes y profesores de prueba...")
    usuarios_estudiantes = []
    for i in range(1, 141):
        u = Usuario(codigo=f"E{1000+i}", contrasena="123", id_rol=rol_est.id)
        session.add(u)
        usuarios_estudiantes.append(u)

    u_prof1 = Usuario(codigo="75004321", contrasena="123", id_rol=rol_prof.id) 
    u_prof2 = Usuario(codigo="9999", contrasena="4321", id_rol=rol_prof.id)     
    u_adm = Usuario(codigo="99001111", contrasena="123", id_rol=rol_admin.id)
    
    session.add_all([u_prof1, u_prof2, u_adm])
    session.commit()

    for i, u in enumerate(usuarios_estudiantes):
        perfil = Estudiante(nombre=f"Estudiante de Prueba {i+1}", id_usuario=u.id)
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