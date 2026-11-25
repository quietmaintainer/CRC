"""Regrow-8's eight-instruction CPU with external program ROM and data RAM."""

from enum import IntEnum

import pyrtl
from pyrtl.rtllib.adders import ripple_add


class Op(IntEnum):
    LDI = 0
    ADDI = 1
    SUBI = 2
    XORI = 3
    STA = 4
    BZ = 5
    JMP = 6
    NOP = 7


operand = pyrtl.Input(8, "i")
opcode = pyrtl.Input(3, "op")
reset = pyrtl.Input(1, "rst")

accumulator = pyrtl.Register(8, "accumulator")
program_counter = pyrtl.Register(2, "program_counter")

# ADDI and SUBI share one adder. SUBI complements the operand and adds one.
subtract = opcode == Op.SUBI
run = ~reset
arithmetic = ripple_add(accumulator, operand ^ subtract.sign_extended(8), subtract)[:8]


def when(condition, value):
    return value & (run & condition).sign_extended(len(value))


# These opcode cases are disjoint. Reset disables every source for the next value.
accumulator.next <<= (
    when(opcode == Op.LDI, operand)
    | when((opcode == Op.ADDI) | subtract, arithmetic)
    | when(opcode == Op.XORI, accumulator ^ operand)
    | when(opcode[2], accumulator)
)

branch = (opcode == Op.JMP) | ((opcode == Op.BZ) & (accumulator == 0))
next_pc = pyrtl.select(branch, operand[:2], (program_counter + 1)[:2])
program_counter.next <<= next_pc & run.sign_extended(2)

# Match the demo's physical pin order, including the interleaved addresses.
write_enable = pyrtl.Output(1, "we")
data = pyrtl.Output(8, "data")
write_enable <<= (opcode == Op.STA) & run
data <<= accumulator

for bit in range(2):
    pc_pin = pyrtl.Output(1, f"pc{bit}")
    addr_pin = pyrtl.Output(1, f"addr{bit}")
    pc_pin <<= program_counter[bit]
    addr_pin <<= operand[bit]
