// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Card {
    id: card
    property var device: ({})

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Icon {
                source: "computer"
                implicitWidth: Kirigami.Units.iconSizes.medium
                implicitHeight: Kirigami.Units.iconSizes.medium
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                Kirigami.Heading {
                    level: 3
                    text: {
                        const vendor = card.device.vendor || "";
                        const model = card.device.model || "";
                        return (vendor + " " + model).trim() || qsTr("Dispositivo");
                    }
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }

                Controls.Label {
                    text: card.device.modalias || ""
                    opacity: 0.6
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        Controls.Label {
            Layout.fillWidth: true
            text: card.device.status || ""
            wrapMode: Text.WordWrap
        }

        Controls.ButtonGroup {
            id: driverGroup
        }

        Column {
            Layout.fillWidth: true

            Repeater {
                model: card.device.drivers || []

                delegate: DriverRow {
                    width: parent.width
                    group: driverGroup
                    device: card.device
                    driverData: modelData
                }
            }

            DriverRow {
                width: parent.width
                group: driverGroup
                device: card.device
                driverData: ({
                    "package": "none",
                    "title": qsTr("No usar ningún driver"),
                    "installed": false,
                    "recommended": false,
                    "free": true
                })
            }
        }
    }
}
