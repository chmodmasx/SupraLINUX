# Política de seguridad

SupraLINUX es un proyecto personal. La seguridad se maneja de forma
responsable, sin SLA ni soporte comercial.

## Versiones soportadas

| Versión | Soporte |
|---|---|
| 1.0.x | Sí |
| Anteriores | No |

## Fallos en KDE o Ubuntu

Reportalos en los canales oficiales de KDE o Ubuntu. SupraLINUX reconstruye y
publica las actualizaciones cuando corresponde.

## Fallos en SupraLINUX

Aplican a packaging, defaults, instalador, repositorio, claves, permisos,
scripts privilegiados, tema y ajustes del sistema.

Reportá en privado:

1. `https://supralinux.com/bugs.html`, marcando “seguridad” en el resumen.
2. Cuando el repositorio esté público, se habilitará un aviso privado de
   seguridad (GitHub Security Advisory o equivalente).

No abras issues públicos para vulnerabilidades.

## Qué incluir

- Versión de SupraLINUX.
- Pasos para reproducir.
- Impacto y si el fallo es explotable.
- Logs relevantes.
- Configuración que se aparte de los defaults.

No incluyas datos personales de terceros.

## Tiempo de respuesta

Best-effort, sin SLA. Se priorizan los fallos con impacto real.

## Clave GPG

La clave pública de release está en `installer/keys/supralinux-archive-key.asc`.

Huella Ed25519:

```text
9BAD7A4B1826213B3BE271E208780B9EEC43C2B8
```

La clave privada y su passphrase viven en `SUPRALINUX_SECRETS`, nunca en el
repositorio.
