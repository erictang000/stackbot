'''
Created on Jun 29, 2017

@author:    Alan Buckley, 
            Benedikt Ursprung (Simple version)
'''


from ScopeFoundry import HardwareComponent
from pywinusb import hid
    

class PowermateHWSimple(HardwareComponent):
    
    name = "powermate_hw"    
    def setup(self):
        """
        This module creates a list of devices handlers. 
        Implement a raw_data_handler on the measurement level and use self.set_data_handler 
        to assign devices to settings.
        """
        pass
        

    def connect(self):
        """Connects to equipment level module, 
        creates list of devices handlers and finally opens them"""

        # get device addresses        
        self.filter = hid.HidDeviceFilter(vendor_id=0x077D, product_id = 0x0410)
        self.device_addrs = []
        for v in self.filter.get_devices_by_parent().items():
            self.device_addrs.append(v[0])
            #print(v)
        
        # create devices handler list
        self.devices = []
        for addr in self.device_addrs:
            dev = self.filter.get_devices_by_parent()[addr][0]           
            self.devices.append(dev)
            
        self.open_all_devices()


    def set_data_handler(self, powermate_dev_number, raw_data_handler):
        """Use this function to connect a device to a function on the measurement level.
        
        powermate_dev_number     *int         0 ... #devices-1
        raw_data_handler(data)   *function
            data                 *list         output from devices. (is implemented in hid class)
            do something with the data.i.e. manipulate logged quantities 
        """
        try:
            self.devices[powermate_dev_number].set_raw_data_handler(raw_data_handler)      
        finally:
            pass        
        
         
    def open_all_devices(self):
        for dev in self.devices:
            if not dev.is_opened():           
                dev.open()

        
    def close_all_devices(self):
        for dev in self.devices:
            if dev.is_opened():
                dev.close()
        
        
    def disconnect(self):
        """Hardware disconnect and cleanup function."""
        if hasattr(self, 'devices'):
            self.close_all_devices()
            del self.devices
            
        if hasattr(self, 'device_addrs'):
            del self.device_addrs


class PowermateHW(HardwareComponent):

    name = "powermate_hw"
    def setup(self):
        self.settings.New(name='devices', initial=None, dtype=str, choices = [], ro=True)
        self.settings.New(name='button', initial=True, dtype=bool, ro=True)
        self.settings.New(name='wheel_axis', initial=0, dtype=int, ro=True)
        self.add_operation(name='poll_devices', op_func=self.poll_devices)
        
    def connect(self):
        """Connects to equipment level module, 
        loads the appropriate key map into memory,
        opens the selected device, sets data handler."""
        self.poll_devices()

    def detect_devices(self):
        self.filter = hid.HidDeviceFilter(vendor_id=0x077D)
        self.retrieve_addresses()

    def retrieve_addresses(self):
        self.device_map = {}
        for j, v in enumerate(self.filter.get_devices_by_parent().items()):
            addr_hw_pair = tuple([v[0], v[1][0]])
            self.device_map[j] = addr_hw_pair
            self.dev_num = j
        
    def poll_devices(self):
        self.detect_devices()
        
        self.choice_list = []
        for i in range(self.dev_num+1):
            update = (self.device_map[i][0])
            self.choice_list.append(update)
        
        self.settings.devices.change_choice_list(self.choice_list)
        
                
    def open_active_device(self):
        if hasattr(self, 'active_device'):
            if self.active_device.is_opened:
                self.active_device.close()
        else: pass
        device_addr = self.settings.devices.val
        self.active_device = self.filter.get_devices_by_parent()[int(device_addr)][0]
        self.active_device.open()
        
    def set_data_handler(self):
        self.active_device.set_raw_data_handler(self.raw_data_handler)
            
    def raw_data_handler(self, data):
#         print(data)
        self.settings['button'] = bool(data[1])
        wheel = data[2]
        if wheel > 1:
            self.settings['wheel_axis'] -= 1
        elif wheel == 1:
            self.settings['wheel_axis'] += 1    
    
    def close_active_device(self):
        if self.active_device.is_opened:
            self.active_device.close()
       
    def disconnect(self):
        """Hardware disconnect and cleanup function."""
        self.close_active_device()
        del self.active_device
        del self.device_map
        del self.choice_list