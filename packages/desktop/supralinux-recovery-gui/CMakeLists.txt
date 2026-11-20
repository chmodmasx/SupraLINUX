cmake_minimum_required(VERSION 3.16)

project(supralinux-recovery-gui VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2)

add_executable(supralinux-recovery-gui
    src/main.cpp
    src/backend.cpp
    src/backend.h
)

target_link_libraries(supralinux-recovery-gui PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Quick
    Qt6::QuickControls2
)

target_compile_definitions(supralinux-recovery-gui PRIVATE
    SUPRALINUX_QML_DIR="${CMAKE_INSTALL_PREFIX}/share/supralinux/recovery"
)

install(TARGETS supralinux-recovery-gui
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
