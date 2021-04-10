"""
memory.py
=========
Provides a byte-addressed memory.
"""
from pydigital.utils import sextend
class Memory:
    "Memory module which implements the risc-v sodor memory interface"
    def __init__(self, segment = None):
        "initialize with a memory segment"
        self.mem = segment
    def out(self, addr, byte_count = 4, signed = True):
        "read access"
        if addr == None:
            return None
        #TODO check of byte_count is larger than word size, that won't work!
        if signed:
            f = sextend
        else:
            f = lambda x, c: x
        if byte_count == 1:
            return f(self.mem[addr] & 0xff, 8)
        elif byte_count == 2:
            return f(self.mem[addr] & 0xffff, 16)
        elif byte_count == 4:
            return f(self.mem[addr] & 0xffffffff, 32)
        elif byte_count == 8:
            return self.mem[addr] & 0xffffffffffffffff
        else:
            raise ValueError("Mem can only access Bytes/Half Words/Words.")
    def clock(self, addr, data, mem_rw = 0, byte_count = 4):
        "synchronous write, mem_rw=1 for write"
        if mem_rw == 1:
            mask = (2**(byte_count*8))-1
            #print(f"MEM write mask {mask:08x} masked val is {(mask&data):08x} of {byte_count} bytes")
            # mask out any upper bits so to_bytes doesn't complain
            val = (mask & data).to_bytes(length=byte_count,
                byteorder = self.mem.byteorder, signed = False)
            #print(f'MEM val is {val}')
            self.mem[addr] = val
class ELFMemory:
    "ELFMemory is a collection of memory segments that supports get/set"
    def __init__(self):        
        self.mems = []
        self.byteorder = None
    def __getitem__(self, i):
        if i == None: 
            return None
        for m in self.mems:
            if i in m:
                return m[i]
        raise IndexError(f"Address {i:08x} not found in memory.")
    def __setitem__(self, i, val):
        if i == None:
            return
        for m in self.mems:
            if i in m:                  
                m[i] = val
    def __iadd__(self, seg):
        if self.byteorder == None:
            self.byteorder = seg.byteorder      
        elif self.byteorder != seg.byteorder:
            raise ValueError("Byteorder does not match previous segments.")
        self.mems.append(seg)
        return self
    def begin_addr(self):
        "return the lowest begin address included"
        return min([m.begin_addr for m in self.mems])
    def end_addr(self):
        "return the highest end address included"
        return max([m.end_addr for m in self.mems])
    def __str__(self):
        "debug segment addresses"
        s = []
        for i, seg in enumerate(self.mems):
            s += [f"[{i}] {seg.begin_addr:08x}:{seg.end_addr:08x} ({len(seg.data):4x} bytes)"]
        return "\n".join(s)
    def __len__(self):
        return sum([len(m.data) for m in self.mems])
class MemorySegment:
    "A continuous segment of byte addressable memory"
    def __init__(self, begin_addr = 0x1000, count = None, 
        word_size = 4, data = None, byteorder = 'big'):
        "create a new memory from begin_addr with count words (32 or 64 bits per word)"
        self.word_size = word_size
        self.byteorder = byteorder
        if data == None:
            if count == None:
                raise ValueError("Count must be given without data.")
            self.data = bytearray(self.word_size * count)           
        else:
            if count != None:
                 raise ValueError("Count must NOT be given with data.")            
            if type(data) is bytearray:
                self.data = data
            else:
                # attempt to convert to bytearray
                self.data = bytearray(data)
        self.end_addr = begin_addr + len(self.data)
        self.begin_addr = begin_addr
    def __str__(self):
        return f"Memory[{self.begin_addr:8x}:{self.end_addr:8x}] ({len(self.data)})"
    def __getitem__(self, i):
        "get a word from a given *byte* address"
        if i == None:
            return None
        if isinstance(i, slice):
            # if you ask for a slice, you get raw bytes
            data = self.data[i.start - self.begin_addr: i.stop - self.begin_addr: i.step]            
            return data
            # this decodes, but that's less useful
            #return [int.from_bytes(data[_i:_i+self.word_size], byteorder=self.byteorder, signed=False) \
                    #for _i in data[::self.word_size]]
        else:
            try:
                i -= self.begin_addr
            except TypeError as err:
                print("can't access", i)
                raise err
            # returns the given word size value as an unsigned int (preserving 2s comp)
            return int.from_bytes(
                self.data[i: i+self.word_size],
                byteorder=self.byteorder, signed=False)
    def __setitem__(self, i, val, signed=False):
        "set a word at given *byte* address"
        if type(val) == int:
            # convert to a words/bytes
            val = val.to_bytes(length=self.word_size, 
                byteorder=self.byteorder, signed=signed)
        if type(val) == bytes or type(val) == bytearray:
            # print('setting bytes', val)
            # byte by byte copy
            i -= self.begin_addr
            for v in val:
                self.data[i] = v
                i += 1 
        else:
            raise ValueError("Value must be bytes or int.")
        # self.data[(i - self.begin_addr) // self.word_size] = self.fromTwosComp(val)
    def __contains__(self, addr):
        "is the given byte address in this memory segment?"
        if isinstance(addr, slice):
            return addr.start in self and addr.stop in self
        else:
            return addr >= self.begin_addr and addr < self.end_addr
    def to_hex(self):
        s = ["@" + format(int(self.begin_addr / self.word_size), "x")]
        
        fmt = f"0{2*self.word_size}x"
        num = int(len(self.data) / self.word_size)
        print(fmt)
        for wordaddr in range(num):
            byteaddr = wordaddr * self.word_size
            d = int.from_bytes(self.data[byteaddr: byteaddr + self.word_size], 
                byteorder=self.byteorder)    
            s.append(format(d, fmt))

        return " ".join(s)

def readmemh(filename, begin_addr = 0, word_size = 4, byteorder = 'big'):
    "reads a verilog hex file and returns a memory segment"
    at = begin_addr
    data = None
    with open (filename, 'r') as f:
        for statement in f.read().split():            
            if statement[0] == '@':
                if data != None:
                    # output segment before creating a new one
                    # multi segment hex files are not supported atm.
                    raise NotImplementedError()
                # the hex file is indexed by words
                at = word_size * int (statement[1:], base=16)
                data = []
            else:
                data.append(int(statement, 16).to_bytes(word_size, byteorder))

    data = b"".join(data)
    return MemorySegment(begin_addr = at, 
        data = data, 
        word_size = word_size,
        byteorder = byteorder)
    