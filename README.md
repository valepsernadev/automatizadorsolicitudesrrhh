# Automatizador de solicitudes de RRHH

> 🚧 **Proyecto en construcción.** Este README se completará al terminar el proyecto.

Automatización que recibe solicitudes de empleados (vacaciones, certificados laborales, incapacidades y cambios de datos), las clasifica con IA, valida reglas de negocio y genera un reporte para Recursos Humanos. Los casos dudosos siempre pasan a revisión humana, con el motivo explicado.

Proyecto desarrollado como reto técnico para un cargo de Automatizador de IA. La empresa (*Talento Andino S.A.S.*) y todos los datos son ficticios.

## Tecnologías

- **Python** y **pandas**: carga y limpieza de datos
- **SQLite** y **SQL**: almacenamiento y consultas
- **API REST** ([Nager.Date](https://date.nager.at)): festivos de Colombia para calcular días hábiles
- **Gemini API**: clasificación de solicitudes y extracción de fechas
- **Power Automate para escritorio**: orquestación, verificación y registro
- **pytest**: pruebas automáticas

## Avance

- [ ] Misión 1: Datos limpios (Python y SQL)
- [ ] Misión 2: Días hábiles con una API REST
- [ ] Misión 3: IA con revisión humana
- [ ] Misión 4: Orquestación con Power Automate
- [ ] Misión 5: Calidad y documentación

## Estructura

```
data/      Datos de entrada (ficticios)
src/       Código fuente
outputs/   Resultados y reportes
docs/      Documentación y decisiones
tests/     Pruebas
```
