.pragma library

var es = {
    appTitle: "Recuperar SupraLINUX",
    heading: "Volver a un estado anterior",
    subtitle: "Elegí una instantánea del sistema para restaurarla. La raíz actual se conserva por si necesitás volver atrás.",
    warning: "Se restaura la raíz del sistema. Tus archivos personales en /home no se tocan. La raíz actual se guarda como @pre-rollback-<fecha>.",
    device: "Disco",
    noDevice: "No se encontró un sistema de archivos Btrfs.",
    noSnapshots: "No hay instantáneas disponibles. Si el sistema usa EXT4, no hay rollback con Snapper.",
    snapshotNumber: "Instantánea",
    restore: "Restaurar",
    close: "Cerrar",
    refresh: "Actualizar",
    confirmTitle: "Confirmar restauración",
    confirmText: "¿Restaurar la instantánea seleccionada?",
    progressTitle: "Restaurando",
    progressHeading: "Restaurando el sistema",
    stepVerify: "Verificando el disco",
    stepBackup: "Guardando la raíz actual",
    stepRestore: "Restaurando la instantánea",
    stepCleanup: "Limpiando",
    doNotClose: "No cierres la aplicación mientras se restaura el sistema.",
    successTitle: "Restauración completada",
    successText: "Listo. Reiniciá el equipo para usar la versión restaurada.",
    reboot: "Reiniciar ahora",
    errorTitle: "No se pudo restaurar",
    errorGeneric: "Ocurrió un error al restaurar la instantánea.",
    retry: "Volver a intentar",
    details: "Detalles",
    loading: "Buscando instantáneas…",
    latest: "Más reciente"
};

var en = {
    appTitle: "Recover SupraLINUX",
    heading: "Go back to an earlier state",
    subtitle: "Choose a system snapshot to restore. The current root is kept in case you need to go back.",
    warning: "The system root will be restored. Your personal files in /home are not touched. The current root is saved as @pre-rollback-<date>.",
    device: "Disk",
    noDevice: "No Btrfs filesystem was found.",
    noSnapshots: "No snapshots are available. If the system uses EXT4, Snapper rollback is not available.",
    snapshotNumber: "Snapshot",
    restore: "Restore",
    close: "Close",
    refresh: "Refresh",
    confirmTitle: "Confirm restore",
    confirmText: "Restore the selected snapshot?",
    progressTitle: "Restoring",
    progressHeading: "Restoring the system",
    stepVerify: "Checking the disk",
    stepBackup: "Saving the current root",
    stepRestore: "Restoring the snapshot",
    stepCleanup: "Cleaning up",
    doNotClose: "Do not close the application while the system is being restored.",
    successTitle: "Restore completed",
    successText: "Done. Restart the computer to use the restored version.",
    reboot: "Restart now",
    errorTitle: "Restore failed",
    errorGeneric: "An error occurred while restoring the snapshot.",
    retry: "Try again",
    details: "Details",
    loading: "Looking for snapshots…",
    latest: "Most recent"
};

function get(localeName) {
    return String(localeName).toLowerCase().indexOf("es") === 0 ? es : en;
}
