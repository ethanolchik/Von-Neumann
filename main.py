# TODO: Add buses

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
    def __init__(self, name):
        # [0,1,0,0,1,0,0,1]
        self.name = name
        self.data = [Transistor() for _ in range(BIT_RESOLUTION)]

    def get(self):
        value = 0
        for i in range(BIT_RESOLUTION):
            # [0,1,0,0,1,0,0,1]
            # value | 0
            # value | 1 << 1 == value | 10
            value |= (self.data[i].get() << i)
        return value

    def set(self, value):
        print(f"Setting {self.name} to {bin(value)}")
        for i in range(BIT_RESOLUTION):
            self.data[i].set((value >> i) & 1)


class RAM:
    def __init__(self):
        print(f"Initializing RAM of size {RAM_SIZE}")
        self.cells = [[Transistor() for _ in range(BIT_RESOLUTION)] for _ in range(RAM_SIZE)]
        print(f"RAM of size {RAM_SIZE} initialized.")

    def get(self, address):
        value = 0
        for i in range(BIT_RESOLUTION):
            value |= (self.cells[address][i].get() << i)
        return value
    
    def set(self, address, value):
        for i in range(BIT_RESOLUTION):
            self.cells[address][i].set((value >> i) & 1)


class ALU:
    @staticmethod
    def add(val1, val2):
        return (val1 + val2) & MAX_VALUE

    @staticmethod
    def sub(val1, val2):
        return (val1 - val2) & MAX_VALUE

    @staticmethod
    def and_(val1, val2):
        return val1 & val2

    @staticmethod
    def or_(val1, val2):
        return val1 | val2

    @staticmethod
    def not_(val1):
        return ~val1
    
    @staticmethod
    def xor_(val1, val2):
        return val1 ^ val2

class CU:
    def __init__(self):
        self.pc = Register("PC")
        self.mar = Register("MAR")
        self.mdr = Register("MDR")
        self.cir = Register("CIR")
        self.accumulator = Register("ACCUMULATOR")
        self.ram = RAM()
        self.alu = ALU()

        self.variables = {}
        self.next_variable_address = RAM_SIZE-1

    def fetch(self):
        self.mar.set(self.pc.get())
        self.mdr.set(self.ram.get(self.mar.get()))
        self.pc.set(self.pc.get()+1)
        self.cir.set(self.mdr.get())

    def decode_execute(self):
        # 4 bit opcode + 16 bit operand
        # 0101 0101 0101 0101 0101
        # 0000 1111 1111 1111 1111
        #      0101 0101 0101 0101
        instruction = self.cir.get()
        opcode = (instruction >> 16) & 0xF
        operand = instruction & 0xFFFF

        if opcode == instructions["LDA"]:
            self.accumulator.set(self.ram.get(operand))
        elif opcode == instructions["STA"]:
            self.ram.set(operand, self.accumulator.get())
        elif opcode == instructions["ADD"]:
            self.accumulator.set(self.alu.add(self.accumulator.get(), self.ram.get(operand)))
        elif opcode == instructions["SUB"]:
            self.accumulator.set(self.alu.sub(self.accumulator.get(), self.ram.get(operand)))
        elif opcode == instructions["AND"]:
            self.accumulator.set(self.alu.and_(self.accumulator.get(), self.ram.get(operand)))
        elif opcode == instructions["OR"]:
            self.accumulator.set(self.alu.or_(self.accumulator.get(), self.ram.get(operand)))
        elif opcode == instructions["NOT"]:
            self.accumulator.set(self.alu.not_(self.accumulator.get()))
        elif opcode == instructions["XOR"]:
            self.accumulator.set(self.alu.xor_(self.accumulator.get(), self.ram.get(operand)))
        elif opcode == instructions["INP"]:
            self.accumulator.set(int(input()))
        elif opcode == instructions["OUT"]:
            print("OUT:", self.accumulator.get())
        elif opcode == instructions["HLT"]:
            exit("Halt")
        else:
            raise ValueError(f"Invalid opcode")

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

    while True:
        ram = open("ram.txt", "w")
        for c in cu.ram.cells:
            for t in c:
                ram.write(str(t))
            ram.write("\n")
        ram.close()
        print(f"PC:\t\t{bin(cu.pc.get())}")
        print(f"MAR:\t\t{bin(cu.mar.get())}")
        print(f"MDR:\t\t{bin(cu.mdr.get())}")
        print(f"CIR:\t\t{bin(cu.cir.get())}")
        print(f"Accumulator:\t{bin(cu.accumulator.get())}\n")

        cu.fetch() 
        cu.decode_execute()

if __name__ == '__main__':
    main()
