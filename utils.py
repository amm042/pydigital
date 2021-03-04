import re
def verilog_fmt(fstr, *args, timeval = -1):
    """Verilog % style formating
    Supports %t for time and %d or %x for integers only!
    It does support width specifiers on all arg types.

    Example:
    >>> verilog_fmt("At time %3t, value = 0x%05x (%d)", 99, 99, timeval = 33)
    At time  33, value = 0x00063 (99)
    """    
    argidx = 0
    pos = 0
    s = ""
    for part in re.finditer(r"(\%\d*[txd])", fstr):
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