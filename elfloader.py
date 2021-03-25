"""
elfloader.py
------------
A wrapper for pyelftools https://github.com/eliben/pyelftools
"""

from elftools.elf.elffile import ELFFile
from elftools.elf.enums import *
from elftools.elf.sections import SymbolTableSection
import elftools.elf.constants as elfconst

from .memory import ELFMemory, MemorySegment

class Elf():
    """
    Simplified ELF wrapper class, use with a context manager as:
    with Elf('elffile') as foo:
        ...
    """
    def __init__(self, elffilename, quiet = False):
        self.elffilename = elffilename
        self.quiet = quiet
    def __enter__(self):
        self.f = open(self.elffilename, 'rb')
        self.ef = ELFFile(self.f)
        self.byteorder = "little" if self.ef.little_endian else "big"

        if not self.quiet:
            print(f"Loading ELF binary \"{self.elffilename}\".")
            print(f'{self.ef.get_machine_arch()} {self.byteorder} endian {self.ef["e_ident"]["EI_CLASS"]} has {self.ef.num_segments()} segments')
        
        if self.ef['e_ident']['EI_CLASS'] == 'ELFCLASS64':
            self.bytes_per_word = 8
        elif self.ef['e_ident']['EI_CLASS'] == 'ELFCLASS32':
            self.bytes_per_word = 4
        else:
            raise ValueError(f"Unsupported word size: {self.ef['e_ident']['EI_CLASS'] }")

        self.symtab = self.ef.get_section_by_name('.symtab')
        # build a symbol lookup map forward and reverse
        self.symbol_map = {sym.entry["st_value"]:sym.name for sym in self.symtab.iter_symbols()}
        self.symbol_map.update({sym.name:sym.entry["st_value"] for sym in self.symtab.iter_symbols()})
        
        return self
    def entry_point(self):
        return self.ef["e_entry"]

    def segments(self):
        if not self.quiet:
            print( '  --- SEGMENTS ---')
        for idx, segment in enumerate(self.ef.iter_segments()):
            d = segment.data()
            if not self.quiet:
                print(f'    {idx}: {segment["p_type"].ljust(8)} '
                    f'@{segment["p_vaddr"]:08x} '
                    f'size = {segment["p_memsz"]:4x}, '
                    f'data = {len(d):4x}')
            yield segment["p_vaddr"], segment["p_memsz"], d

    def sections(self):
        # print( '  --- SECTIONS ---')
        for idx, section in enumerate(self.ef.iter_sections()):
            # print(f'    {idx}: {section.name} {section["sh_type"]}',
            #         hex(section["sh_addr"]), 
            #         hex(section["sh_offset"]),
            #         hex(section["sh_size"]))
            yield section["sh_addr"], section["sh_size"], section.data()
            
    def __exit__(self, *args):
        self.f.close()

def load_elf(elffile, stack_size = 64 * 2**10, quiet = False):
    "this loads an elf file into memory segments for simulation"
    # initialize memories as a unified memory (instruction + data)
    sys_mem = ELFMemory()
    # TODO this should read the word size from the file, now it assumes 32 bit.
    with Elf(elffile, quiet=quiet) as e:
        for addr, size, data in e.segments():
            if len(data) == 0:
                # non initalized segments need to be allocated
                data = bytearray(size)
            elif len(data) < size:
                # bss segments are in size but not data
                # need to zero initialize this memory.
                data = bytearray(data) + bytearray(size-len(data))

            ms = MemorySegment(
                begin_addr = addr,
                data = data,
                byteorder = e.byteorder,
                word_size = 4)

            # add the segment to system memory
            sys_mem += ms

        symbols = e.symbol_map    
    # allocate stack immediately at the end of the elf segments
    # this is how the UCB linker script expects memory 
    sys_mem += MemorySegment(
        begin_addr = sys_mem.end_addr(),
        count = stack_size,
        byteorder = sys_mem.byteorder,
        word_size = 4)
    if not quiet:
        print(f"Created system memory in range {sys_mem.begin_addr():08x}:{sys_mem.end_addr():08x}")                
        print( "Segments:\n" + str(sys_mem))
        print(f"Total allocated system memory is {len(sys_mem) / 1024:4.1f} kilobytes.")
        print("-"*60)


    return sys_mem, symbols