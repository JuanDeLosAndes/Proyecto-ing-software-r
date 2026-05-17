from sqlmodel import SQLModel, create_engine, Session, select
from models import Salon, Materia, Rol, Usuario, Estudiante, Profesor, Administrador, ConfiguracionFront, Grupo

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        inicializar_sistema_completo(session)

def get_session():
    with Session(engine) as session:
        yield session

def inicializar_sistema_completo(session: Session):
    if session.exec(select(Salon)).first():
        return  # Evita duplicaciones si la base de datos ya contiene registros

    # 1. Crear Roles del Sistema
    rol_est = Rol(nombre_rol="Estudiante")
    rol_prof = Rol(nombre_rol="Profesor")
    rol_admin = Rol(nombre_rol="Administrador")
    session.add_all([rol_est, rol_prof, rol_admin])
    session.commit()

    # 2. Crear Configuración Visual Global Inicial
    config_inicial = ConfiguracionFront(
        mensaje_superior="Bienvenido al sistema institucional de la Universidad Católica de Colombia. Gestiona tus horarios.",
        mensaje_inferior="La Universidad Católica de Colombia cuenta con acreditación de alta calidad, garantizando excelencia.",
        url_imagen="https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=600"
    )
    session.add(config_inicial)

    # 3. Crear Salones de Cómputo (Sistemas)
    salas = []
    for i in range(1, 8):
        cap = 30 if i == 7 else 20
        sala = Salon(nombre=f"Sala de Cómputo {i}", capacidad=cap)
        session.add(sala)
        salas.append(sala)

    # 4. Crear Aulas Teóricas (Matemáticas/Ciencias Básicas)
    aulas = []
    caps_aulas = [25, 30, 35, 28, 32, 26, 34, 30, 25, 35, 27, 33, 29, 31]
    for i in range(14):
        aula = Salon(nombre=f"AULA-{301 + i}", capacidad=caps_aulas[i])
        session.add(aula)
        aulas.append(aula)
    session.commit()

    # 5. Crear 20 Materias del Plan de Estudios
    materias_sistemas = [
        "Algoritmia y programación", "Introducción a la Teoría de la Computación",
        "Diseño y Programación Orientados a Objetos", "Estructuras de Datos",
        "Desarrollo de Software", "Bases de Datos", "Sistemas operativos",
        "Análisis y Diseño de Algoritmos", "Producción de Software", "Redes computacionales"
    ]
    materias_mate = [
        "Fundamentación matemática", "Álgebra lineal", "Cálculo diferencial",
        "Cálculo integral", "Probabilidad y estadística", "Ecuaciones diferenciales",
        "Cálculo vectorial", "Estructuras Discretas", "Física I", "Física II"
    ]

    lista_materias = []
    for idx, nom in enumerate(materias_sistemas):
        m = Materia(nombre=nom, creditos=3, facultad="Sistemas", semestre=(idx // 2) + 1)
        session.add(m)
        lista_materias.append(m)

    for idx, nom in enumerate(materias_mate):
        m = Materia(nombre=nom, creditos=3, facultad="Ciencias Básicas", semestre=(idx // 2) + 1)
        session.add(m)
        lista_materias.append(m)
    session.commit()

    # 6. Crear Usuarios de Prueba vinculados con el Diagrama E-R
    u_est = Usuario(codigo="67001234", contrasena="123", id_rol=rol_est.id)
    u_prof = Usuario(codigo="75004321", contrasena="123", id_rol=rol_prof.id)
    u_adm = Usuario(codigo="99001111", contrasena="123", id_rol=rol_admin.id)
    session.add_all([u_est, u_prof, u_adm])
    session.commit()

    perfil_est = Estudiante(nombre="Andrés Rodríguez", id_usuario=u_est.id)
    perfil_prof = Profesor(nombre="Carlos Mendoza", especialidad="Ingeniería de Software", id_usuario=u_prof.id)
    perfil_adm = Administrador(nombre="UI Admin Global", codigo_admin="ADM-01", id_usuario=u_adm.id)
    session.add_all([perfil_est, perfil_prof, perfil_adm])
    session.commit()

    # 7. Distribución Automática Inteligente de Clases Iniciales según condiciones
    # Grupo de Sistemas asignado automáticamente a una Sala de Computo disponible
    g_sistemas = Grupo(
        num_grupo=1, cupo_maximo=35, id_materia=lista_materias[3].id,  # Estructuras de Datos
        id_salon=salas[2].id, id_profesor=perfil_prof.id, dia="Martes", hora="7:00"
    )
    # Grupo de Matemáticas asignado automáticamente a un Aula Teórica
    g_mate = Grupo(
        num_grupo=1, cupo_maximo=35, id_materia=lista_materias[12].id,  # Cálculo diferencial
        id_salon=aulas[0].id, id_profesor=perfil_prof.id, dia="Jueves", hora="13:00"
    )
    session.add_all([g_sistemas, g_mate])
    session.commit()
    print("Datos institucionales, infraestructura fija y relaciones creadas con éxito.")