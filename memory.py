class MemorySegment:
    "A continuous segment of memory"
    def __init__(self, begin_addr = 0x1000, count = None, word_size = 4, data = None):
        "create a new memory from begin_addr with count words (32 or 64 bits per word)"
        self.word_size = word_size
       
        if data == None:
            if count == None:
                raise ValueError("Count must be given without data.")
            self.data = bytearray(self.word_size * count)           
        else:
            if count != None:
                 raise ValueError("Count must NOT be given with data.")            
            if type(data) is bytes:
                self.data = data
            else:
                # attempt to convert to bytes
                self.data = bytearray(data)
        self.end_addr = begin_addr + len(self.data) #* self.word_size
        self.begin_addr = begin_addr
    def __getitem__(self, i):
        "get from a given *byte* address"
        if i == None:
            return None
        try:
            i -= self.begin_addr
        except TypeError as err:
            print("can't access", i)
            raise err
        # returns the given word size value as an unsigned int (preserving 2s comp)
        return int.from_bytes(
            self.data[i: i+self.word_size],
            byteorder='big', signed=False)
    def __setitem__(self, i, val, signed=False):
        "set a word at given *byte* address"
        if type(val) == int:
            # convert to a words/bytes
            val = val.to_bytes(length=self.word_size, 
                byteorder='big', signed=signed)
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
        return addr >= self.begin_addr and addr < self.end_addr
    def to_hex(self, byteorder='big'):
        s = ["@" + format(int(self.begin_addr / self.word_size), "x")]
        
        fmt = f"0{2*self.word_size}x"    
        num = int(len(self.data) / self.word_size)
        print(fmt)
        for wordaddr in range(num):
            byteaddr = wordaddr * self.word_size
            d = int.from_bytes(self.data[byteaddr: byteaddr + self.word_size], byteorder=byteorder)    
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
                    raise NotImplemented()
                at = word_size * int (statement[1:], base=16)
                data = []
            else:
                data.append(int(statement, 16).to_bytes(word_size, byteorder))

    data = b"".join(data)
    return MemorySegment(begin_addr = at, 
        data = data, 
        word_size = word_size)
    