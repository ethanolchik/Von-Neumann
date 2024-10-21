from queue import Queue
import time
from colorama import Fore, Style

# Constants
BIT_RESOLUTION = 20
MAX_VALUE = (2 ** BIT_RESOLUTION) - 1
RAM_SIZE = 100

instructions = {
    "LDA":      0x1,
    "STA":      0x2,
    "ADD":      0x3,
    "SUB":      0x4,
    "AND":      0x5,
    "OR":       0x6,
    "NOT":      0x7,
    "XOR":      0x8,
    "INP":      0x9,
    "OUT":      0xA,
    "HLT":      0xB
}

def to_signed(value):
    if value >= (1 << (BIT_RESOLUTION - 1)):
        value -= (1 << BIT_RESOLUTION)
    return value

def to_unsigned(value):
    if value < 0:
        value += (1 << BIT_RESOLUTION)
    return value & MAX_VALUE

def clock(cu, frequency=1.0):
    period = 1.0 / frequency
    while True:
        start_time = time.time()
        cu.fetch()
        cu.decode()
        cu.execute()
        elapsed_time = time.time() - start_time
        time.sleep(max(0, period - elapsed_time))

def prettyprint(cu):
    print(Fore.YELLOW + "PC:" + Style.RESET_ALL, cu.pc.get())
    print(Fore.YELLOW + "MAR:" + Style.RESET_ALL, cu.mar.get())
    print(Fore.YELLOW + "MDR:" + Style.RESET_ALL, cu.mdr.get())
    print(Fore.YELLOW + "CIR:" + Style.RESET_ALL, cu.cir.get())
    print(Fore.YELLOW + "ACCUMULATOR:" + Style.RESET_ALL, cu.accumulator.get())
    print(Fore.YELLOW + "RAM:" + Style.RESET_ALL)
    print(Fore.YELLOW + "Variables:" + Style.RESET_ALL)
    for key, value in cu.variables.items():
        print(Fore.CYAN + f"{key}:" + Style.RESET_ALL, cu.ram.get(value))

class Bus:
    def __init__(self):
        self.data = Queue()

    def read(self):
        return self.data.get()

    def write(self, value):
        self.data.put(value)

class Transistor:
    def __init__(self):
        self.state = 0

    def get(self):
        return self.state

    def set(self, state):
        self.state = state & 1 # either 0 or 1
    
    def __str__(self):
        return str(self.state)

    def __repr__(self):
        return str(self.state)

class Register:
    def __init__(self, name, bus):
        self.name = name
        self.data = [Transistor() for _ in range(BIT_RESOLUTION)]
        self.bus = bus

    def get(self):
        value = 0
        for i in range(BIT_RESOLUTION):
            value |= (self.data[i].get() << i)
        return to_signed(value)

    def set(self, value):
        value = to_unsigned(value)
        print(f"{Fore.GREEN}Setting {self.name} to {bin(value)}{Fore.RESET}")
        for i in range(BIT_RESOLUTION):
            self.data[i].set((value >> i) & 1)

    def read_from_bus(self):
        self.set(self.bus.read())

    def write_to_bus(self):
        self.bus.write(self.get())

class RAM:
    def __init__(self, bus):
        print(f"Initializing RAM of size {RAM_SIZE}")
        self.cells = [[Transistor() for _ in range(BIT_RESOLUTION)] for _ in range(RAM_SIZE)]
        self.bus = bus
        print(f"{Fore.GREEN}RAM of size {RAM_SIZE} initialized.{Fore.RESET}")

    def get(self, address):
        value = 0
        for i in range(BIT_RESOLUTION):
            value |= (self.cells[address][i].get() << i)
        return to_signed(value)
    
    def set(self, address, value):
        value = to_unsigned(value)
        for i in range(BIT_RESOLUTION):
            self.cells[address][i].set((value >> i) & 1)

    def read_from_bus(self):
        address = self.bus.read()
        self.bus.write(self.get(address))

    def write_to_bus(self):
        address = self.bus.read()
        value = self.bus.read()
        self.set(address, value)

class ALU:
    @staticmethod
    def add(val1, val2):
        return to_signed((to_unsigned(val1) + to_unsigned(val2)) & MAX_VALUE)

    @staticmethod
    def sub(val1, val2):
        return to_signed((to_unsigned(val1) - to_unsigned(val2)) & MAX_VALUE)

    @staticmethod
    def and_(val1, val2):
        return val1 & val2

    @staticmethod
    def or_(val1, val2):
        return val1 | val2

    @staticmethod
    def not_(val1):
        return to_signed(~to_unsigned(val1))
    
    @staticmethod
    def xor_(val1, val2):
        return val1 ^ val2

class CU:
    def __init__(self):
        self.bus = Bus()
        self.pc = Register("PC", self.bus)
        self.mar = Register("MAR", self.bus)
        self.mdr = Register("MDR", self.bus)
        self.cir = Register("CIR", self.bus)
        self.accumulator = Register("ACCUMULATOR", self.bus)
        self.ram = RAM(self.bus)
        self.alu = ALU()

        self.variables = {}
        self.next_variable_address = RAM_SIZE-1

        self.pipeline_fetch = None
        self.pipeline_decode = None

    def fetch(self):
        self.mar.set(self.pc.get())
        self.bus.write(self.mar.get())
        self.ram.read_from_bus()
        self.mdr.read_from_bus()
        self.pc.set(self.pc.get()+1)
        self.pipeline_fetch = self.mdr.get()

    def decode(self):
        if self.pipeline_fetch is not None:
            instruction = self.pipeline_fetch
            opcode = (instruction >> 16) & 0xF
            operand = instruction & 0xFFFF
            self.pipeline_decode = (opcode, operand)
            self.pipeline_fetch = None

    def execute(self):
        if self.pipeline_decode is not None:
            opcode, operand = self.pipeline_decode
            if opcode == instructions["LDA"]:
                self.bus.write(operand)
                self.ram.read_from_bus()
                self.accumulator.read_from_bus()
            elif opcode == instructions["STA"]:
                self.bus.write(operand)
                self.bus.write(self.accumulator.get())
                self.ram.write_to_bus()
            elif opcode == instructions["ADD"]:
                self.bus.write(operand)
                self.ram.read_from_bus()
                self.accumulator.set(self.alu.add(self.accumulator.get(), self.bus.read()))
            elif opcode == instructions["SUB"]:
                self.bus.write(operand)
                self.ram.read_from_bus()
                self.accumulator.set(self.alu.sub(self.accumulator.get(), self.bus.read()))
            elif opcode == instructions["AND"]:
                self.bus.write(operand)
                self.ram.read_from_bus()
                self.accumulator.set(self.alu.and_(self.accumulator.get(), self.bus.read()))
            elif opcode == instructions["OR"]:
                self.bus.write(operand)
                self.ram.read_from_bus()
                self.accumulator.set(self.alu.or_(self.accumulator.get(), self.bus.read()))
            elif opcode == instructions["NOT"]:
                self.accumulator.set(self.alu.not_(self.accumulator.get()))
            elif opcode == instructions["XOR"]:
                self.bus.write(operand)
                self.ram.read_from_bus()
                self.accumulator.set(self.alu.xor_(self.accumulator.get(), self.bus.read()))
            elif opcode == instructions["INP"]:
                self.accumulator.set(int(input()))
            elif opcode == instructions["OUT"]:
                print("OUT:", self.accumulator.get())
            elif opcode == instructions["HLT"]:
                exit("Halt")
            else:
                raise ValueError(f"Invalid opcode")
            self.pipeline_decode = None
        prettyprint(self)

def main():
    program = []
    x = ""
    cu = CU()

    while x != "end":
        x = input().split(" ")
        if x[0] == "end":
            break
    
        if x[0] == "DAT":
            cu.variables[x[1]] = cu.next_variable_address
            cu.ram.set(cu.next_variable_address, int(x[2]))
            cu.next_variable_address -= 1
        else:
            if len(x) > 1:
                if x[1].isalnum():
                    program.append(
                        (instructions[x[0]] << 16) | (cu.variables[x[1]] & 0xFFFF)
                    )
                else:
                    program.append(
                        (instructions[x[0]] << 16) | (int(x[1]) & 0xFFFF)
                    )
            else:
                program.append(
                    (instructions[x[0]] << 16)
                )

    for i in range(len(program)):
        cu.ram.set(i, program[i])
        print(f"{bin(cu.ram.get(i))}")

    clock(cu)

if __name__ == '__main__':
    main()
