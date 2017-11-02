from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, \
    QLabel, QPushButton
from PyQt5.QtCore import Qt


class MetaListGui(QWidget):
    def __init__(self, metadata_list=None, *args, **kwargs):
        """ Constructor
        :param metadata_list: Metadata objects list
        """
        super().__init__(*args, **kwargs)

        self.layout = QGridLayout()
        self.metadata_list = metadata_list
        self.create_layout()

        self.setLayout(self.layout)

    def create_layout(self):
        # Clear layout from previous widgets:
        for i in reversed(range(self.layout.count())):
            widgetToRemove = self.layout.itemAt(i).widget()
            # remove it from the layout list
            self.layout.removeWidget(widgetToRemove)
            # remove it from the gui
            widgetToRemove.setParent(None)

        self.widget_list = []
        for j, metadata in enumerate(self.metadata_list):
            new_widg = metadata.get_gui(save_button=False)
            new_widg.layout.addStretch()

            name = type(metadata).__name__
            label = QLabel(name)
            label.setAlignment(Qt.AlignHCenter)
            label.setStyleSheet("font-weight: bold; text-align: center;")

            self.layout.addWidget(label, 0, j)
            self.layout.addWidget(new_widg, 1, j)

            self.widget_list.append(new_widg)

        ok_button = QPushButton("Save Metadata")
        ok_button.clicked.connect(self.save_all_meta)
        self.layout.addWidget(ok_button, 2, 0, 1, j+1)

    def show_gui(self):
        self.create_layout()
        self.show()

    def save_all_meta(self):
        check_list = []
        for paramqt_widget in self.widget_list:
            check = paramqt_widget.save_meta()
            check_list.append(check)

        if all(check_list):
            self.close()


if __name__ == '__main__':
    from stytra.metadata import MetadataLightsheet, MetadataFish

    app = QApplication([])
    lightsheetmeta = MetadataLightsheet()
    fishmeta = MetadataFish()
    lightsheetmeta.piezo_frequency = 8
    metadata_gui = MetaListGui([lightsheetmeta, fishmeta])

    metadata_gui.show()
    app.exec_()
