"""
pydigital is a verlog-like simulation engine for digital systems.

The system class provides a clock to various modules.

Alan Marchiori 2021
"""

from .utils import verilog_fmt

class System():
    """
    The system clock generates clock ticks and keeps track of time
    Similar to verilog:
        reg clk = 0;
        always #1 clk = !clk;
    """
    def __init__(self, posedge=[], negedge=[]):
        "Pass in componets to be clocked on positive and negative edges"
        self.time = 0
        self._val = False
        self._pos = posedge
        self._neg = negedge
        self._mon_str = None
        self._mon_vals = []
        self._disp_str = None
        self._disp_vals = []
    def monitor(self, mon_str, *mon_vals):
        "Attach a monitor, mon_vals must be functions that return the current value"
        self._mon_str = mon_str
        self._mon_vals = mon_vals
        self._mon_last_vals = None
        self.do_monitor()
    def display(self, mon_str, *mon_vals):
        "Attach a display, mon_vals must be functions that return the current value"
        self._disp_str = mon_str
        self._disp_vals = mon_vals
        self.do_display()
    def do_display(self):
        "evaluates the expressions and prints if anything has changed"                       
        if self._disp_str and self._disp_vals:
            clk = '-'
            if self._val:
                clk = '+'
            print (clk + verilog_fmt(self._disp_str, 
                    *[x() for x in self._disp_vals], 
                    timeval = self.time))        

    def do_monitor(self):
        "evaluates the monitored expressions and prints if anything has changed"
        # evaluate all monitored values and store
        current_vals = [x() for x in self._mon_vals]

        # only print if there is a monitor and something changed
        if self._mon_str and self._mon_vals and current_vals != self._mon_last_vals:
            clk = '-'
            if self._val:
                clk = '+'
            print (clk + verilog_fmt(self._mon_str, 
                    *current_vals, 
                    timeval = self.time))
        self._mon_last_vals = current_vals

    def __iter__(self):
        return self
    def __next__(self):        
        # update monitor
        self.do_monitor()

        self._val ^= True # invert the clock level
        self.time += 1    # increment time 

        def evaluate(modules):
            # sample inputs
            vals = []
            for x in modules:
                vals.append(list(y() for y in x.inputs))
            # clock passing in input vals
            for x,y in zip(modules, vals):
                x.clock(*y)

        # execute the pos/negedge methods
        if self._val:            
            evaluate(self._pos)
        else:
            evaluate(self._neg)

        # update monitor
        self.do_monitor()
        
        # execute displays
        self.do_display()
        return self._val  # return new clock level

    def run(self, ticks=2):
        """run the system for the given number of clock ticks (clock half-cycles), 
           like a #ticks; in verilog
           The default (2) runs one full clock period.
        """       
        for _i in range(ticks):
            next(self)