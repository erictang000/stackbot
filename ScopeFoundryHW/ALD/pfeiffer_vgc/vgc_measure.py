'''
Created on Nov 20, 2017

@author: Alan Buckley <alanbuckley@berkeley.edu>
                      <alanbuckley@lbl.gov>
'''

from ScopeFoundry import Measurement
from PyQt5 import QtWidgets
import time 

class VGC_Measure(Measurement):
    
    name = "vgc_measure"
    
    def __init__(self, app):
        Measurement.__init__(self, app)
        
    def setup(self):
        
        self.ui = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()
        self.ui.setLayout(self.layout)
#         self.ui.setWindowTitle("Vacuum System Control")
        
        self.vgc = self.app.hardware['vgc_hw']
    
    def run(self):
        while not self.interrupt_measurement_called:
            self.vgc.read_from_hardware()
            time.sleep(0.25)