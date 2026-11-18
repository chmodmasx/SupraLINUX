// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.Dialog {
    id: sheet
    title: qsTr("Acerca de Controladores")
    modal: true
    width: Kirigami.Units.gridUnit * 28
    standardButtons: Controls.Dialog.Close

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        Controls.Label {
            text: "SupraLINUX - Aurora"
            font.bold: true
        }

        Controls.Label {
            text: qsTr("Gestor de controladores de hardware.")
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.Label {
            text: qsTr("Detección con UbuntuDrivers; instalación con ubuntu-drivers y desinstalación con apt, mediante pkexec.")
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.Label {
            text: qsTr("Versión %1").arg(appVersion)
            opacity: 0.7
        }

        Controls.Button {
            text: "https://supralinux.com/"
            flat: true
            onClicked: Qt.openUrlExternally("https://supralinux.com/")
        }
    }
}
