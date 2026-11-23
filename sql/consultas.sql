-- nombre: consulta_a_provisional
-- (a) Solicitudes por categoría y área. PROVISIONAL: usa etiqueta_esperada solo para validar el SQL.
SELECT COALESCE(e.area, 'EMPLEADO_INEXISTENTE') AS area,
       s.etiqueta_esperada AS categoria,
       COUNT(*) AS total_solicitudes
FROM solicitudes s
LEFT JOIN empleados e ON e.id_empleado = s.id_empleado
GROUP BY 1, 2
ORDER BY 1, 2;


-- nombre: consulta_b_empleados_inexistentes
-- (b) Solicitudes de empleados que no existen en la nómina
SELECT s.id_solicitud, s.id_empleado, s.fecha_recepcion, s.canal
FROM solicitudes s
LEFT JOIN empleados e ON e.id_empleado = s.id_empleado
WHERE e.id_empleado IS NULL;


-- nombre: consulta_c_saldo_menor_5
-- (c) Empleados con menos de 5 días de vacaciones disponibles
SELECT id_empleado, nombre, area, dias_vacaciones_disponibles
FROM empleados
WHERE dias_vacaciones_disponibles < 5
ORDER BY dias_vacaciones_disponibles;