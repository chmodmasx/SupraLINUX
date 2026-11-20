#include "backend.h"

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QProcess>
#include <QStandardPaths>
#include <QTimer>

#include <functional>

namespace {
constexpr const char *kDefaultHelper = "/usr/libexec/supralinux-recovery-helper";
constexpr int kMaxLogCharacters = 16000;

QString cleanProcessError(const QString &error)
{
    const QString trimmed = error.trimmed();
    return trimmed.isEmpty() ? QStringLiteral("El ayudante de recuperación no devolvió detalles.")
                             : trimmed;
}
}

Backend::Backend(bool demo, QObject *parent)
    : QObject(parent)
    , m_demo(demo)
{
    QFile cmdline(QStringLiteral("/proc/cmdline"));
    if (cmdline.open(QIODevice::ReadOnly)) {
        m_recoveryMode = QString::fromUtf8(cmdline.readAll()).contains(QStringLiteral("supralinux.recovery=1"));
    }

    if (m_demo) {
        m_devices = {
            QVariantMap{{QStringLiteral("device"), QStringLiteral("/dev/demo0")},
                        {QStringLiteral("label"), QStringLiteral("Disco de demostración (40 GB)")},
                        {QStringLiteral("size"), QStringLiteral("40G")},
                        {QStringLiteral("model"), QStringLiteral("Demo")}},
        };
        m_currentDevice = QStringLiteral("/dev/demo0");
        m_snapshots = {
            QVariantMap{{QStringLiteral("num"), 1},
                        {QStringLiteral("date"), QStringLiteral("2026-11-20 06:35:44")},
                        {QStringLiteral("description"), QStringLiteral("Instalación inicial")},
                        {QStringLiteral("type"), QStringLiteral("single")},
                        {QStringLiteral("label"), QStringLiteral("2026-11-20 06:35:44 — Instalación inicial")}},
            QVariantMap{{QStringLiteral("num"), 2},
                        {QStringLiteral("date"), QStringLiteral("2026-11-20 06:39:27")},
                        {QStringLiteral("description"), QStringLiteral("APT pre")},
                        {QStringLiteral("type"), QStringLiteral("single")},
                        {QStringLiteral("label"), QStringLiteral("2026-11-20 06:39:27 — APT pre")}},
        };
        emit devicesChanged();
        emit snapshotsChanged();
        emit currentDeviceChanged();
    }
}

QVariantList Backend::devices() const
{
    return m_devices;
}

QVariantList Backend::snapshots() const
{
    return m_snapshots;
}

QString Backend::currentDevice() const
{
    return m_currentDevice;
}

bool Backend::busy() const
{
    return m_busy;
}

double Backend::progress() const
{
    return m_progress;
}

QString Backend::step() const
{
    return m_step;
}

QString Backend::error() const
{
    return m_error;
}

QString Backend::log() const
{
    return m_log;
}

bool Backend::recoveryMode() const
{
    return m_recoveryMode;
}

bool Backend::demo() const
{
    return m_demo;
}

void Backend::refreshDevices()
{
    if (m_busy) {
        return;
    }

    if (m_demo) {
        if (m_currentDevice.isEmpty() && !m_devices.isEmpty()) {
            setCurrentDevice(m_devices.first().toMap().value(QStringLiteral("device")).toString());
        }
        emit devicesChanged();
        emit snapshotsChanged();
        return;
    }

    setError(QString());
    setSnapshots({});
    setBusy(true);

    QString lsblk = QStandardPaths::findExecutable(QStringLiteral("lsblk"));
    if (lsblk.isEmpty()) {
        lsblk = QStringLiteral("lsblk");
    }

    auto *process = new QProcess(this);
    m_process = process;
    m_restoreMode = false;
    m_stdoutBuffer.clear();

    connect(process, &QProcess::readyReadStandardOutput, this, [this, process]() {
        m_stdoutBuffer += QString::fromUtf8(process->readAllStandardOutput());
    });

    connect(process, &QProcess::errorOccurred, this, [this, process](QProcess::ProcessError processError) {
        if (processError != QProcess::FailedToStart) {
            return;
        }
        if (m_process == process) {
            m_process = nullptr;
        }
        process->deleteLater();
        setBusy(false);
        setError(QStringLiteral("No se pudo iniciar lsblk para buscar discos Btrfs."));
    });

    connect(process, &QProcess::finished, this,
            [this, process](int exitCode, QProcess::ExitStatus exitStatus) {
                if (m_process == process) {
                    m_process = nullptr;
                }
                const QString standardError = QString::fromUtf8(process->readAllStandardError());
                process->deleteLater();
                setBusy(false);

                if (exitStatus != QProcess::NormalExit || exitCode != 0) {
                    setError(cleanProcessError(standardError));
                    return;
                }

                QJsonParseError parseError;
                const QJsonDocument document = QJsonDocument::fromJson(m_stdoutBuffer.toUtf8(), &parseError);
                m_stdoutBuffer.clear();
                if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
                    setError(QStringLiteral("No se pudo interpretar la lista de discos."));
                    return;
                }

                QVariantList found;
                std::function<void(const QJsonArray &)> visit = [&found, &visit](const QJsonArray &nodes) {
                    for (const QJsonValue &value : nodes) {
                        const QJsonObject node = value.toObject();
                        const QString name = node.value(QStringLiteral("name")).toString();
                        const QString fstype = node.value(QStringLiteral("fstype")).toString();
                        if (fstype == QStringLiteral("btrfs") && !name.isEmpty()) {
                            const QString label = node.value(QStringLiteral("label")).toString();
                            const QString model = node.value(QStringLiteral("model")).toString();
                            const QString size = node.value(QStringLiteral("size")).toString();
                            QString text = label;
                            if (text.isEmpty()) {
                                text = model.isEmpty() ? QStringLiteral("Disco Btrfs") : model;
                            }
                            if (!size.isEmpty()) {
                                text += QStringLiteral(" (%1)").arg(size);
                            }
                            found.append(QVariantMap{
                                {QStringLiteral("device"), QStringLiteral("/dev/") + name},
                                {QStringLiteral("label"), text},
                                {QStringLiteral("size"), size},
                                {QStringLiteral("model"), model},
                            });
                        }
                        if (node.value(QStringLiteral("children")).isArray()) {
                            visit(node.value(QStringLiteral("children")).toArray());
                        }
                    }
                };
                visit(document.object().value(QStringLiteral("blockdevices")).toArray());

                if (found.isEmpty()) {
                    setDevices({});
                    setCurrentDevice(QString());
                    setSnapshots({});
                    setError(QStringLiteral("No se encontró un sistema de archivos Btrfs."));
                    return;
                }

                setDevices(found);
                QString nextDevice = m_currentDevice;
                bool currentStillExists = false;
                for (const QVariant &entry : found) {
                    if (entry.toMap().value(QStringLiteral("device")).toString() == nextDevice) {
                        currentStillExists = true;
                        break;
                    }
                }
                if (!currentStillExists) {
                    nextDevice = found.first().toMap().value(QStringLiteral("device")).toString();
                }
                setCurrentDevice(nextDevice);
                runList(nextDevice);
            });

    process->start(lsblk, {QStringLiteral("-J"), QStringLiteral("-o"),
                           QStringLiteral("NAME,FSTYPE,SIZE,LABEL,MODEL,TYPE")});
}

void Backend::selectDevice(const QString &device)
{
    if (m_busy || device.isEmpty()) {
        return;
    }

    if (device == m_currentDevice && !m_snapshots.isEmpty()) {
        return;
    }

    setCurrentDevice(device);
    setSnapshots({});
    setError(QString());

    if (m_demo) {
        emit snapshotsChanged();
        return;
    }

    runList(device);
}

void Backend::runList(const QString &device)
{
    if (m_demo) {
        emit snapshotsChanged();
        return;
    }

    setBusy(true);
    setError(QString());
    startHelper({QStringLiteral("--list-tsv"), QStringLiteral("--device"), device}, false);
}

void Backend::parseListOutput(const QString &output)
{
    QVariantList found;
    const QStringList lines = output.split(QLatin1Char('\n'), Qt::SkipEmptyParts);
    for (const QString &line : lines) {
        const QStringList fields = line.split(QLatin1Char('\t'));
        if (fields.size() < 4) {
            continue;
        }
        bool ok = false;
        const int number = fields.at(0).toInt(&ok);
        if (!ok) {
            continue;
        }
        const QString date = fields.at(1);
        const QString description = fields.at(2);
        const QString type = fields.at(3);
        found.append(QVariantMap{
            {QStringLiteral("num"), number},
            {QStringLiteral("date"), date},
            {QStringLiteral("description"), description},
            {QStringLiteral("type"), type},
            {QStringLiteral("label"), date + QStringLiteral(" — ") + description},
        });
    }
    setSnapshots(found);
}

void Backend::restore(int index)
{
    if (m_busy) {
        return;
    }
    if (index < 0 || index >= m_snapshots.size()) {
        setError(QStringLiteral("Elegí una instantánea antes de restaurar."));
        return;
    }
    if (m_currentDevice.isEmpty()) {
        setError(QStringLiteral("No hay un disco Btrfs seleccionado."));
        return;
    }

    const QVariantMap snapshot = m_snapshots.at(index).toMap();
    m_pendingSnapshot = snapshot.value(QStringLiteral("num")).toInt();
    m_sawDone = false;
    setError(QString());
    setProgress(0.0);
    setStep(QStringLiteral("verify"));
    m_log.clear();
    emit logChanged();
    setBusy(true);

    if (m_demo) {
        startDemoRestore();
        return;
    }

    startHelper({QStringLiteral("--device"), m_currentDevice,
                 QStringLiteral("--snapshot"), QString::number(m_pendingSnapshot),
                 QStringLiteral("--yes"), QStringLiteral("--progress=json")},
                true);
}

void Backend::parseProgressLine(const QString &line)
{
    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(line.toUtf8(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        appendLog(line);
        return;
    }

    const QJsonObject event = document.object();
    const QString type = event.value(QStringLiteral("event")).toString();

    if (type == QStringLiteral("step")) {
        const QString stepName = event.value(QStringLiteral("step")).toString();
        const QString status = event.value(QStringLiteral("status")).toString();
        setStep(stepName);

        double value = m_progress;
        if (stepName == QStringLiteral("verify")) {
            value = status == QStringLiteral("ok") ? 0.15 : 0.05;
        } else if (stepName == QStringLiteral("backup")) {
            value = status == QStringLiteral("ok") ? 0.45 : 0.25;
        } else if (stepName == QStringLiteral("restore")) {
            value = status == QStringLiteral("ok") ? 0.85 : 0.55;
        } else if (stepName == QStringLiteral("cleanup")) {
            value = status == QStringLiteral("ok") ? 0.98 : 0.90;
        } else if (stepName == QStringLiteral("done")) {
            value = 1.0;
        }
        setProgress(value);
    } else if (type == QStringLiteral("done")) {
        m_sawDone = true;
        setStep(QStringLiteral("done"));
        setProgress(1.0);
    } else if (type == QStringLiteral("error")) {
        setError(event.value(QStringLiteral("message")).toString());
    } else {
        appendLog(line);
    }
}

void Backend::startHelper(const QStringList &arguments, bool restoreMode)
{
    m_restoreMode = restoreMode;
    m_stdoutBuffer.clear();
    m_sawDone = false;

    QStringList command = helperArguments(arguments);
    if (command.isEmpty()) {
        setBusy(false);
        finishRestore(false, QStringLiteral("No se pudo preparar el ayudante de recuperación."));
        return;
    }

    auto *process = new QProcess(this);
    m_process = process;
    const QString program = command.takeFirst();

    connect(process, &QProcess::readyReadStandardOutput, this, [this, process]() {
        m_stdoutBuffer += QString::fromUtf8(process->readAllStandardOutput());
        if (!m_restoreMode) {
            return;
        }
        int newline = -1;
        while ((newline = m_stdoutBuffer.indexOf(QLatin1Char('\n'))) >= 0) {
            const QString line = m_stdoutBuffer.left(newline).trimmed();
            m_stdoutBuffer.remove(0, newline + 1);
            if (!line.isEmpty()) {
                parseProgressLine(line);
            }
        }
    });

    connect(process, &QProcess::readyReadStandardError, this, [this, process]() {
        appendLog(QString::fromUtf8(process->readAllStandardError()));
    });

    connect(process, &QProcess::errorOccurred, this, [this, process](QProcess::ProcessError processError) {
        if (processError != QProcess::FailedToStart) {
            return;
        }
        if (m_process == process) {
            m_process = nullptr;
        }
        process->deleteLater();
        setBusy(false);
        if (m_restoreMode) {
            m_restoreMode = false;
            finishRestore(false, QStringLiteral("No se pudo iniciar el ayudante de recuperación."));
        } else {
            setError(QStringLiteral("No se pudo iniciar el ayudante de recuperación."));
        }
    });

    connect(process, &QProcess::finished, this,
            [this, process](int exitCode, QProcess::ExitStatus exitStatus) {
                if (m_process == process) {
                    m_process = nullptr;
                }
                const QString standardError = QString::fromUtf8(process->readAllStandardError());
                process->deleteLater();
                setBusy(false);

                if (m_restoreMode) {
                    const QString remainder = m_stdoutBuffer.trimmed();
                    m_stdoutBuffer.clear();
                    if (!remainder.isEmpty()) {
                        parseProgressLine(remainder);
                    }
                    m_restoreMode = false;
                    if (exitStatus != QProcess::NormalExit || exitCode != 0 || !m_sawDone) {
                        finishRestore(false, cleanProcessError(standardError));
                    } else {
                        finishRestore(true);
                    }
                    return;
                }

                if (exitStatus != QProcess::NormalExit || exitCode != 0) {
                    setError(cleanProcessError(standardError));
                    return;
                }
                parseListOutput(m_stdoutBuffer);
                m_stdoutBuffer.clear();
            });

    process->start(program, command);
}

QString Backend::helperPath() const
{
    return qEnvironmentVariable("SUPRALINUX_RECOVERY_HELPER", QString::fromLatin1(kDefaultHelper));
}

QString Backend::pkexecPath() const
{
    const QString path = QStandardPaths::findExecutable(QStringLiteral("pkexec"));
    return path.isEmpty() ? QStringLiteral("/usr/bin/pkexec") : path;
}

QStringList Backend::helperArguments(const QStringList &arguments) const
{
    const QString devHelper = qEnvironmentVariable("SUPRALINUX_RECOVERY_DEV_HELPER");
    if (!devHelper.isEmpty()) {
        QStringList command{devHelper};
        command.append(arguments);
        return command;
    }

    QStringList command{pkexecPath(), helperPath()};
    command.append(arguments);
    return command;
}

void Backend::startDemoRestore()
{
    QTimer::singleShot(200, this, [this]() {
        setStep(QStringLiteral("verify"));
        setProgress(0.08);
    });
    QTimer::singleShot(600, this, [this]() {
        setStep(QStringLiteral("backup"));
        setProgress(0.30);
    });
    QTimer::singleShot(1100, this, [this]() {
        setStep(QStringLiteral("restore"));
        setProgress(0.65);
    });
    QTimer::singleShot(1600, this, [this]() {
        setStep(QStringLiteral("cleanup"));
        setProgress(0.92);
    });
    QTimer::singleShot(2150, this, [this]() {
        setStep(QStringLiteral("done"));
        setProgress(1.0);
        setBusy(false);
        emit restoreFinished(true);
    });
}

void Backend::finishRestore(bool success, const QString &fallbackError)
{
    if (success) {
        setStep(QStringLiteral("done"));
        setProgress(1.0);
    } else if (m_error.isEmpty()) {
        setError(fallbackError.isEmpty() ? QStringLiteral("No se pudo completar la restauración.")
                                         : fallbackError);
    }
    setBusy(false);
    emit restoreFinished(success);
}

void Backend::reboot()
{
    if (m_demo) {
        return;
    }
    if (!QProcess::startDetached(QStringLiteral("systemctl"), {QStringLiteral("reboot")})) {
        setError(QStringLiteral("No se pudo reiniciar el equipo. Reiniciá manualmente."));
    }
}

void Backend::clearError()
{
    setError(QString());
    m_log.clear();
    emit logChanged();
}

void Backend::setDevices(const QVariantList &devices)
{
    if (m_devices == devices) {
        return;
    }
    m_devices = devices;
    emit devicesChanged();
}

void Backend::setSnapshots(const QVariantList &snapshots)
{
    if (m_snapshots == snapshots) {
        return;
    }
    m_snapshots = snapshots;
    emit snapshotsChanged();
}

void Backend::setCurrentDevice(const QString &device)
{
    if (m_currentDevice == device) {
        return;
    }
    m_currentDevice = device;
    emit currentDeviceChanged();
}

void Backend::setBusy(bool busy)
{
    if (m_busy == busy) {
        return;
    }
    m_busy = busy;
    emit busyChanged();
}

void Backend::setProgress(double progress)
{
    const double normalized = qBound(0.0, progress, 1.0);
    if (qFuzzyCompare(m_progress, normalized)) {
        return;
    }
    m_progress = normalized;
    emit progressChanged();
}

void Backend::setStep(const QString &step)
{
    if (m_step == step) {
        return;
    }
    m_step = step;
    emit stepChanged();
}

void Backend::setError(const QString &error)
{
    if (m_error == error) {
        return;
    }
    m_error = error;
    emit errorChanged();
}

void Backend::appendLog(const QString &text)
{
    if (text.isEmpty()) {
        return;
    }
    m_log += text;
    if (m_log.size() > kMaxLogCharacters) {
        m_log = m_log.right(kMaxLogCharacters);
    }
    emit logChanged();
}
