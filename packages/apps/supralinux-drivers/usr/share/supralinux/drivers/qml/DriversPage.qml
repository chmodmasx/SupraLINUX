// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Controladores")

    actions: [
        Kirigami.Action {
            text: qsTr("Actualizar")
            icon.name: "view-refresh"
            enabled: !backend.busy
            onTriggered: backend.refresh()
        },
        Kirigami.Action {
            text: qsTr("Actualizar índices")
            icon.name: "update-none"
            enabled: !backend.busy
            onTriggered: backend.refreshCache()
        },
        Kirigami.Action {
            text: qsTr("Aplicar")
            icon.name: "dialog-ok-apply"
            enabled: backend.canApply && !backend.busy
            onTriggered: backend.apply()
        },
        Kirigami.Action {
            text: qsTr("Descartar")
            icon.name: "edit-undo"
            enabled: backend.canApply && !backend.busy
            onTriggered: backend.revert()
        },
        Kirigami.Action {
            text: qsTr("Cancelar")
            icon.name: "process-stop"
            visible: backend.busy
            onTriggered: backend.cancel()
        },
        Kirigami.Action {
            text: qsTr("Acerca de")
            icon.name: "help-about"
            onTriggered: aboutSheet.open()
        }
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: backend.error.length > 0
            type: Kirigami.MessageType.Error
            text: backend.error
            showCloseButton: true
            onVisibleChanged: {
                if (!visible)
                    backend.clearError();
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: backend.proprietaryInUse
            type: Kirigami.MessageType.Warning
            text: backend.rebootRequired
                ? qsTr("Hay drivers propietarios en uso. Para que surtan efecto, reiniciar el equipo.")
                : qsTr("Hay drivers propietarios en uso.")
            actions: [
                Kirigami.Action {
                    text: qsTr("Reiniciar")
                    icon.name: "system-reboot"
                    visible: backend.rebootRequired
                    onTriggered: backend.reboot()
                }
            ]
        }

        Controls.ProgressBar {
            Layout.fillWidth: true
            visible: backend.busy
            from: 0
            to: 100
            value: backend.progress
            indeterminate: backend.progress <= 0
        }

        Controls.Label {
            Layout.fillWidth: true
            visible: backend.busy || backend.status.length > 0
            text: backend.status
            opacity: 0.8
            wrapMode: Text.WordWrap
        }

        Column {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            Repeater {
                model: backend.devices
                delegate: DeviceCard {
                    width: parent.width
                    device: modelData
                }
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: backend.devices.length === 0 && !backend.busy
            type: Kirigami.MessageType.Information
            text: qsTr("No se encontraron dispositivos que necesiten drivers. Si acabás de instalar el sistema, actualizá los índices de paquetes.")
        }

        Controls.Button {
            Layout.alignment: Qt.AlignHCenter
            visible: backend.devices.length === 0 && !backend.busy
            text: qsTr("Actualizar índices de paquetes")
            icon.name: "update-none"
            onClicked: backend.refreshCache()
        }

        Item {
            Layout.fillHeight: true
        }
    }

    AboutSheet {
        id: aboutSheet
    }
}
