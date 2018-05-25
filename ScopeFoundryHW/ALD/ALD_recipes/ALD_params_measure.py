'''
Created on Apr 11, 2018

@author: Alan Buckley <alanbuckley@berkeley.edu>
                      <alanbuckley@lbl.gov>
'''

from ScopeFoundry import Measurement
from ScopeFoundry.ndarray_interactive import ArrayLQ_QTableModel
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.Qt import QVBoxLayout
from ScopeFoundryHW.ALD.ALD_recipes import resources
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock
import numpy as np
import datetime
import time
import os
from ScopeFoundryHW.ALD.ALD_recipes.ALD_recipe import ALD_Recipe


class ALD_params(Measurement):
    
    name = 'ALD_params'
    
    def __init__(self, app):
        Measurement.__init__(self, app)        
        
    def setup(self):
        self.cb_stylesheet = '''
        QCheckBox::indicator {
            width: 100px;
            height: 100px;
        }
        QCheckBox::indicator:checked {
            image: url(://icons//green-led-on.png);
        }
        QCheckBox::indicator:unchecked {
            image: url(://icons//led-red-on.png);
        }
        '''

        self.settings.New('RF_pulse_duration', dtype=int, initial=1)
        self.settings.New('history_length', dtype=int, initial=1e6, vmin=1)
        self.settings.New('shutter_open', dtype=bool, initial=False, ro=True)
        self.settings.New('display_window', dtype=int, initial=1e4, vmin=1)
        self.settings.New('cycles', dtype=int, initial=1, ro=False, vmin=1)
    
        self.settings.New('time', dtype=float, array=True, initial=[[0.3, 0.07, 2.5, 5, 0.3, 0.3, 0]], fmt='%1.3f', ro=False)

        self.setup_buffers_constants()
        self.settings.New('save_path', dtype=str, initial=self.full_file_path, ro=False)

        
        if hasattr(self.app.hardware, 'seren_hw'):
            self.seren = self.app.hardware.seren_hw
            if self.app.measurements.seren.psu_connected:
                print('Seren PSU Connected')
            else:
                print('Connect Seren HW component first.')

        if hasattr(self.app.hardware, 'ald_shutter'):
            self.shutter = self.app.hardware.ald_shutter
        else:
            print('Connect ALD shutter HW component first.')
        
        if hasattr(self.app.hardware, 'lovebox'):
            self.lovebox = self.app.hardware.lovebox
        
        if hasattr(self.app.hardware, 'mks_146_hw'):
            self.mks146 = self.app.hardware.mks_146_hw
        
        if hasattr(self.app.measurements, 'ALD_Recipe'):
            self.recipe = self.app.measurements.ALD_Recipe
        else:
            print('ALD_Recipe not setup')
            
        self.ui_enabled = True
        if self.ui_enabled:
            self.ui_setup()

        self.settings.time.add_listener(self.sum)
        self.settings.cycles.add_listener(self.sum)
    
    def sum(self):
        prepurge = self.settings['time'][0][0]
        cycles = self.settings['cycles']
        total_loop_time = cycles*np.sum(self.settings['time'][0][1:5])
        print(total_loop_time)
        postpurge = self.settings['time'][0][5]
        sum_value = prepurge + total_loop_time + postpurge
        self.settings['time'][0][6] = sum_value
        self.tableModel.on_lq_updated_value()

    def ui_setup(self):
        
        self.ui = DockArea()
        self.layout = QtWidgets.QVBoxLayout()
        self.ui.show()
        self.ui.setWindowTitle('ALD Control Panel')
        self.ui.setLayout(self.layout)
        self.widget_setup()
        self.dockArea_setup()

    def dockArea_setup(self):
        self.rf_dock = Dock('RF Settings')
        self.rf_dock.addWidget(self.rf_widget)
        self.ui.addDock(self.rf_dock)

        self.thermal_dock = Dock('Thermal History')
        self.thermal_dock.addWidget(self.thermal_widget)
        self.ui.addDock(self.thermal_dock, position='right', relativeTo=self.rf_dock)
        
        self.shutter_dock = Dock('Shutter Controls')
        self.shutter_dock.addWidget(self.shutter_control_widget)
        self.ui.addDock(self.shutter_dock, position='bottom')
        
        self.display_ctrl_dock = Dock('Display Controls')
        self.display_ctrl_dock.addWidget(self.display_control_widget)
        self.ui.addDock(self.display_ctrl_dock, position='right', relativeTo=self.shutter_dock)
        
        self.ui.addDock(name="Recipe Controls", position='bottom', widget=self.recipe_control_widget)
        
        
    def load_ui_defaults(self):
        pass
    
    def save_ui_defaults(self):
        pass
    
    def widget_setup(self):
        self.setup_shutter_control_widget()
        self.setup_thermal_control_widget()
        self.setup_rf_flow_widget()
        self.setup_recipe_control_widget()
        self.setup_display_controls()

    def setup_thermal_control_widget(self):
        self.thermal_widget = QtWidgets.QGroupBox('Thermal Controller Overview')
        self.layout.addWidget(self.thermal_widget)
        self.thermal_widget.setLayout(QtWidgets.QVBoxLayout())
        self.thermal_channels = 1
        

        self.thermal_plot_widget = pg.GraphicsLayoutWidget()
        self.thermal_plot = self.thermal_plot_widget.addPlot(title='Temperature History')
        self.thermal_plot.showGrid(y=True)
        self.thermal_plot.addLegend()
        self.thermal_widget.layout().addWidget(self.thermal_plot_widget)
        self.thermal_plot_names = ['Heater Temperature']
        self.thermal_plot_lines = []
        for i in range(self.thermal_channels):
            color = pg.intColor(i)
            plot_line = self.thermal_plot.plot([1], pen=pg.mkPen(color, width=2),
                                                    name = self.thermal_plot_names[i])
            self.thermal_plot_lines.append(plot_line)
        self.vLine1 = pg.InfiniteLine(angle=90, movable=False)
        self.hLine1 = pg.InfiniteLine(angle=0, movable=False)
        self.thermal_plot.addItem(self.vLine1)
        self.thermal_plot.addItem(self.hLine1)
    
    def setup_rf_flow_widget(self):
        self.rf_widget = QtWidgets.QGroupBox('RF Settings')
        self.layout.addWidget(self.rf_widget)
        self.rf_widget.setLayout(QtWidgets.QVBoxLayout())
        
        self.rf_plot_widget = pg.GraphicsLayoutWidget()
        self.rf_plot = self.rf_plot_widget.addPlot(title='RF power and scaled MFC flow')
        self.rf_plot.showGrid(y=True)
        self.rf_plot.addLegend()
        self.rf_widget.layout().addWidget(self.rf_plot_widget)
        self.rf_plot_names = ['Forward', 'Reflected', 'MFC flow (scaled)']
        self.rf_plot_lines = []
        for i in range(self.RF_CHANS):
            color = pg.intColor(i)
            plot_line = self.rf_plot.plot([1], pen=pg.mkPen(color, width=2),
                                          name = self.rf_plot_names[i])
            self.rf_plot_lines.append(plot_line)
        self.vLine2 = pg.InfiniteLine(angle=90, movable=False)
        self.hLine2 = pg.InfiniteLine(angle=0, movable=False)
        self.rf_plot.addItem(self.vLine2)
        self.rf_plot.addItem(self.hLine2)
        
        
    def setup_shutter_control_widget(self):
        self.shutter_control_widget = QtWidgets.QGroupBox('Shutter Controls')
        self.shutter_control_widget.setLayout(QtWidgets.QGridLayout())
        self.shutter_control_widget.setStyleSheet(self.cb_stylesheet)

        self.layout.addWidget(self.shutter_control_widget)        
        
        self.shutter_status = QtWidgets.QCheckBox(self.shutter_control_widget)
        self.shutter_control_widget.layout().addWidget(self.shutter_status, 0, 0)
        self.shutter.settings.shutter_open.connect_to_widget(self.shutter_status)

        self.shaul_shutter_toggle = QtWidgets.QPushButton('Shaul\'s Huge Shutter Button')
        self.shaul_shutter_toggle.setMinimumHeight(200)
        font = self.shaul_shutter_toggle.font()
        font.setPointSize(24)
        self.shaul_shutter_toggle.setFont(font)
        self.shutter_control_widget.layout().addWidget(self.shaul_shutter_toggle, 0, 1)
        if hasattr(self, 'shutter'):
            self.shaul_shutter_toggle.clicked.connect(self.shutter.shutter_toggle)

    def setup_recipe_control_widget(self):
        self.recipe_control_widget = QtWidgets.QGroupBox('Recipe Controls')
        self.recLayout = QtWidgets.QVBoxLayout()
        self.recipe_control_widget.setLayout(self.recLayout)
        self.layout.addWidget(self.recipe_control_widget)
    
        ## Settings Widget
        self.settings_widget = QtWidgets.QWidget()
        self.settings_layout = QtWidgets.QGridLayout()
        self.settings_widget.setLayout(self.settings_layout)
        
        self.cycle_label = QtWidgets.QLabel('N Cycles')
        self.settings_widget.layout().addWidget(self.cycle_label, 0,0)
        self.cycle_field = QtWidgets.QDoubleSpinBox()
        self.settings.cycles.connect_to_widget(self.cycle_field)
        self.settings_widget.layout().addWidget(self.cycle_field, 1,0)
        self.recipe_control_widget.layout().addWidget(self.settings_widget)
    
        ## Table Widget
        self.table_widget = QtWidgets.QWidget()
        self.table_widget_layout = QtWidgets.QHBoxLayout()
        self.table_widget.setLayout(self.table_widget_layout)

        self.pulse_label = QtWidgets.QLabel('Step Durations [s]')
        self.table_widget.layout().addWidget(self.pulse_label)

        self.pulse_table = QtWidgets.QTableView()
        self.pulse_table.setMaximumHeight(65)
        names = ['t'+u'\u2080'+' Pre Purge', 't'+u'\u2081'+' (TiCl'+u'\u2084'+' PV)',\
                  't'+u'\u2082'+' Purge', 't'+u'\u2083'+' (N'+u'\u2082'+'/Shutter)', \
                 't'+u'\u2084'+' Purge', 't'+u'\u2085'+' Post Purge', u'\u03a3'+'t'+u'\u1d62']
        self.tableModel = ArrayLQ_QTableModel(self.settings.time, col_names=names)
        self.pulse_table.setModel(self.tableModel)
        self.table_widget.layout().addWidget(self.pulse_table)
        self.recipe_control_widget.layout().addWidget(self.table_widget)
    
        self.recipe_panel = QtWidgets.QWidget()
        self.recipe_panel_layout = QtWidgets.QGridLayout()
        self.recipe_panel.setLayout(self.recipe_panel_layout)
        
        self.single_start_button = QtWidgets.QPushButton('Start 1 Recipe')
        self.single_start_button.clicked.connect(self.load_single_recipe)
        self.recipe_panel.layout().addWidget(self.single_start_button, 0, 0)
        
        self.start_button = QtWidgets.QPushButton('Start Recipe')
        self.start_button.clicked.connect(self.recipe.start)
        self.recipe_panel.layout().addWidget(self.start_button, 0, 1)
        
        self.abort_button = QtWidgets.QPushButton('Abort Recipe')
        self.abort_button.clicked.connect(self.recipe.interrupt)
        self.recipe_panel.layout().addWidget(self.abort_button, 0, 2)

        self.recipe_control_widget.layout().addWidget(self.recipe_panel)

    def load_single_recipe(self):
        self.recipe.load_times()
        self.recipe.routine()

        
    def setup_display_controls(self):
        self.display_control_widget = QtWidgets.QGroupBox('Display Control Panel')
        self.display_control_widget.setLayout(QtWidgets.QVBoxLayout())
        
        self.field_panel = QtWidgets.QWidget()
        self.field_panel_layout = QtWidgets.QGridLayout()
        self.field_panel.setLayout(self.field_panel_layout)
        self.display_control_widget.layout().addWidget(self.field_panel)
        
        self.export_button = QtWidgets.QPushButton('Export Temperature Data')
        self.save_field = QtWidgets.QLineEdit('Directory')
        self.save_field.setMinimumWidth(200)
        self.save_field.setMaximumWidth(600)

        self.field_panel.layout().addWidget(self.export_button, 1, 0)
        self.field_panel.layout().addWidget(self.save_field, 1, 1)
        
        self.export_button.clicked.connect(self.export_to_disk)
        self.settings.save_path.connect_to_widget(self.save_field)
        
        plot_ui_list = ('display_window','history_length')
        self.field_panel.layout().addWidget(self.settings.New_UI(include=plot_ui_list), 2,0)


    def setup_buffers_constants(self):
        home = os.path.expanduser("~")
        self.path = home+'\\Desktop\\'
        self.full_file_path = self.path+'np_export'
        self.psu_connected = None
        self.HIST_LEN = self.settings.history_length.val
        self.WINDOW = self.settings.display_window.val
        self.RF_CHANS = 3
        self.T_CHANS = 1
        self.history_i = 0
        self.index = 0
        
        self.rf_history = np.zeros((self.RF_CHANS, self.HIST_LEN))
        self.thermal_history = np.zeros((self.T_CHANS, self.HIST_LEN))
        self.time_history = np.zeros((1, self.HIST_LEN), dtype='datetime64[s]')
        self.debug_mode = False


    def plot_routine(self):
        if self.debug_mode:
            rf_entry = np.random.rand(3,)
            t_entry = np.random.rand(1,)
        else:
            rf_entry = np.array([self.seren.settings['forward_power_readout'], \
                             self.seren.settings['reflected_power'], \
                             self.mks146.settings['MFC0_flow']])
            t_entry = np.array([self.lovebox.settings['pv_temp']])

        time_entry = datetime.datetime.now()
        if self.history_i < self.HIST_LEN-1:
            self.index = self.history_i % self.HIST_LEN
        else:
            self.index = self.HIST_LEN-1
            self.rf_history = np.roll(self.rf_history, -1, axis=1)
            self.thermal_history = np.roll(self.thermal_history, -1, axis=1)
            self.time_history = np.roll(self.time_history, -1, axis=1)
        self.rf_history[:, self.index] = rf_entry
        self.thermal_history[:, self.index] = t_entry
        self.time_history[:, self.index] = time_entry
        self.history_i += 1
    
    def export_to_disk(self):
        path = self.settings['save_path']
        np.save(path+'_temperature.npy', self.thermal_history)
        np.save(path+'_times.npy', self.time_history)
        
    def update_display(self):
        self.WINDOW = self.settings.display_window.val
        self.vLine1.setPos(self.WINDOW)
        self.vLine2.setPos(self.WINDOW)
        
        lovebox_level = self.lovebox.settings['sv_setpoint']
        self.hLine1.setPos(lovebox_level)
        
        
        flow_level = self.mks146.settings['MFC0_SP']
        self.hLine2.setPos(flow_level)
        

        
        lower = self.index-self.WINDOW

        for i in range(self.RF_CHANS):
            if self.index >= self.WINDOW:

                self.rf_plot_lines[i].setData(
                    self.rf_history[i, lower:self.index+1])
            else:
                self.rf_plot_lines[i].setData(
                    self.rf_history[i, :self.index+1])
                self.vLine1.setPos(self.index)
                self.vLine2.setPos(self.index)

        for i in range(self.T_CHANS):
            if self.index >= self.WINDOW:
                self.thermal_plot_lines[i].setData(
                    self.thermal_history[i, lower:self.index+1])
                
            else:
                self.thermal_plot_lines[i].setData(
                    self.thermal_history[i, :self.index+1])
                self.vLine1.setPos(self.index)
                self.vLine2.setPos(self.index)
    
    def run(self):
        dt = 0.2
        while not self.interrupt_measurement_called:
            self.plot_routine()
            time.sleep(dt)
            