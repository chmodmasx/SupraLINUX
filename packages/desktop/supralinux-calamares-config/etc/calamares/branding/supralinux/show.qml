import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    Timer {
        interval: 12000
        running: true
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    // Slide 1: product identity.
    Slide {
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#050b14" }
                GradientStop { position: 0.55; color: "#081a2e" }
                GradientStop { position: 1.0; color: "#0b2a4a" }
            }
        }
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 4
            color: "#51a2da"
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 3
            color: "#1d4d72"
        }

        Image {
            id: welcomeWordmark
            source: "wordmark.png"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: parent.height * 0.16
            width: parent.width * 0.56
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: welcomeWordmark.bottom
            anchors.topMargin: parent.height * 0.035
            text: "Aurora 1.0.0"
            color: "#7fd1ff"
            font.pixelSize: Math.round(presentation.height * 0.030)
            font.letterSpacing: 1.5
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: welcomeWordmark.bottom
            anchors.topMargin: parent.height * 0.095
            text: "Plasma 6.6.7 · Wayland"
            color: "#d7e3ef"
            font.pixelSize: Math.round(presentation.height * 0.022)
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: welcomeWordmark.bottom
            anchors.topMargin: parent.height * 0.18
            text: qsTr("Tu escritorio, listo para empezar")
            color: "#ffffff"
            font.pixelSize: Math.round(presentation.height * 0.034)
            font.bold: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: parent.height * 0.06
            text: "supralinux.com"
            color: "#7f9bb5"
            font.pixelSize: Math.round(presentation.height * 0.017)
        }
    }

    // Slide 2: base and stack.
    Slide {
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#050b14" }
                GradientStop { position: 0.55; color: "#081a2e" }
                GradientStop { position: 1.0; color: "#0b2a4a" }
            }
        }
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 4
            color: "#51a2da"
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 3
            color: "#1d4d72"
        }

        Image {
            id: stackLogo
            source: "logo.png"
            anchors.left: parent.left
            anchors.leftMargin: parent.width * 0.10
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(parent.width * 0.22, parent.height * 0.32)
            height: width
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }

        Column {
            anchors.left: stackLogo.right
            anchors.leftMargin: parent.width * 0.055
            anchors.right: parent.right
            anchors.rightMargin: parent.width * 0.08
            anchors.verticalCenter: parent.verticalCenter
            spacing: parent.height * 0.018

            Text {
                text: qsTr("BASE UBUNTU 26.04 LTS")
                color: "#7fd1ff"
                font.pixelSize: Math.round(presentation.height * 0.018)
                font.letterSpacing: 2
            }
            Text {
                text: "Plasma 6.6.7"
                color: "#ffffff"
                font.pixelSize: Math.round(presentation.height * 0.048)
                font.bold: true
            }
            Text {
                width: parent.width
                text: "Frameworks 6.24 · Gear 25.12.3 · Qt 6.10.2"
                color: "#d7e3ef"
                font.pixelSize: Math.round(presentation.height * 0.024)
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: qsTr("Wayland · Snapper · Descubrir aplicaciones")
                color: "#9fb3c8"
                font.pixelSize: Math.round(presentation.height * 0.020)
                wrapMode: Text.WordWrap
            }
        }
    }

    // Slide 3: welcome and tips.
    Slide {
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#050b14" }
                GradientStop { position: 0.55; color: "#081a2e" }
                GradientStop { position: 1.0; color: "#0b2a4a" }
            }
        }
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 4
            color: "#51a2da"
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 3
            color: "#1d4d72"
        }

        Image {
            id: thanksWordmark
            source: "wordmark.png"
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: parent.height * 0.13
            width: parent.width * 0.42
            fillMode: Image.PreserveAspectFit
            asynchronous: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: thanksWordmark.bottom
            anchors.topMargin: parent.height * 0.035
            text: qsTr("Gracias por elegir SupraLINUX")
            color: "#ffffff"
            font.pixelSize: Math.round(presentation.height * 0.038)
            font.bold: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: thanksWordmark.bottom
            anchors.topMargin: parent.height * 0.115
            width: parent.width * 0.72
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("Firefox, Discover y las herramientas de KDE ya están listas.")
            color: "#d7e3ef"
            font.pixelSize: Math.round(presentation.height * 0.022)
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: thanksWordmark.bottom
            anchors.topMargin: parent.height * 0.175
            width: parent.width * 0.72
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("Tus instantáneas Btrfs te permiten volver atrás cuando lo necesites.")
            color: "#9fb3c8"
            font.pixelSize: Math.round(presentation.height * 0.020)
            wrapMode: Text.WordWrap
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: parent.height * 0.06
            text: "SupraLINUX Aurora 1.0.0 · supralinux.com"
            color: "#7f9bb5"
            font.pixelSize: Math.round(presentation.height * 0.017)
        }
    }
}
