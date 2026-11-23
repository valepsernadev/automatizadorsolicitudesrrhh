# Trampas detectadas en los datos

| # | Trampa | Dónde | Tratamiento previsto |
|---|---|---|---|
| 1 | Empleado duplicado | empleados.csv · E003 | Deduplicar por id_empleado (PK) y registrarlo en el log |
| 2 | Correo con mayúsculas y espacio | empleados.csv · E002 | strip() + lower() |
| 3 | Área vacía | empleados.csv · E004 | Marcar SIN_AREA, sin borrar la fila |
| 4 | Empleado inexistente | solicitudes.json · S10 (E009) | Revisión humana: "empleado inexistente" |
| 5 | Vacaciones sin fechas | S09 | Revisión humana: "vacaciones sin fechas" |
| 6 | Saldo insuficiente | S06 (E008: saldo 0, pide 8) | Revisión humana: "días pedidos > saldo" |
| 7 | Datos personales en el texto | S03 cédula · S04 celular · S11 correo | Enmascarar antes de la IA |
| 8 | Fechas relativas | S12 "ayer y hoy" | Resolver con fecha_recepcion |
| 9 | Sinónimos | S07 "constancia" | Prueba del clasificador |
| 10 | Festivos | 8 y 25 de diciembre | Descontar con Nager.Date |
| 11 | Incapacidad: ¿días hábiles o calendario? | S03, S12 | Supuesto documentado (pregunta para RRHH) |