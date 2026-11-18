# SPDX-License-Identifier: GPL-3.0-or-later
"""Start the SupraLINUX driver manager."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QLocale, QTranslator, QUrl
from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtQml import QQmlApplicationEngine

from .backend import Backend
from . import __version__


def qml_path() -> Path:
    override = os.environ.get("SUPRALINUX_DRIVERS_QML")
    if override:
        return Path(override)
    installed = Path("/usr/share/supralinux/drivers/qml/Main.qml")
    if installed.is_file():
        return installed
    return Path(__file__).resolve().parents[4] / "share/supralinux/drivers/qml/Main.qml"


def translations_path() -> Path:
    installed = Path("/usr/share/supralinux/drivers/translations")
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[4] / "share/supralinux/drivers/translations"


def install_translator(app: QGuiApplication) -> QTranslator | None:
    translator = QTranslator(app)
    locale = QLocale.system().name()
    for candidate in (locale, locale.split("_", 1)[0]):
        if translator.load(f"supralinux-drivers_{candidate}", str(translations_path())):
            app.installTranslator(translator)
            return translator
    return None


def main() -> int:
    app = QGuiApplication(sys.argv)
    install_translator(app)
    app.setApplicationName("supralinux-drivers")
    app.setApplicationDisplayName(QCoreApplication.translate("Main", "Controladores"))
    app.setOrganizationName("SupraLINUX")
    app.setDesktopFileName("org.supralinux.drivers")
    app.setWindowIcon(QIcon.fromTheme("supralinux-drivers"))
    app.setApplicationVersion(__version__)

    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("appVersion", __version__)
    engine.load(QUrl.fromLocalFile(str(qml_path())))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
