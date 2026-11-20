import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

import "Strings.js" as Strings

Kirigami.ApplicationWindow {
    id: root
    width: 940
    height: 700
    minimumWidth: 720
    minimumHeight: 520
    visible: true
    title: t.appTitle

    readonly property var t: Strings.get(Qt.locale().name)
    readonly property var stepOrder: ["verify", "backup", "restore", "cleanup", "done"]

    function stepState(key) {
        var current = stepOrder.indexOf(Backend.step);
        var index = stepOrder.indexOf(key);
        if (current < 0) {
            return "pending";
        }
        if (index < current) {
            return "done";
        }
        if (index === current) {
            return "current";
        }
        return "pending";
    }

    function selectedSnapshotText() {
        if (snapshotsView.currentIndex < 0 || snapshotsView.currentIndex >= Backend.snapshots.length) {
            return "";
        }
        var snapshot = Backend.snapshots[snapshotsView.currentIndex];
        return "\n\n" + snapshot.date + "\n" + snapshot.description;
    }

    onClosing: function(close) {
        if (Backend.busy) {
            close.accepted = false;
        }
    }

    Component.onCompleted: Backend.refreshDevices()

    Timer {
        interval: 1200
        running: Backend.recoveryMode
        repeat: false
        onTriggered: {
            root.raise();
            root.requestActivate();
        }
    }

    pageStack.initialPage: startPage

    Connections {
        target: Backend

        function onRestoreFinished(success) {
            while (root.pageStack.depth > 1) {
                root.pageStack.pop();
            }
            root.pageStack.push(success ? successPage : errorPage);
        }
    }

    Kirigami.ScrollablePage {
        id: startPage
        title: t.appTitle

        ColumnLayout {
            x: Kirigami.Units.largeSpacing
            y: Kirigami.Units.largeSpacing
            width: startPage.width - Kirigami.Units.largeSpacing * 2
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                Kirigami.Icon {
                    source: "edit-undo"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                    Layout.preferredHeight: Kirigami.Units.iconSizes.huge
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Heading {
                        level: 1
                        text: t.heading
                        Layout.fillWidth: true
                    }

                    Controls.Label {
                        text: t.subtitle
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        opacity: 0.8
                    }
                }
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                type: Kirigami.MessageType.Warning
                text: t.warning
                visible: true
            }

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                type: Kirigami.MessageType.Error
                text: Backend.error
                visible: Backend.error.length > 0
            }

            RowLayout {
                Layout.fillWidth: true
                visible: Backend.devices.length > 1
                spacing: Kirigami.Units.largeSpacing

                Controls.Label {
                    text: t.device + ":"
                }

                Controls.ComboBox {
                    id: deviceCombo
                    Layout.fillWidth: true
                    model: Backend.devices
                    textRole: "label"
                    enabled: !Backend.busy
                    currentIndex: Backend.devices.length > 0 ? 0 : -1
                    onActivated: Backend.selectDevice(Backend.devices[currentIndex].device)
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                visible: Backend.devices.length === 1
                text: t.device + ": " + (Backend.devices.length > 0 ? Backend.devices[0].label : "")
                opacity: 0.8
            }

            Controls.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: Backend.busy
                visible: Backend.busy
            }

            Controls.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: t.loading
                visible: Backend.busy
                opacity: 0.8
            }

            Controls.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: Backend.devices.length === 0 ? t.noDevice : t.noSnapshots
                visible: !Backend.busy && Backend.snapshots.length === 0
                opacity: 0.8
            }

            ListView {
                id: snapshotsView
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, Kirigami.Units.gridUnit * 6),
                                                 Kirigami.Units.gridUnit * 18)
                visible: Backend.snapshots.length > 0
                clip: true
                model: Backend.snapshots
                currentIndex: -1
                spacing: Kirigami.Units.smallSpacing

                delegate: Controls.ItemDelegate {
                    width: ListView.view.width
                    highlighted: ListView.isCurrentItem
                    onClicked: snapshotsView.currentIndex = index

                    Accessible.name: modelData.date + ", " + modelData.description
                    Accessible.description: t.snapshotNumber + " " + modelData.num

                    contentItem: RowLayout {
                        spacing: Kirigami.Units.largeSpacing

                        Kirigami.Icon {
                            source: "document-save"
                            Layout.preferredWidth: Kirigami.Units.iconSizes.medium
                            Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            RowLayout {
                                Layout.fillWidth: true

                                Controls.Label {
                                    text: modelData.date
                                    font.bold: true
                                    Layout.fillWidth: true
                                }

                                Controls.Label {
                                    text: index === Backend.snapshots.length - 1 ? t.latest : ""
                                    visible: text.length > 0
                                    opacity: 0.7
                                }
                            }

                            Controls.Label {
                                text: modelData.description
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }

                            Controls.Label {
                                text: t.snapshotNumber + " " + modelData.num + " · " + modelData.type
                                opacity: 0.6
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.largeSpacing

                Item { Layout.fillWidth: true }

                Controls.Button {
                    text: t.refresh
                    icon.name: "view-refresh"
                    enabled: !Backend.busy
                    onClicked: Backend.refreshDevices()
                }

                Controls.Button {
                    text: t.close
                    onClicked: Qt.quit()
                }

                Controls.Button {
                    text: t.restore
                    icon.name: "edit-undo"
                    enabled: snapshotsView.currentIndex >= 0 && !Backend.busy
                    onClicked: confirmDialog.open()
                }
            }
        }
    }

    Kirigami.Page {
        id: progressPage
        title: t.progressTitle
        visible: false

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Heading {
                level: 1
                text: t.progressHeading
            }

            Rectangle {
                Layout.fillWidth: true
                height: Kirigami.Units.gridUnit * 0.6
                radius: height / 2
                color: Kirigami.Theme.alternateBackgroundColor

                Rectangle {
                    width: parent.width * Backend.progress
                    height: parent.height
                    radius: parent.radius
                    color: Kirigami.Theme.highlightColor
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                Repeater {
                    model: [
                        { key: "verify", label: t.stepVerify },
                        { key: "backup", label: t.stepBackup },
                        { key: "restore", label: t.stepRestore },
                        { key: "cleanup", label: t.stepCleanup }
                    ]

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.largeSpacing

                        Kirigami.Icon {
                            Layout.preferredWidth: Kirigami.Units.iconSizes.small
                            Layout.preferredHeight: Kirigami.Units.iconSizes.small
                            source: root.stepState(modelData.key) === "done" ? "dialog-ok" :
                                    root.stepState(modelData.key) === "current" ? "arrow-right" :
                                    "media-record"
                            opacity: root.stepState(modelData.key) === "pending" ? 0.4 : 1.0
                        }

                        Controls.Label {
                            Layout.fillWidth: true
                            text: modelData.label
                            opacity: root.stepState(modelData.key) === "pending" ? 0.5 : 1.0
                        }
                    }
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: t.doNotClose
                opacity: 0.7
            }

            Item { Layout.fillHeight: true }
        }
    }

    Kirigami.Page {
        id: successPage
        title: t.successTitle
        visible: false

        ColumnLayout {
            anchors.centerIn: parent
            width: Math.min(parent.width - Kirigami.Units.largeSpacing * 4,
                            Kirigami.Units.gridUnit * 30)
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Icon {
                Layout.alignment: Qt.AlignHCenter
                source: "dialog-ok"
                Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                Layout.preferredHeight: Kirigami.Units.iconSizes.huge
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                level: 1
                text: t.successTitle
            }

            Controls.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: t.successText
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Kirigami.Units.largeSpacing

                Controls.Button {
                    text: t.reboot
                    icon.name: "system-reboot"
                    onClicked: Backend.reboot()
                }

                Controls.Button {
                    text: t.close
                    onClicked: Qt.quit()
                }
            }
        }
    }

    Kirigami.Page {
        id: errorPage
        title: t.errorTitle
        visible: false

        ColumnLayout {
            anchors.centerIn: parent
            width: Math.min(parent.width - Kirigami.Units.largeSpacing * 4,
                            Kirigami.Units.gridUnit * 30)
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Icon {
                Layout.alignment: Qt.AlignHCenter
                source: "dialog-error"
                Layout.preferredWidth: Kirigami.Units.iconSizes.huge
                Layout.preferredHeight: Kirigami.Units.iconSizes.huge
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                level: 1
                text: t.errorTitle
            }

            Controls.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: Backend.error.length > 0 ? Backend.error : t.errorGeneric
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Kirigami.Units.largeSpacing

                Controls.Button {
                    text: t.details
                    onClicked: detailsDialog.open()
                }

                Controls.Button {
                    text: t.retry
                    onClicked: {
                        while (root.pageStack.depth > 1) {
                            root.pageStack.pop();
                        }
                        Backend.clearError();
                        Backend.refreshDevices();
                    }
                }

                Controls.Button {
                    text: t.close
                    onClicked: Qt.quit()
                }
            }
        }
    }

    Controls.Dialog {
        id: confirmDialog
        title: t.confirmTitle
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        width: Math.min(root.width - Kirigami.Units.largeSpacing * 4,
                        Kirigami.Units.gridUnit * 28)
        standardButtons: Controls.Dialog.Ok | Controls.Dialog.Cancel

        Controls.Label {
            width: parent.width
            wrapMode: Text.WordWrap
            text: t.confirmText + root.selectedSnapshotText()
        }

        onAccepted: {
            var index = snapshotsView.currentIndex;
            if (index < 0) {
                return;
            }
            root.pageStack.push(progressPage);
            Backend.restore(index);
        }
    }

    Controls.Dialog {
        id: detailsDialog
        title: t.details
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2
        width: Math.min(root.width - Kirigami.Units.largeSpacing * 4,
                        Kirigami.Units.gridUnit * 44)
        height: Math.min(root.height - Kirigami.Units.largeSpacing * 4,
                         Kirigami.Units.gridUnit * 28)
        standardButtons: Controls.Dialog.Close

        Flickable {
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: logLabel.implicitHeight

            Controls.Label {
                id: logLabel
                width: parent.width
                text: Backend.log
                wrapMode: Text.WrapAnywhere
                textFormat: Text.PlainText
            }
        }
    }
}
