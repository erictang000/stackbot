from __future__ import division, print_function
from ScopeFoundry import BaseMicroscopeApp

from hardware_components.apd_counter_usb import APDCounterUSBHardwareComponent
from hardware_components.mcl_xyz_stage import MclXYZStage
from measurement_components.apd_confocal import APD_MCL_2DSlowScan
from measurement_components.apd_optimizer import APDOptimizerMeasurement

from hardware_components.winspec_remote_client import WinSpecRemoteClientHC
from winspec_remote_readout import WinSpecRemoteReadout
from winspec_remote_2Dscan import WinSpecMCL2DSlowScan

from hardware_components.power_wheel_arduino import PowerWheelArduinoComponent

#from hardware_components.thorlabs_powermeter import ThorlabsPM100D

class DFMicroscopeApp(BaseMicroscopeApp):

    name = 'DFMicroscopeApp'
    
    def setup(self):
        print("Adding Hardware Components")
        self.add_hardware_component(APDCounterUSBHardwareComponent(self))
        #self.add_hardware_component(DummyXYStage(self))
        self.add_hardware_component(MclXYZStage(self))
        self.add_hardware_component(WinSpecRemoteClientHC(self))
        #self.add_hardware_component(ThorlabsPM100D(self))

        self.add_hardware_component(PowerWheelArduinoComponent(self))
    
        print("Adding Measurement Components")
        self.add_measurement_component(APD_MCL_2DSlowScan(self))
        self.add_measurement_component(WinSpecRemoteReadout(self))
        self.add_measurement_component(WinSpecMCL2DSlowScan(self))
        self.add_measurement_component(APDOptimizerMeasurement(self))


        self.ui.show()
        self.ui.close()
        self.ui.show()

        #self.ui._raise()
        self.ui.activateWindow()
        
if __name__ == '__main__':
    import sys
    app = DFMicroscopeApp(sys.argv)
    sys.exit(app.exec_())