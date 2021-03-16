class Register:
    "A generic register, at the clock edge the input is evaluated and assigned to the output"
    def __init__(self, *args):        
        self._val = None
        self._args = args
        self.out = lambda: self._val
    def reset(self, value):    
        # asynchronous (re)set
        self._val = value
    def clock (self, next_val):
        # the system block evaluates all inputs and passes in their values here
        # we just need to assign (copy) them to the stored values
        self._val = next_val