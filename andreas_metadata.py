from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication, QDialog, QGridLayout, \
    QLabel, QLineEdit, QPushButton, QComboBox
from PyQt5.QtGui import QIntValidator
import param
from param.parameterized import classlist

from os import getcwd
import json
from time import strftime
from glob import glob
import re

app = QApplication([])


class Metadata (QDialog):
    """
        Metadata class for saving relevant metadata for lightsheet experiments
    """
    meta = {
        'Imaging':
        {
            'Framerate [fps]': int,
            'Piezo frequency': int,
            'Readout mode': ['Continuous', 'Lightsheet'],
            'Binning': ['1x1', '2x2', '4x4'],
            'Trigger': ['Internal', 'External'],
            'Exposure time [ms]': int,
            'Laser power [mA]': int,
        },
        'Behavior':
        {
            'Program': str,
            'Fish age': ["{} dpf".format(i) for i in range(5,9)],
            'Genotype': ['Huc:GCaMP6f','Huc:GCaMP6s','Huc:H2B-GCaMP6s',
                         'Fyn-tagRFP:PC:NLS-6f','Fyn-tagRFP:PC:NLS-6s','Fyn-tagRFP:PC:GCaMP5G'],
            'Comment': str,
            'Scanning profile': ['none','sawtooth','triangle']
        },
    }

    def __init__ (self, cwd = None, filename = None):
        """
            Constructor.

            If filename is None, the file will be named as follows:
               YEARMONTHDAY_HOURSMINUTESSECONDS_behavior+imaging.meta

            The data is saved in pretty formatted JSON.
        """
        super(Metadata,self).__init__()

        self.cwd = cwd if cwd else getcwd()
        self.filename = filename

        self.meta_val = self.meta.copy()
        

        files = sorted(glob(self.cwd+"\\**\\*.meta"))#,key=self.metasort)

        self._load_default = True

        try:
            with open(files[-1]) as fp:
                self.default = json.load(fp)

                print("Last meta file used as default: \n", files[-1], "\n")

        except:
            self._load_default = False

        self.initUI()

    def initUI (self):
        self.setWindowTitle("Select Metadata")

        self.l = QGridLayout()

        self.setLayout(self.l)

        column = 0

        for k, v in sorted(self.meta.items()):
            if type(v) == dict:
                l = QLabel(k.upper())
                self.l.addWidget(l, 0, column)

                self.addBoxes(v, column, k)

            column += 1

        ok = QPushButton("Save Metadata")
        ok.clicked.connect(self.close)
        okl = self.l.addWidget(ok, self.l.rowCount(), 0, 1,-1)

        self.show()

    def addBoxes(self, d, column, main_key):
        row = 1

        for k, v in sorted(d.items()):
            tbl = QLabel(k)
            self.l.addWidget(tbl,row,column)

            row += 1
            
            if v == str:                
                tb = QLineEdit(self.getDefault(main_key, k))                

            elif v == int:
                val = QIntValidator(50,100)
                tb = QLineEdit(self.getDefault(main_key, k))
                tb.setValidator(val)

            elif type(v) == list:
                tb = QComboBox()
                tb.addItems(v)
                tb.setCurrentIndex(tb.findText(self.getDefault(main_key,k)))

            else:
                tb = QLabel(v)
            
            self.meta_val[main_key][k] = tb
            self.l.addWidget(tb,row,column)

            row += 1

    def saveMeta (self):
        self.parseValues()
        with open((self.cwd+"\\"+str(strftime("%Y%m%d_%H%M%S_behavior+imaging")) if self.filename is None else self.filename)+".meta", "w") as f:
            json.dump(self.meta_val, f, indent=4)

        self.close()

    def parseValues (self):
        for k, v in self.meta_val.items():
            for kk, vv in v.items():
                try:
                    if type(vv) == QComboBox:
                        self.meta_val[k][kk] = str(vv.currentText())
                    else:
                        self.meta_val[k][kk] = vv.text()
                except:
                    print(k, kk)

        print(self.meta_val)

    def closeEvent (self, event):
        self.saveMeta()

    def getDefault (self, main_key, sub_key):
        try:
            return self.default[main_key][sub_key]

        except:
            return ""
            
    def metasort (self, x, pattern='lightsheet_f'):
        c = re.compile(pattern+"([0-9]+)")
        return int(c.findall(x)[0])

if __name__ == '__main__':
    m = Metadata()

    app.exec_()