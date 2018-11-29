from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtGui import QPalette, QIcon
import pkg_resources


class IconButton(QToolButton):
    def __init__(self, *args, icon_name="", action_name="", **kwargs):
        super().__init__(*args, **kwargs)
        self.icon = QIcon(pkg_resources.resource_filename(__name__,
                                                                   "../icons/"+icon_name+".svg"))
        self.setIcon(self.icon)
        self.setToolTip(action_name)
        self.setFixedSize(QSize(48, 48))
        self.setIconSize(QSize(32,32))

class ToggleIconButton(QToolButton):
    def __init__(self, *args, icon_on="", icon_off=None, action_on="", action_off="", on=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon_on = QIcon(pkg_resources.resource_filename(__name__,
                                                                   "../icons/" + icon_on+".svg"))
        if icon_off is not None:
            self.icon_off = QIcon(pkg_resources.resource_filename(__name__,
                                                             "../icons/" + icon_off + ".svg"))
        else:
            self.icon_off = self.icon_on

        self.setCheckable(True)
        self.setChecked(on)
        self.setIcon(self.icon_on if on else self.icon_off)
        self.on = on
        self.setToolTip(action_on)
        self.setFixedSize(QSize(48, 48))
        self.setIconSize(QSize(32, 32))
        self.toggled.connect(self.flip_icon)

    def flip_icon(self, tg):
        if not tg:
            self.setIcon(self.icon_off)
            self.on = False
        else:
            self.setIcon(self.icon_on)
            self.on = True

