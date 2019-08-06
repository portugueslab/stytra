from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtGui import QIcon
import pkg_resources


def get_icon(icon_name):
    return QIcon(
        pkg_resources.resource_filename(__name__, "../icons/" + icon_name + ".svg")
    )


class IconButton(QToolButton):
    def __init__(self, *args, icon_name="", action_name="", **kwargs):
        super().__init__(*args, **kwargs)
        self.icon = QIcon(
            pkg_resources.resource_filename(__name__, "../icons/" + icon_name + ".svg")
        )
        self.setIcon(self.icon)
        self.setToolTip(action_name)
        self.setFixedSize(QSize(48, 48))
        self.setIconSize(QSize(32, 32))


class ToggleIconButton(QToolButton):
    def __init__(
        self,
        *args,
        icon_on="",
        icon_off=None,
        action_on="",
        action_off=None,
        on=False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.icon_on = get_icon(icon_on)
        if icon_off is not None:
            self.icon_off = get_icon(icon_off)
        else:
            self.icon_off = self.icon_on

        self.setCheckable(True)
        self.setChecked(on)
        self.setIcon(self.icon_on if on else self.icon_off)
        self.on = on
        self.action_on = action_on
        self.action_off = action_off or action_on
        self.setToolTip(action_on)
        self.setFixedSize(QSize(48, 48))
        self.setIconSize(QSize(32, 32))
        self.clicked.connect(self.flip_icon)

    def flip_icon(self, tg):
        if not tg:
            self.setIcon(self.icon_off)
            self.on = False
            self.setChecked(False)
        else:
            self.setIcon(self.icon_on)
            self.on = True
            self.setChecked(True)
        self.setToolTip(self.action_on if self.on else self.action_off)
