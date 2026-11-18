# Reutilización

## Referencia preservada

El proyecto anterior se conserva como referencia de sólo lectura:

```text
/mnt/RAID0/SupraLINUX_OS/repo
rama: campaign/6.6.7
commit: 2643f8e
```

No se modifica, no se copia en bloque y no se usa como historia del proyecto
nuevo. La historia nueva empieza en `aa80781` y no contiene commits, ramas ni
tags anteriores.

## Reglas

Antes de reutilizar código, packaging, documentación o evidencia:

1. Revisar función, inputs y alcance.
2. Comprobar que no depende de una versión, ruta o decisión muerta.
3. Verificar hashes y procedencia.
4. Registrar el commit original y los cambios en este documento.
5. Crear un commit nuevo con un mensaje que describa el resultado, no el
   recorrido anterior.

No se reutilizan:

- `AGENTS.md` ni instrucciones internas del proyecto anterior.
- Manifests, ISOs, discos, claves o credenciales anteriores como verdad vigente.
- La historia de 498 commits ni sus ramas de campaña.
- Datos personales, rutas internas, capturas del host o logs sin sanear.
- Paquetes con parches obsoletos o dependencias que ya no existan en la base.

Un artifact heredado sólo se admite como input después de comprobar SHA-256,
versión, arquitectura, dependencias y que su build siga siendo aplicable. No
certifica un build nuevo ni una release.

## Registro de importaciones

| Área | Referencia anterior | Commit nuevo | Cambios aplicados | Estado |
|---|---|---|---|---|
| Portada y licencias | Textos estándar GPL/LGPL/CC/OFL/BSD | `aa80781` | Documentos nuevos; no se copió contenido del proyecto anterior | Hecho |
| Producto, arquitectura y packaging | `docs/product.md` y notas de campaña | `94a6e55` | Reescrito para la identidad y las decisiones de 1.0.0 | Hecho |
| Frameworks 6.24 | `packages/kde/` | — | Pendiente de revisión paquete por paquete | Pendiente |
| Plasma 6.6.7 | `packages/plasma/` | — | Pendiente de revisión paquete por paquete | Pendiente |
| Gear 25.12.3 | `packages/gear/` y `packages/complete/` | — | Renombrar a `gear-extras`; revisar dependencias | Pendiente |
| Integración de escritorio | `packages/desktop/` | — | Revisar defaults, tema, base-files y hardware | Pendiente |
| Firefox y l10n | `packages/` y notas de mirror | — | Pasar al repositorio oficial de Mozilla; retirar mirror y cron | Pendiente |
| Calamares | `installer/calamares/` | — | Empaquetar como `supralinux-calamares-config`; retirar `calamares-settings-kubuntu` | Pendiente |
| Live y arranque | `tools/live/` | — | Revisar hooks, shim/GRUB firmados y sellado | Pendiente |
| Branding | `branding/` | — | Revisar licencias, assets y textos | Pendiente |
| Herramientas y pruebas | `tools/` y `tests/` | — | Revisar contratos, quitar rutas y `__pycache__` | Pendiente |
| Evidencia anterior | `evidence/` | — | Sólo diagnóstico; no se usa como PASS de release | Pendiente |

Cada importación actualiza esta tabla en el mismo commit o en el commit de
documentación inmediatamente posterior.

## Criterio de revisión

Para cada paquete o script se registra:

- Qué hacía y qué problema resolvía.
- Qué inputs usa y si siguen disponibles.
- Qué cambió respecto de la referencia anterior.
- Qué pruebas se ejecutaron.
- Qué licencia y copyright aplican.

Si no se puede explicar el alcance, no se importa.

## Evidencia

La evidencia anterior sirve para entender fallos y decisiones, no para certificar
la release nueva. Un resultado viejo se puede citar como diagnóstico si se
identifica el run y su hash; nunca se convierte en PASS de 1.0.0.

## Licencias de la reutilización

- El código y la configuración propios se distribuyen bajo GPL-2.0-or-later,
  salvo la excepción de `supralinux-drivers` (GPL-3.0-or-later).
- El arte se distribuye bajo CC-BY-4.0; los sonidos, bajo CC0-1.0.
- Las partes derivadas de KDE/Breeze conservan LGPL-2.1-or-later.
- Las fuentes conservan OFL-1.1.
- Los terceros conservan la licencia de su `debian/copyright`.

La reutilización no cambia la licencia de un componente de terceros.
