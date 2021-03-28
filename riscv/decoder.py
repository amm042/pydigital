"""
When run with construct, this generates the control table from the 
riscv sodor collection. Copy-paste the output into the exported table
to udpate.

To use, import this file and use the *control* dictionary.
Each instruction (lowercase) has all control signals defined. 
For each signal, look at *enums* this defines the enum value corresponding 
to each integer value in the object (it may not match the sodor docs).

For example,
control["add"] has the following fields:
val_inst = 1
br_type = 0
op1_sel = 0
op2_sel = 0
ALU_fun = 5
wb_sel = 1
rf_wen = 1
mem_em = 0
mem_wr = 0
mask_type = 0
csr_cmd = 3

If you convert the control to a string it replaces the values 
with its enum name eg, print(str(decoder.control['add'])) returns:
val_inst:Y         
br_type:BR_N      
op1_sel:OP1_RS1   
op2_sel:OP2_RS2   
ALU_fun:ALU_ADD    
wb_sel:WB_ALU     
rf_wen:REN_1      
mem_em:MEN_0      
mem_wr:M_XRD    
mask_type:MT_H     
csr_cmd:CSR.N
"""

# this is the raw compressed control table using the edited enums
_c = """Inst    val_inst,br_type,op1_sel,op2_sel,ALU_fun,wb_sel,rf_wen,mem_em,mem_wr,mask_type,csr_cmd
ADD	10005110043
ADDI	10015110043
AND	10004110043
ANDI	10014110043
AUIPC	10235110043
BEQ	18000000043
BGE	15000000043
BGEU	12000000043
BLT	13000000043
BLTU	17000000043
BNE	14000000043
CSRRC	10002310040
CSRRCI	10102310040
CSRRS	10002310044
CSRRSI	10102310044
CSRRW	10002310041
CSRRWI	10102310041
DRET	10000000042
EBREAK	10000000042
ECALL	10000000042
FENCE	10000000043
FENCE_I	10000000043
JAL	16000010043
JALR	11010010043
LB	10015211013
LBU	10015211013
LH	10015211023
LHU	10015211023
LUI	10202110043
LW	10015211043
MRET	10000000042
OR	1000b110043
ORI	1001b110043
SB	10025001113
SH	10025001123
SLL	1000a110043
SLLI	1001a110043
SLT	10006110043
SLTI	10016110043
SLTIU	10013110043
SLTU	10003110043
SRA	10007110043
SRAI	10017110043
SRL	10009110043
SRLI	10019110043
SUB	10008110043
SW	10025001143
WFI	10000000043
XOR	10001110043
XORI	10011110043"""

class IControl:
    "instruction control helper class, decodes one compressed line of control signals"
    def __init__(self, fields, cstr, renums):
        self.fields = fields        
        self.renums = renums 
        for field,ch in zip(fields,cstr):
            setattr(self, field, int(ch, base=16))
    def __repr__(self):
        return "".join(["{:x}".format(getattr(self,i)) for i in self.fields])
    def __str__(self): 
        return " ".join(["{}:{:8}".format(i.rjust(8), self.renums[i][getattr(self,i)]) for i in self.fields])
def make_control_table(enums=None):
    "used to generate the control table from the ucb scala source"
    req = requests.get('https://raw.githubusercontent.com/ucb-bar/riscv-sodor/master/src/main/scala/rv32_1stage/cpath.scala')
    t = {}
    r = re.compile("([\\w\\d\\.]+)[,\\t\\s\\d]*")

    # fields in the order of the source code
    fields = ["val_inst", "br_type", "op1_sel", "op2_sel", "ALU_fun", "wb_sel", "rf_wen", "mem_em", "mem_wr", "mask_type", "csr_cmd"]
    
    in_arr = False
    if enums == None:
        # keep a list of all string vals for each field
        field_vals = {f: set() for f in fields}
        # insert invalid inst value at begining so it gets enum val of 0
        field_vals['val_inst'].add('N')
        field_vals['val_inst'].add('Y')
    for line in req.text.split('\n'):
        if line == '': #skip blanks
            continue
        # LW is the first instruction currently, but should be manually checked
        if line.strip().split()[0] == "LW":
            in_arr = True # continue so we process the first line
        if in_arr:
            parts = r.findall(line)      
            vals = tuple(zip(fields, parts[2:]))            
            if enums==None:
                for f,val in vals:            
                    field_vals[f].add(val)
            t[parts[0]] = dict(vals)       
                        
            # FENCE is the last instruction currently, but should be manually checked
            if parts[0] == 'FENCE':
                in_arr = False
                break # all done
    
    if enums == None:
        field_enums = {}    
        for f, s in field_vals.items():
            # enumerate returns #, val, we want val, #, have to reverse each eunumerate obj.
            e = tuple(map(reversed,enumerate(s)))
            field_enums[f] = dict(e)
           
        return t, field_enums
    else:
        return t, enums

# minor mods by hand for 0/1 and X vals. 
# set to None to regenerate
enums = {
		"val_inst": {
			"N": 0,
			"Y": 1
		},
		"br_type": {
			"BR_N": 0,
			"BR_JR": 1,
			"BR_GEU": 2,
			"BR_LT": 3,
			"BR_NE": 4,
			"BR_GE": 5,
			"BR_J": 6,
			"BR_LTU": 7,
			"BR_EQ": 8
		},
		"op1_sel": {
			"OP1_X": 0,
            "OP1_RS1": 0,			
			"OP1_IMZ": 1,
			"OP1_IMU": 2
		},
		"op2_sel": {
            "OP2_X": 0,
			"OP2_RS2": 0,
            "OP2_IMI": 1,            
			"OP2_IMS": 2,			
			"OP2_PC": 3,			
		},
		"ALU_fun": {
			"ALU_X": 0,
            "ALU_XOR": 1,
			"ALU_COPY1": 2,
			"ALU_SLTU": 3,
			"ALU_AND": 4,
			"ALU_ADD": 5,
			"ALU_SLT": 6,
			"ALU_SRA": 7,
			"ALU_SUB": 8,
			"ALU_SRL": 9,
			"ALU_SLL": 10,
			"ALU_OR": 11
		},
		"wb_sel": {
			"WB_X": 0,
            "WB_PC4": 0,
            "WB_ALU": 1,
            "WB_MEM": 2,
            "WB_CSR": 3
		},
		"rf_wen": {
			"REN_0": 0,
            "REN_1": 1			
		},
		"mem_em": {
			"MEN_0": 0,
			"MEN_1": 1
		},
		"mem_wr": {
			"M_X": 0,
            "M_XRD": 0,			
			"M_XWR": 1
		},
		"mask_type": {
			"MT_X": 4,
            "MT_H": 2,			
			"MT_HU": 2,
			"MT_BU": 1,
			"MT_B": 1,
			"MT_W": 4
		},
		"csr_cmd": {
			"CSR.C": 0,
			"CSR.W": 1,
			"CSR.I": 2,
			"CSR.N": 3,
			"CSR.S": 4  # read and set bits
		}
	}


def compact(tab, enums):
    "a more compact representation"
    fields = enums.keys()
    s = []
    for inst, signals in tab.items():
        k = inst + '\t'
        for sname in fields:
            k+= f'{enums[sname][signals[sname]]:x}'
        s += [k]
    return "\n".join(['Inst\t' + ','.join(fields)] + sorted(s))


construct = False
if construct:
    import re
    import requests    
    #from pprint import pprint
    import json
    print(compact(*make_control_table(enums=enums)))
    #print(json.dumps(make_control_table(), sort_keys=False, indent='\t'))
else:  
    fields = None
    control = {}
    # reverse enum lookup
    renum = {field:{v:k for k,v in lut.items()} for field,lut in enums.items()}
    for line in _c.split("\n"):

        instr, ctrl = line.split()

        if fields == None: # first line is fields
            fields = ctrl.split(',')
        else:
            control[instr.lower()] = IControl(fields, ctrl, renum)
