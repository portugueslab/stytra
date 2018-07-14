from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton


class CollapseButton(QPushButton):
    def __init__(self, name, expanded=True):
        super().__init__()
        self.name = name
        self.expanded = expanded
        self.setStyleSheet(
            "text-align: left;" + "border: none;" + "padding-bottom: 5px;"
            "border-bottom: 1px solid palette(Light);"
        )
        self.setFlat(True)
        self.update_text()
        self.clicked.connect(self.toggle_name)

    def toggle_name(self):
        self.expanded = not self.expanded
        self.update_text()

    def update_text(self):
        if self.expanded:
            self.setText("▼ " + self.name)
        else:
            self.setText("▲ " + self.name)


class CollapsibleWidget(QWidget):
    def __init__(self, child: QWidget, name="", expanded=True):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.btnCollapse = CollapseButton(name, expanded=expanded)
        self.layout().addWidget(self.btnCollapse)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.child_widget = child
        self.normalMaximum = child.maximumHeight()
        self.layout().addWidget(self.child_widget)
        self.btnCollapse.clicked.connect(self.toggle_collapse)
        self.expanded = expanded
        self.collapse()

    def toggle_collapse(self):
        self.expanded = not self.expanded
        self.collapse()

    def collapse(self):
        if self.expanded:
            self.child_widget.setMaximumHeight(0)
        else:
            self.child_widget.setMaximumHeight(self.normalMaximum)
