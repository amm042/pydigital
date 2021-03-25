from .csr_list import csrs
class BadInstruction(Exception):
    pass

# build csr lookup
csrd = {k:v for k,v in csrs}

def regNumToName(num):
    if type(num) != int or num < 0 or num > 31:
        raise BadInstruction()
    return ['zero','ra','sp','gp',  # 0..3
            'tp', 't0', 't1', 't2', # 4..7
            's0', 's1', 'a0', 'a1', # 8..11
            'a2', 'a3', 'a4', 'a5', # 12..15
            'a6', 'a7', 's2', 's3', # 16..19
            's4', 's5', 's6', 's7', # 20..23
            's8', 's9', 's10', 's11', # 24..27]
            't3', 't4', 't5', 't6'][num] # 28..31
class Instruction():
    "represents/decodes RISCV instructions"    
    def __init__ (self, val, pc, symbols = {}):
        """
        Decodes a risc-v instruction word
        val is the machine code word
        pc is the pc value used to format pc-relative assembly instructions
        symbols is an optional symbol table to decode addresses in assembly output 
        """
        self.val = val        
        self.pc = pc # pc relative instrs need pc to compute targets for display
        self.symbols = symbols
        if val == None:
            self.name = "None"
            return

        self.op = val & 0x7f

        # common fields decoded for all instructions, even if not used
        self.rd = 0x1f & (self.val >> 7)
        self.rs1 = 0x1f & (self.val >> 15)
        self.rs2 = 0x1f & (self.val >> 20)
        self.func3 = (self.val >> 12) & 0x7 
        self.func7 = 0x7f & (self.val >> 25)
        
        # decode all possible immediate values
        self.i_imm = self.sextend12(0xfff & (self.val >> 20))    
        self.s_imm = self.sextend12(0xfff & (
                    (0x1f & (self.val >> 7)) |
                    ((0x7f & (self.val >> 25)) << 5)
                ) )
        self.sb_imm = self.sextend(
            0x1fffff & (
                ((0xf  & (self.val >> 8)) << 1)   |
                ((0x3f & (self.val >> 25)) << 5 ) |
                ((0x1  & (self.val >> 7)) << 11 ) |
                ((0x80000000 & self.val) >> 19)
            ), 13)
        self.u_imm = self.sextend(0xfffff000 & self.val, 32)
        # u_imm is already 32-bits, don't have to sign extend, that would make it wrong!
        #self.u_imm = 0xfffff000 & self.val
        self.uj_imm = self.sextend(0xfffff & 
            (
                ((0x3ff & (self.val >> 21)) << 1) |
                ((0x1 & (self.val >> 20)) << 11) |
                ((0xff & (self.val >> 12)) << 12) |
                ((0x1 & (self.val >> 31)) << 20)
            ), 20)
        # special case for CSR instructions, immediate val is stored in rs1's place.
        self.z_imm = 0x1f & (self.val >> 15)
        # instruction name
        self.name = "" # to be filled in later by a decoder

        # extra flags for special instruction types
        self.is_branch = False
        self.is_jump = False
        self.is_jump_reg = False
        self.is_csr = False

        # indexed by bits 4:2 of instruction    
        self.decoders = [
            self.LOAD_STORE_BRANCH,         # 000
            self.LOADFP_STOREFP_JALR,
            None,                           # 010 custom-0
            self.MISCMEM_JAL,
            self.OP_OPIMM_SYSTEM,           # 100
            self.AUIPC_LUI,
            self.OP32_OPIMM32,              # 110
            None,                           # 111 expansion
        ]
        # https://riscv.org/wp-content/uploads/2017/05/riscv-spec-v2.2.pdf
        # page 103
   
        if self.op & 0b11 != 0b11:
            raise BadInstruction()
        decoder = self.decoders[0b111 & (self.op >> 2)] #4:2
        if decoder != None:
            decoder()
        else:
            raise BadInstruction()

    def dump(self):
        "dump all instruction details, useful for debugging"
        f = ['val', 'op', 'rd','rs1','rs2']
        s = ", ".join([f'{_n.rjust(10)}: {format(getattr(self, _n), "8x")}' for _n in f])
        f = ['func3', 'func7']
        s += '\n' + ", ".join([f'{_n.rjust(10)}: {format(getattr(self, _n), "8x")}' for _n in f])
        f = ['i_imm', 's_imm', 'sb_imm', 'u_imm', 'uj_imm', 'z_imm']
        s += '\n' + ", ".join([f'{_n.rjust(10)}: {format(getattr(self, _n), "8x")}' for _n in f])
        f = ['is_branch', 'is_jump', 'is_jump_reg', 'is_csr']
        s += '\n' + ", ".join([f'{_n.rjust(10)}: {format(getattr(self, _n), "8x")}' for _n in f])

        if self.is_csr:
            s += f'\n{"csr".rjust(10)}: {format(self.csr, "08x")} == {csrd[self.csr]}'
        return s

    def sextend(self, val, c):
        "sign extend c val to 32 bits"
        sign = 0b1 & (val >> (c-1))
        if sign == 0b1:
            mask = (1 << c) - 1
            uppermask = 0xffffffff ^ mask
            # invert plus one, after sign extension
            return - (0xffffffff - (uppermask | val) + 1) 
        else:
            # postive is unchanged
            return val        

    def sextend12(self, val):
        "12 bit sign extender"
        return self.sextend(val, 12)

    def __str__(self):
        if self.val is None:
            return "None"
        # match objdump (or spike) output
        if hasattr(self, 'asm'):
            #return f'{self.val:08x}\t{self.asm}'
            return f'{self.asm}'
        else:            
            #s = [f'{self.val:08x}\t',
            s = [\
                self.name.ljust(8),
                'NO DECODER']
            return " ".join(s)

    ######################### decoder functions begin
    def LOAD_STORE_BRANCH(self):    
        if 0b11 & (self.op >> 5) == 0b00:
            #LOAD            
            self.name = {
                0x0: 'lb',
                0x1: 'lh',
                0x2: 'lw',
                0x4: 'lbu',
                0x5: 'lhu'
            }[self.func3]
            self.asm = f"{self.name}\t{regNumToName(self.rd)},{self.i_imm}({regNumToName(self.rs1)})"

        elif 0b11 & (self.op >> 5) == 0b01:
            #STORE
            self.name = {
                0b000: 'sb',
                0b001: 'sh',
                0b010: 'sw'
            }[self.func3]
            self.asm = f"{self.name}\t{regNumToName(self.rs2)},{self.s_imm}({regNumToName(self.rs1)})"

        elif 0b11 & (self.op >> 5) == 0b10:
            #MADD
            self.name = 'madd'
            raise NotImplementedError()
        elif 0b11 & (self.op >> 5) == 0b11:
            #BRANCH
            self.is_branch = True
            self.name = [
                'beq', #000
                'bne',
                '---', #010 ?
                '---', #011 ?
                'blt', #100
                'bge', #101
                'bltu', #110
                'bgeu', #111
            ][self.func3]
            if self.name == '---':
                raise BadInstruction()
            elif self.rs1 == 0:
                # pseudo instruction   
                self.asm = f"{self.name}z\t{regNumToName(self.rs2)},pc+{self.sb_imm:x}\t({self.pc + self.sb_imm:x})"
            elif self.rs2 == 0:
                # pseudo instruction
                self.asm = f"{self.name}z\t{regNumToName(self.rs1)},pc+{self.sb_imm:x}\t({self.pc + self.sb_imm:x})"
            else:
                self.asm = f"{self.name}\t{regNumToName(self.rs1)},{regNumToName(self.rs2)},pc{self.sb_imm:+d}\t({self.pc + self.sb_imm:x})"

            if self.pc + self.sb_imm in self.symbols:
                self.asm += f' <{self.symbols[self.pc + self.sb_imm]}>'                
        else:
            raise BadInstruction()

    def LOADFP_STOREFP_JALR(self):
        #JALR instruction here
        if self.op == 0b1100111 and self.func3 == 0b000:
            self.is_jump_reg = True
            self.name = 'jalr'
            if self.rd == 0:
                if self.rs1 == 1 and self.i_imm == 0:
                    self.asm = 'ret'
                else:
                    self.asm = f'jr\t{regNumToName(self.rs1)}'
                
            else:
                self.asm = f'{self.name}\t{regNumToName(self.rd)},{regNumToName(self.rs1)}'
            if self.i_imm > 0:
                self.asm += f'\t({self.i_imm:x})'
        else:
            raise NotImplementedError() 
    def MISCMEM_JAL(self):
        if 0b11 & (self.op >> 5) == 0b11:
            # jumps
            self.is_jump = True
            self.name = 'jal'
            if self.rd == 0:
                # j pseudo instruction
                self.asm = f"j\t{(self.pc + self.uj_imm):8x}"
            else:                
                self.asm = f"{self.name}\t{regNumToName(self.rd)},{(self.pc + self.uj_imm):8x}"
            if self.pc + self.uj_imm in self.symbols:
                self.asm += f'\t<{self.symbols[self.pc + self.uj_imm]}>'
        elif self.op == 0b0001111 and self.func3 == 0b000:
            # not fully implemented/decoded
            self.name = 'fence'
            self.asm = 'fence'
        else:
            print("MISCMEM:\n" + self.dump())
            raise NotImplementedError()
    def OP_OPIMM_SYSTEM(self):
        if 0b11 & (self.op >> 5) == 0b00:          
            self.name = [
                'addi',# 0 
                'slli',
                'slti',
                'sltiu',
                'xori', # 4
                'srli',
                'ori',
                'andi', # 7
            ][self.func3]

            self.asm = f"{self.name}\t{regNumToName(self.rd)},{regNumToName(self.rs1)},{self.i_imm}"
            # special cases
            if self.name == 'addi' and self.rs1 == 0b0:
                # cosmetic, psuedo op translation                
                self.asm = f"li\t{regNumToName(self.rd)},{self.i_imm}"

            if self.func3 == 0b101:
                self.shamt = 0x1f & (self.op >> 20)
                if self.func7 == 0b0100000:
                    self.name = 'srai'
                    self.asm = f"{self.name}\t{regNumToName(self.rd)},{regNumToName(self.rs1)},0x{self.i_imm:x}"
                else:
                    # shift immediates are printed in hex
                    self.asm = f"{self.name}\t{regNumToName(self.rd)},{regNumToName(self.rs1)},0x{self.i_imm:x}"
                
            if self.func3 == 0b001:
                self.shamt = 0x1f & (self.op >> 20)
                self.asm = f"{self.name}\t{regNumToName(self.rd)},{regNumToName(self.rs1)},0x{self.i_imm:x}"

        elif 0b11 & (self.op >> 5) == 0b01:
            # opcodes: 01100xx
            self.name = [
                'add',# 0  (also sub)
                'sll',
                'slt',
                'sltu',
                'xor', # 4
                'srl', # and sra
                'or',
                'and', # 7
            ][self.func3]
            if self.func3 == 5 and self.func7 == 0b0100000:
                self.name = 'sra'
            if self.func3 == 0 and self.func7 == 0b0100000:
                self.name = 'sub'
            self.asm = f"{self.name}\t{regNumToName(self.rd)},{regNumToName(self.rs1)},{regNumToName(self.rs2)}"
            
        elif 0b11 & (self.op >> 5) == 0b10:
            self.name = 'op-fp'
            raise NotImplementedError() 
        elif 0b11 & (self.op >> 5) == 0b11:
                
            if (self.val >> 7) == 0:
                self.name = 'ecall'
                self.asm = self.name
            elif (self.val >> 7) == 0b0000000000010000000000000:
                self.name = 'ebreak'
                self.asm = self.name
            else:          
                self.csr = 0xfff & (self.val >> 20)
                self.is_csr = True
                # system opcodes are messy
                if self.csr == 0 and self.rs1 == 0 and self.func3 == 0 and self.rd == 0:
                    self.name = 'ecall'
                    self.asm = 'ecall'                    
                elif self.csr == 1 and self.rs1 == 0 and self.func3 == 0 and self.rd == 0:
                    self.name = 'ebreak' 
                    self.asm = 'ebreak'
                elif self.func3 == 0 and self.rs1 == 0 and self.rd == 0:
                    # Uret/Sret/Hret/Mret
                    if self.i_imm == 0b000000000010:
                        self.name, self.asm ='uret', 'uret'
                    elif self.i_imm == 0b000100000010:
                        self.name, self.asm ='sret', 'sret'
                    elif self.i_imm == 0b01000000010:
                        self.name, self.asm ='hret', 'hret'
                    elif self.i_imm == 0b001100000010:
                        self.name, self.asm ='mret', 'mret'
                    else:
                        raise ValueError("Unsupported instruction")
                else:
                    self.name = [
                        '---', # ecall or ebreak
                        'csrrw',
                        'csrrs',
                        'csrrc',
                        '---' # 4
                        'csrrwi',
                        'csrrsi',
                        'csrrci'
                    ][self.func3]                          
                    pname = self.name
                    # pseudo name generation
                    if self.rd == 0:
                        # drop inner r
                        pname = self.name[0:3] + self.name[4:]     
                    asm = []
                    # not pseudo op
                    if self.rd != 0:                    
                        asm += [regNumToName(self.rd)]

                    asm += [csrd[self.csr]]
                    
                    if self.name[-1] == 'i':
                        # rs1 is used as the immediate value
                        asm += [str(self.rs1)]
                    else:
                        if self.rs1 != 0:
                            asm += [regNumToName(self.rs1)]
                    self.asm = f"{pname}\t" + ",".join(asm)                                      
        else:
            raise BadInstruction()
    def AUIPC_LUI(self):                
        if self.op == 0b0110111:
            self.name = 'lui'
        elif self.op == 0b0010111:
            self.name = 'auipc'
        else:
            raise BadInstruction()
        # objdump output doesn't show trailing 12-bit of zeros for display
        # and it shows the unsigned value
        self.asm = f"{self.name}\t{regNumToName(self.rd)},0x{(0xfffff000 & self.val)>>12:05x}"

    def OP32_OPIMM32(self):
        print("OPIMM32", end="")
    ######################### decoder functions end
