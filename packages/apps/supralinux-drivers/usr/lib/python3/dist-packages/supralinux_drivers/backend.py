# SPDX-License-Identifier: GPL-3.0-or-later
"""Backend for the SupraLINUX driver manager.

Detection and driver selection are delegated to UbuntuDrivers and the
``ubuntu-drivers`` command line, the same components Ubuntu uses. This module
only presents the detected devices and asks the Ubuntu backend to apply the
selected driver; it does not choose kernel, module or NVIDIA package names.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import apt_pkg
from PyQt6.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    QThread,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from UbuntuDrivers import detect

from . import __version__


class DetectWorker(QThread):
    """Read the apt cache and the UbuntuDrivers device table off the UI thread."""

    detected = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            apt_pkg.init_config()
            apt_pkg.init_system()
            cache = apt_pkg.Cache(None)
            devices = detect.system_device_drivers(cache)
            self.detected.emit((cache, devices))
        except Exception as error:  # noqa: BLE001 - the UI needs the message
            self.failed.emit(str(error))


class Backend(QObject):
    devicesChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    progressChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    errorChanged = pyqtSignal()
    canApplyChanged = pyqtSignal()
    proprietaryInUseChanged = pyqtSignal()
    rebootRequiredChanged = pyqtSignal()
    applied = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._devices: list[dict[str, Any]] = []
        self._cache = None
        self._worker: DetectWorker | None = None
        self._process: QProcess | None = None
        self._process_output = ""
        self._commands: list[tuple[str, list[str]]] = []
        self._command_index = 0
        self._cancelled = False
        self._apply_needs_reboot = False
        self._busy = False
        self._progress = 0
        self._status = ""
        self._error = ""
        self._can_apply = False
        self._proprietary = False
        self._reboot_required = os.path.exists("/var/run/reboot-required")
        self.refresh()

    # ---- properties -----------------------------------------------------

    @pyqtProperty("QVariantList", notify=devicesChanged)
    def devices(self) -> list[dict[str, Any]]:
        return self._devices

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @pyqtProperty(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(str, notify=errorChanged)
    def error(self) -> str:
        return self._error

    @pyqtProperty(bool, notify=canApplyChanged)
    def canApply(self) -> bool:
        return self._can_apply

    @pyqtProperty(bool, notify=proprietaryInUseChanged)
    def proprietaryInUse(self) -> bool:
        return self._proprietary

    @pyqtProperty(bool, notify=rebootRequiredChanged)
    def rebootRequired(self) -> bool:
        return self._reboot_required

    @pyqtProperty(str, constant=True)
    def version(self) -> str:
        return __version__

    # ---- state helpers --------------------------------------------------

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _set_status(self, value: str) -> None:
        if self._status != value:
            self._status = value
            self.statusChanged.emit()

    def _set_error(self, value: str) -> None:
        if self._error != value:
            self._error = value
            self.errorChanged.emit()

    def _set_progress(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        if self._progress != value:
            self._progress = value
            self.progressChanged.emit()

    def _set_can_apply(self, value: bool) -> None:
        if self._can_apply != value:
            self._can_apply = value
            self.canApplyChanged.emit()

    def _set_proprietary(self, value: bool) -> None:
        if self._proprietary != value:
            self._proprietary = value
            self.proprietaryInUseChanged.emit()

    def _set_reboot_required(self, value: bool) -> None:
        if self._reboot_required != value:
            self._reboot_required = value
            self.rebootRequiredChanged.emit()

    # ---- detection ------------------------------------------------------

    @pyqtSlot()
    def refresh(self) -> None:
        if self._busy or self._worker is not None:
            return
        self._set_busy(True)
        self._set_progress(0)
        self._set_error("")
        self._set_status("Buscando dispositivos...")
        worker = DetectWorker(self)
        worker.detected.connect(self._on_detected)
        worker.failed.connect(self._on_detect_failed)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_detected(self, payload: object) -> None:
        cache, infos = payload  # type: ignore[misc]
        self._cache = cache
        self._build_model(infos)
        self._worker = None
        self._set_busy(False)

    def _on_detect_failed(self, message: str) -> None:
        self._worker = None
        self._set_busy(False)
        self._set_status("")
        self._set_error(f"No se pudo detectar el hardware: {message}")

    def _build_model(self, infos: dict[str, Any]) -> None:
        devices: list[dict[str, Any]] = []
        for modalias, info in sorted(
            infos.items(), key=lambda item: (item[1].get("vendor", ""), item[1].get("model", ""))
        ):
            drivers: list[dict[str, Any]] = []
            current = None
            recommended = None
            for name, driver_info in sorted(info.get("drivers", {}).items()):
                try:
                    package = self._cache[name]
                except KeyError:
                    continue
                installed = package.current_ver is not None
                if installed:
                    current = name
                if driver_info.get("recommended"):
                    recommended = name
                candidate = None
                if not installed:
                    depcache = apt_pkg.DepCache(self._cache)
                    candidate = depcache.get_candidate_ver(package)
                version = (package.current_ver or candidate)
                drivers.append(
                    {
                        "package": name,
                        "title": name,
                        "installed": installed,
                        "recommended": bool(driver_info.get("recommended")),
                        "free": bool(driver_info.get("free")),
                        "builtin": bool(driver_info.get("builtin")),
                        "fromDistro": bool(driver_info.get("from_distro")),
                        "version": version.ver_str if version is not None else "",
                    }
                )
            selected = current or "none"
            if info.get("manual_install"):
                status = "Driver instalado manualmente."
            elif current and current == recommended:
                status = "Usando el driver recomendado."
            elif current:
                status = "Usando un driver alternativo."
            elif drivers:
                status = "No hay ningún driver instalado."
            else:
                status = "No se encontraron drivers para este dispositivo."
            devices.append(
                {
                    "modalias": modalias,
                    "vendor": info.get("vendor", ""),
                    "model": info.get("model", ""),
                    "drivers": drivers,
                    "current": current,
                    "recommended": recommended,
                    "selected": selected,
                    "status": status,
                    "manualInstall": bool(info.get("manual_install")),
                    "hasNone": bool(current or drivers),
                }
            )
        self._devices = devices
        proprietary = any(
            driver["installed"] and not driver["free"]
            for device in devices
            for driver in device["drivers"]
        )
        self._set_proprietary(proprietary)
        self.devicesChanged.emit()
        self._recompute_changes()
        self._set_status("Sin cambios." if not self._can_apply else "Hay cambios pendientes.")

    # ---- selection ------------------------------------------------------

    def _recompute_changes(self) -> None:
        changes = [
            device
            for device in self._devices
            if device["selected"] != (device["current"] or "none")
        ]
        self._set_can_apply(bool(changes))
        if changes:
            self._set_status("Hay cambios pendientes. Aplicá para instalarlos.")
        elif not self._busy:
            self._set_status("Sin cambios.")

    @pyqtSlot(str, str)
    def selectDriver(self, modalias: str, package: str) -> None:
        for device in self._devices:
            if device["modalias"] != modalias:
                continue
            if package != "none" and all(
                driver["package"] != package for driver in device["drivers"]
            ):
                return
            device["selected"] = package
            break
        self.devicesChanged.emit()
        self._recompute_changes()

    @pyqtSlot()
    def revert(self) -> None:
        if self._busy:
            return
        for device in self._devices:
            device["selected"] = device["current"] or "none"
        self.devicesChanged.emit()
        self._recompute_changes()

    @pyqtSlot()
    def clearError(self) -> None:
        self._set_error("")

    # ---- apply through ubuntu-drivers ----------------------------------

    def _driver_command(self, package: str) -> tuple[str, list[str]]:
        args = [
            "/usr/bin/pkexec",
            "/usr/bin/env",
            "DEBIAN_FRONTEND=noninteractive",
            "/usr/bin/ubuntu-drivers",
            "install",
        ]
        if "dkms" in package:
            args.append("--include-dkms")
        args.append(package)
        return (f"Instalando {package}", args)

    def _remove_command(self, package: str) -> tuple[str, list[str]]:
        return (
            f"Quitando {package}",
            ["/usr/bin/pkexec", "/usr/bin/env", "DEBIAN_FRONTEND=noninteractive",
             "/usr/bin/apt-get", "remove", "--auto-remove", "-y", package],
        )

    @pyqtSlot()
    def apply(self) -> None:
        if self._busy or not self._can_apply:
            return

        installs: list[str] = []
        removals: list[str] = []
        for device in self._devices:
            selected = device["selected"]
            current = device["current"]
            if selected == (current or "none"):
                continue
            if selected != "none" and selected not in installs:
                installs.append(selected)
            if current and current != selected and current not in installs:
                if current not in removals:
                    removals.append(current)

        commands: list[tuple[str, list[str]]] = []
        for package in installs:
            commands.append(self._driver_command(package))
        for package in removals:
            commands.append(self._remove_command(package))

        if not commands:
            self._set_can_apply(False)
            self._set_status("Sin cambios.")
            return

        self._commands = commands
        self._command_index = 0
        self._process_output = ""
        self._cancelled = False
        self._apply_needs_reboot = True
        self._set_busy(True)
        self._set_progress(0)
        self._set_error("")
        self._set_status("Aplicando cambios con ubuntu-drivers...")
        self._start_next_command()

    def _start_next_command(self) -> None:
        if self._command_index >= len(self._commands):
            self._finish_apply()
            return
        description, argv = self._commands[self._command_index]
        self._set_status(description + "...")
        process = QProcess(self)
        self._process = process
        process.setProgram(argv[0])
        process.setArguments(argv[1:])
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("DEBIAN_FRONTEND", "noninteractive")
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(self._read_process_output)
        process.readyReadStandardError.connect(self._read_process_output)
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(self._on_process_error)
        process.start()

    def _read_process_output(self) -> None:
        if self._process is None:
            return
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", "replace")
        data += bytes(self._process.readAllStandardError()).decode("utf-8", "replace")
        if not data:
            return
        self._process_output = (self._process_output + data)[-4000:]
        lines = [line.strip() for line in data.splitlines() if line.strip()]
        if lines:
            self._set_status(lines[-1][:200])

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error != QProcess.ProcessError.FailedToStart or self._process is None:
            return
        self._process = None
        self._fail_apply("No se pudo iniciar pkexec. Verificá que el agente polkit esté activo.")

    def _on_process_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self._process is None:
            return
        self._process = None
        if self._cancelled:
            self._cancelled = False
            self._commands = []
            self._command_index = 0
            self._apply_needs_reboot = False
            self._set_busy(False)
            self._set_progress(0)
            self._set_status("Operación cancelada.")
            self._set_error("")
            self.refresh()
            return
        if exit_code != 0:
            detail = self._process_output.strip() or f"La orden terminó con código {exit_code}."
            self._fail_apply(detail)
            return
        self._command_index += 1
        self._start_next_command()

    def _fail_apply(self, message: str) -> None:
        self._commands = []
        self._command_index = 0
        self._cancelled = False
        self._apply_needs_reboot = False
        self._set_progress(0)
        self._set_busy(False)
        self._set_error(f"No se pudo completar la operación: {message}")
        self._set_status("La operación no se completó.")

    def _finish_apply(self) -> None:
        self._commands = []
        self._command_index = 0
        self._cancelled = False
        self._set_progress(100)
        self._set_busy(False)
        self._set_can_apply(False)
        self._set_status("Cambios aplicados.")
        self.applied.emit()
        needs_reboot = self._apply_needs_reboot or os.path.exists("/var/run/reboot-required")
        self._apply_needs_reboot = False
        self._set_reboot_required(needs_reboot)
        self.refresh()

    @pyqtSlot()
    def cancel(self) -> None:
        if self._process is not None:
            self._cancelled = True
            self._set_status("Cancelando...")
            self._process.kill()

    # ---- package cache --------------------------------------------------

    @pyqtSlot()
    def refreshCache(self) -> None:
        if self._busy:
            return
        self._process_output = ""
        self._cancelled = False
        self._set_busy(True)
        self._set_progress(0)
        self._set_error("")
        self._set_status("Actualizando índices de paquetes...")
        process = QProcess(self)
        self._process = process
        process.setProgram("/usr/bin/pkexec")
        process.setArguments(["/usr/bin/env", "DEBIAN_FRONTEND=noninteractive",
                              "/usr/bin/apt-get", "update"])
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("DEBIAN_FRONTEND", "noninteractive")
        process.setProcessEnvironment(environment)
        process.readyReadStandardOutput.connect(self._read_process_output)
        process.readyReadStandardError.connect(self._read_process_output)
        process.finished.connect(self._on_cache_finished)
        process.errorOccurred.connect(self._on_process_error)
        process.start()

    def _on_cache_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        if self._process is None:
            return
        self._process = None
        if self._cancelled:
            self._cancelled = False
            self._set_busy(False)
            self._set_progress(0)
            self._set_status("Actualización de índices cancelada.")
            return
        if exit_code != 0:
            detail = self._process_output.strip() or f"apt-get update terminó con código {exit_code}."
            self._fail_apply(detail)
            return
        self._set_busy(False)
        self._set_status("Índices actualizados.")
        self.refresh()

    # ---- session --------------------------------------------------------

    @pyqtSlot()
    def reboot(self) -> None:
        if subprocess.run(
            ["sh", "-c", "command -v qdbus6 >/dev/null 2>&1"], check=False
        ).returncode == 0:
            subprocess.Popen(
                [
                    "qdbus6",
                    "org.kde.Shutdown",
                    "/Shutdown",
                    "org.kde.Shutdown.logoutAndReboot",
                ]
            )
        else:
            subprocess.Popen(["systemctl", "reboot"])
