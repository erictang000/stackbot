#from ScopeFoundryHW.attocube_ecc100.attocube_slowscan import AttoCube2DSlowScan
from ScopeFoundryHW.thorlabs_stepper_motors import ThorlabsStepper2DScan
import numpy as np
import time


class FiberPowerMeterScan(ThorlabsStepper2DScan):
    
    name = 'fiber_powermeter_scan'
    
    def scan_specific_setup(self):
        self.pm = self.app.hardware['thorlabs_powermeter']  
        self.pm.read_from_hardware()
        #self.display_image_map = np.ones_like(self.display_image_map)
    
    def collect_pixel(self, pixel_num, k, j, i):
        print(self.name, "collect_pixel")
        
        avg_power = 0
        for ii in range(20):
            power = self.pm.settings.power.read_from_hardware()
            avg_power += power
        avg_power /= 20
        
        self.display_image_map[k,j,i] = avg_power
        
        
class FiberAPDScan(ThorlabsStepper2DScan):
    
    name = 'fiber_apd_scan'

    def pre_scan_setup(self):
        self.apd = self.app.hardware['apd_counter']


        self.count_rate_map = np.zeros(self.scan_shape,dtype=float)
        if self.settings['save_h5']:
            self.count_rate_map_h5 = self.h5_meas_group.create_dataset('count_rate_map', 
                                                                       shape=self.scan_shape,
                                                                       dtype=float, 
                                                                       compression='gzip')

        
        
    def collect_pixel(self, pixel_num, k, j, i):
        count_rate = self.apd.settings.count_rate.read_from_hardware()
        time.sleep(self.apd.settings['int_time'])
        
        self.display_image_map[k,j,i] = count_rate
        self.count_rate_map[k,j,i] = count_rate
        if self.settings['save_h5']:
            self.count_rate_map_h5[k,j,i] = count_rate


from confocal_measure import Picoharp_MCL_2DSlowScan
class FiberPicoharpScan(ThorlabsStepper2DScan):
    
    name = 'fiber_picoharp_scan'

    def pre_scan_setup(self):
        print("="*60)
        print(self.name, "pre_scan_setup")
        Picoharp_MCL_2DSlowScan.pre_scan_setup(self)

    def collect_pixel(self, pixel_num, k, j, i):
        print(self.name, "collect_pixel", pixel_num, k, j, i)
        Picoharp_MCL_2DSlowScan.collect_pixel(self, pixel_num, k, j, i)
        
    def post_scan_cleanup(self):
        Picoharp_MCL_2DSlowScan.post_scan_cleanup(self)
        
    def update_display(self):
        Picoharp_MCL_2DSlowScan.update_display(self)

from confocal_measure import WinSpecMCL2DSlowScan
class FiberWinSpecScan(ThorlabsStepper2DScan):
    
    name = 'fiber_winspec_scan'
    
    def pre_scan_setup(self):
        WinSpecMCL2DSlowScan.pre_scan_setup(self)
    
    def collect_pixel(self, pixel_num, k, j, i):
        print(self.name, "collect_pixel", pixel_num, k, j, i)
        WinSpecMCL2DSlowScan.collect_pixel(self, pixel_num, k, j, i)

    def post_scan_cleanup(self):
        WinSpecMCL2DSlowScan.post_scan_cleanup(self)
        
    def update_display(self):
        WinSpecMCL2DSlowScan.update_display(self)

    