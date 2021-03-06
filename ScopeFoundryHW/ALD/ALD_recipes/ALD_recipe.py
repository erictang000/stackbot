'''
Created on May 25, 2018

@author: Alan Buckley <alanbuckley@lbl.gov>
                        <alanbuckley@berkeley.edu>
'''

from ScopeFoundry import Measurement
from threading import Lock
import numpy as np
import datetime
import time
import csv
import os

class ALD_Recipe(Measurement):
    """
    This module contains functions which regulate the behavior of the equipment used 
    during the deposition routine. The instruction sets contained here and the user set
    parameters are called a "Recipe."
    
    The run function in this module runs the recipe according to user set parameters. 
    If interrupted, the recipe is interrupted, and the system is allowed time to pump 
    down to initial levels.
    
    This Measurement module and the 
    :class:`ALD_Display` module are interdependent and make calls to functions in the other module.
    These modules should be loaded by 
    :class:`ALD_App`
    in the following order:
    
    1. :class:`ALD_Recipe <ALD.ALD_recipes.ALD_recipe>`
    2. :class:`ALD_Display <ALD.ALD_recipes.ALD_display>`
    


    """
    name = 'ALD_Recipe'
    
    MFC_valve_states = {'Open': 'O',
                         'Closed': 'C',
                         'Manual': 'N'}
    
    header = ['Time', 'Cycles Completed', 'Steps Taken', 'Step Name', 'Shutter Open', \
                       'PV1', 'PV2', 'CM Gauge (Torr)', 'Pirani Gauge (Torr)', 'Manometer (Torr)', \
                       'Valve Position (%)', 'Set Forward Power (W)', 'Read Forward Power (W)', \
                       'Reflected Power (W)', 'MFC Flow Rate (sccm)', 'SV Setpoint (C)', \
                       'PV Temperature (C)', 'Proportional', 'Integral', 'Derivative']
    
    def setup(self):
        
        self.lock = Lock()
        
        self.relay = self.app.hardware['ald_relay_hw']
        if hasattr(self.app.hardware, 'ald_shutter'):
            self.shutter = self.app.hardware.ald_shutter
        else:
            print('Connect ALD shutter HW component first.')
        self.lovebox = self.app.hardware['lovebox']
        if hasattr(self.app.hardware, 'mks_146_hw'):
            self.mks146 = self.app.hardware['mks_146_hw']
        else:
            self.mks146 = None
        if hasattr(self.app.hardware, 'mks_600_hw'):
            self.mks600 = self.app.hardware['mks_600_hw']
        else:
            self.mks600 = None
        self.vgc = self.app.hardware['pfeiffer_vgc_hw']
        self.seren = self.app.hardware['seren_hw']
        self.vat = self.app.hardware['vat_throttle_hw']
        

    
        self.PV_default_time = 1.
        self.default_recipe_array = [[0.3, 0.07, 2.5, 5., 0.3, 0.3, 0],
                                     [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 0.0]]
        self.default_subroutine = [[3., 0.02, 1.]]
        self.settings.New('cycles', dtype=int, initial=1, ro=False, vmin=1)
#         self.settings.New('time', dtype=float, array=True, initial=self.default_times, fmt='%1.3f', ro=False)
#         self.settings.New('positions', dtype=float, array=True, initial=self.default_positions, fmt='%1.3f', ro=False)
#         self.settings.New('subroutine', dtype=float, array=True, initial=self.default_subroutine, fmt='%1.3f', ro=False)

        self.settings.New('recipe_array', dtype=float, array=True, initial=self.default_recipe_array,\
                                            fmt='%g', ro=False)
#                                             fmt='1.3f%', ro=False)
        self.settings.New('PV1', dtype=int, initial=0, ro=True)
        self.settings.New('PV2', dtype=int, initial=0, ro=True)
        
        self.settings.New('t3_method', dtype=str, initial='Shutter', ro=False, choices=(('PV'), ('RF'), ('Shutter')))
        self.settings.New('cycles_completed', dtype=int, initial=0, ro=True)
        self.settings.New('step', dtype=int, initial=0, ro=True)
        self.settings.New('steps_taken', dtype=int, initial=0, ro=True)

        self.create_indicator_lq_battery()
        
        self.settings.New('csv_save_path', dtype=str, initial='', ro=False)
        self.set_default_save_location()

#         self.predep_complete = None
        self.dep_complete = None

        self.display_loaded = False

    
    def create_indicator_lq_battery(self):
        """
        Creates indicator *LoggedQuantities* which indicate the steps completed 
        towards the completion of the deposition process.
        """
        self.settings.New('pumping', dtype=bool, initial=False, ro=True)
        self.settings.New('predeposition', dtype=bool, initial=False, ro=True)
        self.settings.New('deposition', dtype=bool, initial=False, ro=True)
        self.settings.New('vent', dtype=bool, initial=False, ro=True)
        self.settings.New('pumped', dtype=bool, initial=False, ro=True)
        self.settings.New('gases_ready', dtype=bool, initial=False, ro=True)
        self.settings.New('substrate_hot', dtype=bool, initial=False, ro=True)
        self.settings.New('recipe_running', dtype=bool, initial=False, ro=True)
        self.settings.New('recipe_completed', dtype=bool, initial=False, ro=True)
     
    
    def set_default_save_location(self):
        """
        Sets default save location and stores it to *Logged Quantity*
        :attr:`self.settings.csv_save_path`
        """
        home = os.path.expanduser("~")
        self.path = home+'\\Desktop\\'
        filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+'.csv'
        self.full_file_path = self.path+filename
        self.settings['csv_save_path'] = self.full_file_path
        self.firstopened = True

        
    def db_poll(self, step='Placeholder'):
        """
        This command reads all relevant data at the time of its call and logs the data to a
        comma separated value (csv) file.
        
        Calling this the first time since application start creates the csv file with the 
        current time stamp as its filename.
        
        Subsequent calls will append data to existing csv log.
        
        =============  ==========  ==========================================================
        **Arguments**  **type**    **Description**
        step           str         Name of current step in recipe. Allows user to determine 
                                   the step in which data was logged.
        =============  ==========  ==========================================================
        """
        
        entries = []
        entries.append(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        entries.append(self.settings['cycles_completed'])
        entries.append(self.settings['steps_taken'])
        entries.append(step)
        entries.append(int(self.shutter.settings['shutter_open']))
        entries.append(self.settings['PV1'])
        entries.append(self.settings['PV2'])
        entries.append(self.vgc.settings['ch3_pressure_scaled'])
        entries.append(self.vgc.settings['ch2_pressure_scaled'])
        if self.mks600 is not None:
            entries.append(self.mks600.settings['pressure'])
            entries.append(self.mks600.settings['read_valve_position'])
        else:
            entries.extend([0,0])
        entries.append(self.seren.settings['set_forward_power'])
        entries.append(self.seren.settings['forward_power_readout'])
        entries.append(self.seren.settings['reflected_power'])
        if self.mks146 is not None:
            entries.append(self.mks146.settings['MFC0_flow'])
        else:
            entries.append(0)
        entries.append(self.lovebox.settings['sv_setpoint'])
        entries.append(self.lovebox.settings['pv_temp'])
        entries.append(self.lovebox.settings['Proportional_band'])
        entries.append(self.lovebox.settings['Integral_time'])
        entries.append(self.lovebox.settings['Derivative_time'])
        if self.firstopened == True:
            self.new_csv(entries)
        else:
            self.add_to_csv(entries)

    
    def new_csv(self, entry):
        '''
        Creates new comma separated value (csv) file, opens it, and writes an array the first row of 
        csv file.
        
        Run this once to create a new file.
        Run :meth:`add_to_csv` to add new entries.
        
        =============  ==========================================================
        **Arguments**  **Description**
        entry          List to be written to comma separated value formatted log
                       List must have same length as :attr:`header`
                       (Currently input array should have length of 20)
        =============  ==========================================================
        '''
        file = self.settings['csv_save_path']
        with open(file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(self.header)
            writer.writerow(entry)
        self.firstopened = False
    
    def add_to_csv(self, entry):
        
        '''
        Once :meth:`new_csv` is run (and a csv file created,) this function appends 
        entries of another array to a new row in the csv file.
        
        
        =============  ==========================================================
        **Arguments**  **Description**
        entry          List to be written to comma separated value formatted log
                       List must have same length as :attr:`header`
                       (Currently input array should have length of 20)
        =============  ==========================================================
        '''
        file = self.settings['csv_save_path']
        with open(file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(entry)
    
    def load_display_module(self):
        '''Adds listener functions to *LoggedQuantities* so that updates to LQs call functions to 
        recalculate quantities in UI elements and apply updates to LQ arrays'''
        print('load_display')
        if hasattr(self.app.measurements, 'ALD_display'):
            self.display = self.app.measurements.ALD_display
            self.display_loaded = True
            print("Display loaded:", self.display_loaded)
            # Sometimes.. :0
            self.settings.cycles.add_listener(self.sum_times)
            self.settings.recipe_array.add_listener(self.sum_times)
#             self.settings.subroutine.add_listener(self.sum_times)
            self.settings.t3_method.add_listener(self.t3_update)
        
    def t3_update(self):
        '''
        Checks 
        :meth:`self.settings.t3_method` to ascertain current operating mode. 
        Loads t3 entry in array 
        :meth:`self.settings.time` and updates time table 
        accordingly in user interface. 
        
        Time table object can be found as:
        :attr:`app.measurements.ALD_display.pulse_table`
        Its QTableModel object is defined as:
        :attr:`app.measurements.ALD_display.subtableModel`
        
        Acts as listener function in 
        :meth:`load_display_module`
        '''
        method = self.settings['t3_method']
        if method == 'PV':
            result = self.PV_default_time
        elif method == 'Shutter':
            result = self.default_recipe_array[0][3]
        elif method == 'RF':
            result = self.default_recipe_array[0][3]
            
        self.settings['recipe_array'][0][3] = result
        self.display.update_table()
    
#     def subroutine_sum(self):
#         """Sums values entered into subroutine time table 
#         :attr:`app.measurements.ALD_display.subroutine_table`, 
#         updates said table. 
#         
#         Called by 
#         :meth:`sum_times` when 
#         :attr:`self.settings.t3_method` is set to 'PV/Purge'.
#         
#         Not currently used.
#         """
#         data = self.settings['subroutine'][0]
#         coeff = int(data[0])
#         entries = data[1:]
#         self.settings['subroutine'][0][0] = coeff
#         self.display.update_subtable()
# 
#         return coeff*np.sum(entries)
    
    def sum_times(self):
        """
        Sometimes... :0
        
        Performs an estimated time calculation based on values in the main 
        time table. Every time the user updates data in the table, this function is called 
        to recalculate estimated recipe time requirements
        
        
        
        The table widget consists of a hierarchy of PyQt5 classes.
        The structure of the table widget assumes the following form:
        
        * :class:`QWidget`
            * :class:`QTableView`
                * :class:`QTableModel`
        
        More specific to the case of the subroutine table:
        
        * :class:`QWidget` (:attr:`subroutine_table_widget`)
            * :class:`QTableView` (:attr:`subroutine_table`)
                * :class:`QTableModel` (:attr:`subtableModel`)
                
        And in the case of the main recipe table:
        
        * :class:`QWidget` (:attr:`table_widget`)
            * :class:`QTableView` (:attr:`pulse_table`)
                * :class:`QTableModel` (:attr:`tableModel`)
                
        See \
        :meth:`ALD.ALD_recipes.ALD_display.setup_recipe_control_widget` \
        for details.
        
        
        **Example of table creation using PyQt5 and ScopeFoundry:**
        
        .. highlight:: python
        .. code-block:: python
        
            self.table_widget = QtWidgets.QWidget()
            self.table_widget_layout = QtWidgets.QHBoxLayout()
            self.table_widget.setLayout(self.table_widget_layout)
    
            self.table_label = QtWidgets.QLabel('Table Label')
            self.table_widget.layout().addWidget(self.table_label)
    
            self.table = QtWidgets.QTableView()
            ## Optional height constraint.
            self.table.setMaximumHeight(65)
            
            names = ['List', 'of', 'column', 'labels']
            
            self.tableModel = ArrayLQ_QTableModel(self.displayed_array, col_names=names)
            self.table.setModel(self.tableModel)
            self.table_widget.layout().addWidget(self.table)
            
            ### Add widget to enclosing outer widget
            self.containing_widget.layout().addWidget(self.table_widget)
        
        Note that :class:`ArrayLQ_QTableModel` is a ScopeFoundry function containing PyQt5 code.
        For simplicity, it has been included in ScopeFoundry's core framework under ndarray_interactive.
        """
#         if self.settings['t3_method'] == 'PV/Purge':
#             self.settings['recipe_array'][0][3] = self.subroutine_sum()
        prepurge = self.settings['recipe_array'][0][0]
        cycles = self.settings['cycles']
        total_loop_time = cycles*np.sum(self.settings['recipe_array'][0][1:5])
        print(total_loop_time)
        postpurge = self.settings['recipe_array'][0][5]
        sum_value = prepurge + total_loop_time + postpurge
        self.settings['recipe_array'][0][6] = sum_value
        if self.display_loaded:
            self.display.update_table()



    def set_precursor(self):
        '''
        .7 < Argon MFC < 2 sccm +
        X=Ar pressure < channel 3 pressure < Y=1
        '''
        pass

    def plasma_dose(self, width, power):
        """
        Turn on RF source for duration of time.
        
        =============  ==========  ==========================================================
        **Arguments**  **Type**    **Description**
        width          int         Duration RF source is active in seconds.
        power          int         RF forward power rating in Watts.
        =============  ==========  ========================================================== 

        """
        print('Start plasma dose.')
        self.seren.settings['set_forward_power'] = power
        self.seren.settings['RF_enable'] = True
        time.sleep(width)
        self.seren.settings['RF_enable'] = False
        self.seren.settings['set_forward_power'] = 0
        print('Plasma dose finished.')
        
    def valve_pulse(self, channel, width):
        """
        Open one of the pulse valves for specified duration of time, 'width'
        
        =============  ==========================================================
        **Arguments**  **Description**
        width          Valve open time in seconds. Once time width has elapsed, 
                       pulse valve closes once again.
        =============  ==========================================================
        """
        print('Valve pulse', width)
        step_name = 'Valve Pulse'
        assert channel in [1,2]
        self.relay.settings['pulse_width{}'.format(channel)] = 1e3*width
        getattr(self.relay, 'write_pulse{}'.format(channel))(width)
        self.settings['PV{}'.format(channel)] = 1
        t0 = time.time()
        t_lastlog = t0
        while True:
            if self.interrupt_measurement_called:
                self.settings['PV{}'.format(channel)] = 0 
                break
            if time.time()-t0 > width:
                self.settings['PV{}'.format(channel)] = 0
                break
            time.sleep(0.001)
            if time.time() - t_lastlog > 0.005:
                # do some logging
                self.db_poll(step_name)
                t_lastlog = time.time()
        self.settings['steps_taken'] += 1
    
    def purge(self, width):
        """
        This function tells the ALD system to wait 'width' duration of time to 
        allow gases to be vacated from the chamber by the vacuum pump.
        
        This function's timing mechanism is non-blocking.
        
        =============  ==========================================================
        **Arguments**  **Description**
        width          Duration of time for system to wait in order to allow for 
                       the purge of gases
        =============  ==========================================================
        """
        print('Purge', width)
        step_name = 'Purge'
        t0 = time.time()
        t_lastlog = t0
        while True:
            if self.interrupt_measurement_called:
                self.shutoff()
                break
            if time.time()-t0 > width:
                break
            time.sleep(0.001)
            if time.time() - t_lastlog > 0.2:
                # do some logging
                self.db_poll(step_name)
                t_lastlog = time.time()
        self.settings['steps_taken'] += 1
    
    def shutter_pulse(self, width):
        """
        Actuate (open, then close) shutter over interval, 'width'

        =============  ==========================================================
        **Arguments**  **Description**
        width          Time in which shutter remains in open position. 
                       Closes after 'width' seconds
        =============  ==========================================================
        """
        step_name = 'Shutter Pulse'
        self.shutter.settings['shutter_open'] = True
        self.db_poll(step_name)
        print('Shutter open')
        t0 = time.time()
        t_lastlog = t0
        while True:
            if self.interrupt_measurement_called:
                self.shutter.settings['shutter_open'] = False
                break
            if time.time()-t0 > width:
                break
            time.sleep(0.001)
            if time.time() - t_lastlog > 0.2:
                # do some logging
                self.db_poll(step_name)
                t_lastlog = time.time()
            
        self.shutter.settings['shutter_open'] = False
        self.settings['steps_taken'] += 1
        print('Shutter closed')

    def shutoff(self):
        '''
        Restores recipe system of indicators to initial state. 
        Any abort functions should also be called from within this function.
        When 
        :attr:`interrupt_measurement_called` is set to True, this method is called,
        and the routine loop is interrupted.
        '''
        self.display.ui_initial_defaults()
        self.settings['recipe_running'] = False

    
    def predeposition(self):
        """
        Runs pre-deposition stage. 
        * Sets MFC to manual open
        * Sets flow to 0.7 sccm
        
        Called by parent function
        :meth:`routine`
        """
#         status = self.mks146.settings['read_MFC0_valve']
#         if status == 'O' or status == 'C':
#             self.mks146.settings['set_MFC0_valve'] = 'N'
#             time.sleep(1)
#         self.mks146.settings['set_MFC0_SP'] = 0.7
        self.settings['predeposition'] = True
        
    def prepurge(self):
        """
        Runs pre-purge stage.
        Waits a certain duration of time to allow the vacuum pumps 
        time to vacate the chamber of gases.
        
        Called by parent function
        :meth:`routine`
        """
        width = self.times[0]
        position = self.positions[0]
        step_name = 'Pre-purge'
        print('Prepurge', width)
        self.db_poll(step_name)
        self.throttle_valve_set(position)
        time.sleep(width)
        self.settings['steps_taken'] += 1
    
    def throttle_valve_set(self, position):
        self.vat.vat_throttle.write_position(position)
    
    def routine(self):
        """
        This function carries out the looped part of our ALD routine.
        
        Called by parent function
        :meth:`deposition`
        """
        # Read in time table data

        _, t1, t2, t3, t4, _, _ = self.times
        _, p1, p2, p3, p4, _, _ = self.positions
        
        # Carry out routine
        self.throttle_valve_set(p1)
        self.valve_pulse(1, t1)
        if self.interrupt_measurement_called:
            self.shutoff()
            return
        
        self.throttle_valve_set(p2)    
        self.purge(t2)
        if self.interrupt_measurement_called:
            self.shutoff()
            return
            
        
        ## Check selected method for t3 in main recipe table,
        ## Carry out an operation based on the selection
        mode = self.settings['t3_method']
        self.throttle_valve_set(p3)
        
        if mode == 'Shutter':
            self.shutter_pulse(t3)
            if self.interrupt_measurement_called:
                self.shutoff()
                return
        elif mode == 'PV':
            self.valve_pulse(2, t3)
            if self.interrupt_measurement_called:
                self.shutoff()
                return    
        elif mode == 'RF':
            power = self.seren.settings['recipe_power']
            self.plasma_dose(t3, power)
            if self.interrupt_measurement_called:
                self.shutoff()
                return
#         elif mode == 'PV/Purge':
#             '''Run sub_cyc number of subroutine cycles.
#             Subroutine consists of a valve pulse and a purge period.'''
#             for _ in range(sub_cyc):
#                 self.valve_pulse(2, sub_t0)
#                 self.purge(sub_t1)
        
        
        self.throttle_valve_set(p4)
        self.purge(t4)
        if self.interrupt_measurement_called:
            self.shutoff()
            return
            
    
    def postpurge(self):
        """
        Runs post purge stage. 
        Waits a certain duration of time to allow the vacuum pumps time to vacate 
        the chamber of gases.
        
        Called by parent function
        :meth:`routine`
        """
        step_name = 'Post-purge'
        width = self.times[5]
        position = self.positions[5]
        print('Postpurge', width)
        self.db_poll(step_name)
        self.throttle_valve_set(position)
        time.sleep(width)
        self.settings['steps_taken'] += 1
        
    def deposition(self):
        """
        This function runs the full deposition routine. 
        Deposition routine is preceded by pre-purge step and succeeded by post-purge.
        See
        :meth:`run_recipe` for the full recipe when measurement loop is started.
        
        This is the parent function of 
        :meth:`routine`
        """
#         self.dep_complete = False
        cycles = self.settings['cycles']    
        for _ in range(cycles):
            self.routine()
            if self.interrupt_measurement_called:
                self.shutoff()
                break
            
            self.settings['cycles_completed'] += 1
            print(self.settings['cycles_completed'])
            if self.interrupt_measurement_called:
                self.shutoff()
                break
#         self.dep_complete = True
        self.settings['deposition'] = True
    
    def run_recipe(self):
        """Runs full recipe. Called when 
        :meth:`run` is executed."""
        self.settings['recipe_running'] = True
        self.settings['recipe_completed'] = False
        self.settings['steps_taken'] = 0
        self.settings['cycles_completed'] = 0
#         self.sub = self.settings['subroutine']
        self.times = self.settings['recipe_array'][0]
        self.positions = self.settings['recipe_array'][1]
        
        
        self.prepurge()
        if self.interrupt_measurement_called:
            self.shutoff()
            return
            
        self.deposition()

        self.postpurge()
        if self.interrupt_measurement_called:
            self.shutoff()
            return
            
        self.settings['recipe_running'] = False
        self.settings['recipe_completed'] = True
        print('recipe completed')

    def run(self):
        self.run_recipe()
        
