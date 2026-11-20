#include "backend.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QUrl>

#include <cstdio>

#ifndef SUPRALINUX_QML_DIR
#define SUPRALINUX_QML_DIR "/usr/share/supralinux/recovery"
#endif

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setOrganizationName(QStringLiteral("SupraLINUX"));
    QCoreApplication::setApplicationName(QStringLiteral("supralinux-recovery-gui"));
    QCoreApplication::setApplicationVersion(QStringLiteral("1.0.0"));
    QGuiApplication::setDesktopFileName(QStringLiteral("supralinux-recovery"));

    const bool demo = app.arguments().contains(QStringLiteral("--demo"));
    const bool autostart = app.arguments().contains(QStringLiteral("--autostart"));

    Backend backend(demo);
    if (autostart && !backend.recoveryMode()) {
        return 0;
    }

    QQuickStyle::setStyle(QStringLiteral("org.kde.breeze"));

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("Backend"), &backend);

    const QString qmlDirectory = qEnvironmentVariable(
        "SUPRALINUX_RECOVERY_QML", QStringLiteral(SUPRALINUX_QML_DIR));
    const QString qmlFile = qmlDirectory + QStringLiteral("/Main.qml");

    engine.load(QUrl::fromLocalFile(qmlFile));
    if (engine.rootObjects().isEmpty()) {
        std::fprintf(stderr, "No se pudo cargar %s\n", qPrintable(qmlFile));
        return 1;
    }

    return app.exec();
}
