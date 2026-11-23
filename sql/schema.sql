-- Empleados limpios: una fila por empleado
CREATE TABLE IF NOT EXISTS empleados (
    id_empleado TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL, -- normalizado: minúsculas, sin espacios
    area TEXT NOT NULL, -- 'SIN_AREA' si venía vacía
    cargo TEXT,
    fecha_ingreso TEXT NOT NULL, -- ISO AAAA-MM-DD
    dias_vacaciones_disponibles INTEGER NOT NULL CHECK (dias_vacaciones_disponibles >= 0),
    documento TEXT NOT NULL -- texto: es un identificador, no un número
);

-- Solicitudes tal como llegan (sin FK a propósito: los huérfanos se conservan)
CREATE TABLE IF NOT EXISTS solicitudes (
    id_solicitud TEXT PRIMARY KEY,
    id_empleado TEXT NOT NULL,
    fecha_recepcion TEXT NOT NULL,
    canal TEXT NOT NULL CHECK (canal IN ('correo', 'chat', 'formulario')),
    texto TEXT NOT NULL,
    etiqueta_esperada TEXT -- inicial solo para medir la IA
);

-- Resultado de la IA (se llena en la Misión 3)
CREATE TABLE IF NOT EXISTS clasificaciones (
    id_solicitud TEXT PRIMARY KEY,
    categoria TEXT CHECK (categoria IN ('VACACIONES','CERTIFICADO_LABORAL','INCAPACIDAD','ACTUALIZACION_DATOS','OTRO')),
    confianza REAL CHECK (confianza BETWEEN 0 AND 1),
    fecha_inicio TEXT,
    fecha_fin TEXT
);

-- Registro de cada cambio de limpieza en la mision 1
CREATE TABLE IF NOT EXISTS log_limpieza (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_ejecucion TEXT NOT NULL,
    tabla TEXT NOT NULL,
    registro TEXT NOT NULL,
    campo TEXT,
    valor_original TEXT,
    valor_nuevo TEXT,
    regla TEXT NOT NULL
);