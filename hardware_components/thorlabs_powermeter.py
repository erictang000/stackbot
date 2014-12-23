from . import HardwareComponent
try:
    from equipment.thorlabs_pm100d import ThorlabsPM100D
except Exception as err:
    print "Cannot load required modules for Thorlabs Power meter:", err

class ThorlabsPowerMeter(HardwareComponent):
    
    def setup(self):
        self.name = 'thorlabs_powermeter'
        
        # Created logged quantities
        self.wavelength = self.add_logged_quantity(
                                                     name = 'wavelength', 
                                                     unit = "nm",
                                                     dtype = int,
                                                     vmin=0,
                                                     vmax=2000, )
        
        self.power = self.add_logged_quantity(name = 'power', dtype=float, unit="W", vmin=-1, vmax = 10, ro=True)
        self.current = self.add_logged_quantity(name = 'current', dtype=float, unit="A", vmin=-1, vmax = 10, ro=True)
        
        
        self.power_range = self.add_logged_quantity(name = 'power_range', dtype=float, unit="W", vmin=0, vmax=1e3)
        
        self.auto_range = self.add_logged_quantity(name = 'auto_range', dtype=bool, ro=False)
        
        self.zero_state = self.add_logged_quantity(name = "zero_state", dtype=bool, ro=True)
        self.zero_magnitude = self.add_logged_quantity(name = "zero_magnitude", dtype=float, ro=True)
        
        self.photodiode_response = self.add_logged_quantity(name = "photodiode_response", dtype=float, unit="A/W")
        
        self.current_range = self.add_logged_quantity(name = "current_range", dtype=float, unit="A")
        
        # connect GUI
        self.wavelength.connect_bidir_to_widget(self.gui.ui.power_meter_wl_doubleSpinBox)
        self.power.connect_bidir_to_widget(self.gui.ui.power_meter_power_label)
        
        #operations
        self.add_operation("run_zero", self.run_zero)
        
    def connect(self):
        if self.debug_mode.val: print "connecting to", self.name
        
        # Open connection to hardware                        
        self.power_meter = ThorlabsPM100D(debug=self.debug_mode.val)
        
        #Connect lq
        self.wavelength.hardware_read_func = self.power_meter.get_wavelength
        self.wavelength.hardware_set_func  = self.power_meter.set_wavelength
        
        self.power.hardware_read_func = self.power_meter.measure_power
        
        self.current.hardware_read_func = self.power_meter.measure_current

        self.power_range.hardware_read_func = self.power_meter.get_power_range
        self.power_range.hardware_set_func  = self.power_meter.set_power_range

        self.auto_range.hardware_read_func = self.power_meter.get_auto_range
        self.auto_range.hardware_set_func = self.power_meter.set_auto_range

        self.zero_state.hardware_read_func = self.power_meter.get_zero_state
        self.zero_magnitude.hardware_read_func = self.power_meter.get_zero_magnitude

        self.photodiode_response.hardware_read_func = self.power_meter.get_photodiode_response

        self.current_range.hardware_read_func = self.power_meter.get_current_range

    def disconnect(self):
        #disconnect logged quantities from hardware
        for lq in self.logged_quantities.values():
            lq.hardware_read_func = None
            lq.hardware_set_func = None
        
        #disconnect hardware
        self.power_meter.close()
        
        # clean up hardware object
        del self.power_meter

    def run_zero(self):
        self.power_meter.run_zero()