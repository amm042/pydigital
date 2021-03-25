"""
utils.py
========
Misc utilities for working on digital systems including sign extension of python integers.
"""

import re
from functools import partial
def verilog_fmt(fstr, *args, timeval = -1):
    """
    Verilog % style formating
    Supports %t for time and %d or %x for integers only!
    It does support width specifiers on all arg types.

    Example:
    verilog_fmt("At time %3t, value = 0x%05x (%d)", 99, 99, timeval = 33)
    At time  33, value = 0x00063 (99)
    """    
    argidx = 0
    pos = 0
    s = ""
    for part in re.finditer(r"(\%\d*[stxd])", fstr):
        s += fstr[pos:part.start(0)]
        pos = part.end(0)
        fmt = part[0][1:]   # strip leading % from format
        if part[0][-1] == 't':
            val = timeval   # use special global time val
            fmt = fmt[:-1] + 'd' # replace trailing t with d for format
            if fmt == 'd':  # check if no width specified because
                fmt = "20d" # verilog defaults to 20 digits for time.
        else:
            val = args[argidx]
            argidx += 1
            if val == None: # if arg value is None, treat as Undefined (X)
                widthstr = fmt[:-1]
                if widthstr == "":
                    val = 'x'
                else:
                    try:
                        val = 'x'*int(widthstr)
                    except ValueError:
                        val = 'x'
                fmt = ""
        s += format(val, fmt)
    s += fstr[pos:]
    return s

def sextend(val, c=32):
    "sign extend a c bit val to 32 bits as a python integer"
    # this converts from a twos-complement number to a python signed integer
    sign = 0b1 & (val >> (c-1))
    mask = (1 << c) - 1
    

    if sign == 0b1:        
        uppermask = 0xffffffff ^ mask
        #print(f"sign {sign:02x} mask = {mask:08x}, uppermask {uppermask:08x}, val = {val:08x}")
        # invert plus one, after sign extension
        return - (0xffffffff - (uppermask | val) + 1) 
    else:
        # positive values (should we check if > 32 bits and truncate?)
        return val 

def sextend12(val):
    "12 bit sign extender, generates a 32 bit 2s comp value from a 12-bit 2s comp value."
    return partial(sextend, c=12)

def as_twos_comp(val):
    "take a python signed integer value and represent as a 32-bit 2-s complement integer"
    # python bit masking uses the maximum number from either operand and
    # expands the other value to match, so this is easy.
    if val == None:
        return None
    if val >= 0:
        return val# & 0x7fffffff
    else:
        return val & 0xffffffff

if __name__=="__main__":

    print (f'{sextend(0x80000000):08x}')
    print(f'{as_twos_comp(-1)<<1:08x}')
    exit()
    for a in [0, 1, -1, 0x7fffffff, -0x80000000, 0x80000000]:
        twos = as_twos_comp(a)
        fromtwos = sextend(twos)
        print(f"a = {a:+09x} as twos = {twos:08x} from twos {fromtwos:+09x}")
        assert fromtwos == a