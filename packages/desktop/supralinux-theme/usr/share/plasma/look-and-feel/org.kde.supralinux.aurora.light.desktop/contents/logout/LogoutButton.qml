/*
    SPDX-FileCopyrightText: 2016 Marco Martin <mart@kde.org>

    SPDX-License-Identifier: GPL-2.0-or-later
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

import org.kde.breeze.components
import "timer.js" as AutoTriggerTimer

ActionButton {
    id: logoutButton
    // otherwise the Button color group is used
    // and text legibility is broken with light themes
    // which set their own color scheme
    Kirigami.Theme.inherit: false
    Kirigami.Theme.colorSet: Kirigami.Theme.Complementary

    Layout.alignment: Qt.AlignTop

    icon.width: Kirigami.Units.iconSizes.huge
    icon.height: Kirigami.Units.iconSizes.huge

    font.underline: false // See https://phabricator.kde.org/D9452
    opacity: activeFocus || hovered ? 1 : 0.75


    contentItem: Column {
        spacing: logoutButton.spacing
        Kirigami.Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            source: logoutButton.icon.name
            color: "white"
            isMask: true
            implicitWidth: logoutButton.icon.width
            implicitHeight: logoutButton.icon.height
            active: logoutButton.hovered || logoutButton.activeFocus
        }
        PlasmaComponents3.Label {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(implicitWidth, parent.width)
            text: logoutButton.Kirigami.MnemonicData.richTextLabel
            color: "white"
            font: logoutButton.font
            style: logoutButton.softwareRendering ? Text.Outline : Text.Normal
            styleColor: Kirigami.Theme.backgroundColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignTop
            textFormat: Text.StyledText
            wrapMode: Text.WordWrap
        }
    }

    Keys.onPressed: {
        AutoTriggerTimer.cancelAutoTrigger();
    }
}
