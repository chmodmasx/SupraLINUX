// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls as Controls

Controls.RadioButton {
    id: row
    property var group: null
    property var device: ({})
    property var driverData: ({})

    Controls.ButtonGroup.group: group
    checked: device.selected === driverData.package
    text: {
        if (driverData.package === "none")
            return driverData.title || qsTr("No usar ningún driver");
        let label = driverData.package;
        if (driverData.recommended)
            label += "  · " + qsTr("Recomendado");
        if (driverData.installed)
            label += "  · " + qsTr("Instalado");
        if (driverData.free === false)
            label += "  · " + qsTr("Propietario");
        return label;
    }
    onClicked: backend.selectDriver(device.modalias, driverData.package)
}
