#pragma once

#include <QObject>
#include <QProcess>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

class Backend : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList devices READ devices NOTIFY devicesChanged)
    Q_PROPERTY(QVariantList snapshots READ snapshots NOTIFY snapshotsChanged)
    Q_PROPERTY(QString currentDevice READ currentDevice NOTIFY currentDeviceChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(double progress READ progress NOTIFY progressChanged)
    Q_PROPERTY(QString step READ step NOTIFY stepChanged)
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)
    Q_PROPERTY(QString log READ log NOTIFY logChanged)
    Q_PROPERTY(bool recoveryMode READ recoveryMode CONSTANT)
    Q_PROPERTY(bool demo READ demo CONSTANT)

public:
    explicit Backend(bool demo = false, QObject *parent = nullptr);

    QVariantList devices() const;
    QVariantList snapshots() const;
    QString currentDevice() const;
    bool busy() const;
    double progress() const;
    QString step() const;
    QString error() const;
    QString log() const;
    bool recoveryMode() const;
    bool demo() const;

    Q_INVOKABLE void refreshDevices();
    Q_INVOKABLE void selectDevice(const QString &device);
    Q_INVOKABLE void restore(int index);
    Q_INVOKABLE void reboot();
    Q_INVOKABLE void clearError();

signals:
    void devicesChanged();
    void snapshotsChanged();
    void currentDeviceChanged();
    void busyChanged();
    void progressChanged();
    void stepChanged();
    void errorChanged();
    void logChanged();
    void restoreFinished(bool success);

private:
    void setDevices(const QVariantList &devices);
    void setSnapshots(const QVariantList &snapshots);
    void setCurrentDevice(const QString &device);
    void setBusy(bool busy);
    void setProgress(double progress);
    void setStep(const QString &step);
    void setError(const QString &error);
    void appendLog(const QString &text);
    void runList(const QString &device);
    void parseListOutput(const QString &output);
    void parseProgressLine(const QString &line);
    void finishRestore(bool success, const QString &fallbackError = QString());
    void startDemoRestore();
    QString helperPath() const;
    QString pkexecPath() const;
    QStringList helperArguments(const QStringList &arguments) const;
    void startHelper(const QStringList &arguments, bool restoreMode);

    QVariantList m_devices;
    QVariantList m_snapshots;
    QString m_currentDevice;
    bool m_busy = false;
    double m_progress = 0.0;
    QString m_step;
    QString m_error;
    QString m_log;
    bool m_recoveryMode = false;
    bool m_demo = false;
    bool m_restoreMode = false;
    bool m_sawDone = false;
    int m_pendingSnapshot = -1;
    QString m_stdoutBuffer;
    QProcess *m_process = nullptr;
};
