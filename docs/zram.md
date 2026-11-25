# ZRAM en testing

`supralinux-defaults 1.2.7` habilita ZRAM sin umbral de memoria física.
La capacidad lógica es la mitad de MemTotal, limitada a 8192 MiB; LZ4 y
prioridad 100 se mantienen. No se reserva esa capacidad completa al inicio.
No sustituye el swap persistente necesario para hibernación.

Es una política experimental de testing, no una mejora de rendimiento medida.
Validar en VM con 2, 4, 8, 16 y 32 GiB: `zramctl`, `swapon --show`, presión
PSI, uso de memoria comprimida, CPU y eventos OOM. Comparar contra la política
1.2.6 bajo cargas idénticas. Registrar los resultados por configuración de VM.
No desactivar ni reinicializar swap activa durante una actualización: probar
la nueva configuración tras reiniciar. No se modifica la política de Firefox.

Referencia: https://github.com/systemd/zram-generator/blob/main/man/zram-generator.conf.md
