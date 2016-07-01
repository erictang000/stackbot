from ScopeFoundry import HardwareComponent
try:
    from equipment.picam import PiCAM, ROI_tuple
except Exception as err:
    print "Could not load modules needed for PICAM CCD:", err

import equipment.picam_ctypes as picam_ctypes
from equipment.picam_ctypes import PicamParameter


class PicamHardware(HardwareComponent):
    name = "picam"

    def setup(self):
        # Create logged quantities
        self.status = self.add_logged_quantity(name='ccd_satus', dtype=str, fmt="%s",ro=True)
    
        # Single ROI settings
        self.settings.New('roi_x', dtype=int, initial=0, si=False)
        self.settings.New('roi_w', dtype=int, initial=1340, si=False)
        self.settings.New('roi_x_bin', dtype=int, initial=1, si=False)
        self.settings.New('roi_y', dtype=int, initial=0, si=False)
        self.settings.New('roi_h', dtype=int, initial=100, si=False)
        self.settings.New('roi_y_bin', dtype=int, initial=1, si=False)

        # Auto-generate settings from PicamParameters
        for name, param in PicamParameter.items():
            print name, param
            dtype_translate = dict(FloatingPoint=float, Boolean=bool, Integer=int)
            if param.param_type in dtype_translate:
                self.add_logged_quantity(name=param.short_name, dtype=dtype_translate[param.param_type])

            elif param.param_type == 'Enumeration':
                enum_name = "Picam{}Enum".format(param.short_name)
                if hasattr(picam_ctypes, enum_name):
                    enum_obj = getattr(picam_ctypes, enum_name)
                    choice_names = enum_obj.bysname.keys()
                    self.add_logged_quantity(name=param.short_name, dtype=str, choices=choice_names)


        # operations
        self.add_operation('commit_parameters', self.commit_parameters)
    
        #connect to custom gui - NOTE:  these are not disconnected! 

    def connect(self):
        if self.debug_mode.val: print "Connecting to PICAM"
        
        self.cam = PiCAM()

        supported_pnames = self.cam.get_param_names()

        for pname in supported_pnames:
            if pname in self.settings.as_dict():
                print "connecting", pname
                lq = self.settings.as_dict()[pname]
                print "lq.name", lq.name
                lq.hardware_read_func = lambda pname=pname: self.cam.read_param(pname)
                print lq.read_from_hardware()
                rw = self.cam.get_param_readwrite(pname)
                print "picam param rw", lq.name, rw
                if rw in ['ReadWriteTrivial', 'ReadWrite']:
                    lq.hardware_set_func = lambda x, pname=pname: self.cam.write_param(pname, x)
                elif rw == 'ReadOnly':
                    lq.change_readonly(True)
                else:
                    raise ValueError("picam param rw not understood", rw)
                
        for lqname in ['roi_x', 'roi_w', 'roi_x_bin', 'roi_y', 'roi_h', 'roi_y_bin']:
            self.settings.get_lq(lqname).updated_value.connect(self.write_roi)


    def write_roi(self, a=None):
        print 'write_roi'
        S = self.settings
        self.cam.write_single_roi(x=S['roi_x'], width=S['roi_w'],  x_binning=S['roi_x_bin'],
                                  y=S['roi_y'], height=S['roi_h'], y_binning=S['roi_y_bin'])

    def disconnect(self):
        
        #disconnect hardware
        self.cam.close()
        
        #disconnect logged quantities from hardware
        for lq in self.logged_quantities.values():
            lq.hardware_read_func = None
            lq.hardware_set_func = None
        
        # clean up hardware object
        del self.cam
        
        #self.is_connected = False
    
    def commit_parameters(self):
        self.cam.commit_parameters()
    
