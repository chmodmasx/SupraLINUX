var panel = new Panel
panel.location = "bottom"
panel.height = 46
panel.floating = true
panel.opacity = "translucent"

var kickoff = panel.addWidget("org.kde.plasma.kickoff")
kickoff.currentConfigGroup = ["General"]
kickoff.writeConfig("icon", "supralinux-color")
kickoff.writeConfig("decoration", "supralinux-color")
kickoff.writeConfig("switchCategoryOnHover", true)

panel.addWidget("org.kde.plasma.pager")
panel.addWidget("org.kde.plasma.icontasks")
panel.addWidget("org.kde.plasma.marginsseparator")
panel.addWidget("org.kde.plasma.systemtray")
panel.addWidget("org.kde.plasma.digitalclock")
panel.addWidget("org.kde.plasma.showdesktop")

var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = 'org.kde.image';
}
