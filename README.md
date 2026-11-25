# Circuit Recipe Compiler

CRC compiles a circuit written in [PyRTL](https://pyrtl.readthedocs.io/) to a plain-text recipe for [Regrow-8](https://github.com/quietmaintainer/Regrow-8). PyRTL describes what the circuit computes. CRC turns that design into pins, logic gates, and flip-flops. Regrow-8 reads the recipe and handles placement, routing, and repair.

## Generate the 8-bit CPU

Use Python 3.10 or later. From the CRC repository, run the following commands in your Python environment.

```sh
python -m pip install .
crc examples/regrow8_cpu.py -o recipes/cpu.txt
```

The [PyRTL CPU design](examples/regrow8_cpu.py) specifies the accumulator, program counter, and eight instructions. ADDI and SUBI share an adder. Regrow-8 supplies the instruction ROM and data RAM through the CPU's pins. The [generated recipe](recipes/cpu.txt) uses the demo's pin names and order.

## Write your own circuit

Save a regular PyRTL design as `inverter.py`.

```python
import pyrtl

a = pyrtl.Input(1, "a")
y = pyrtl.Output(1, "y")
y <<= ~a
```

Run `crc inverter.py -o inverter.txt`. CRC executes the Python file to elaborate its PyRTL circuit. You can also call `compile_block(pyrtl.working_block())` from `circuit_recipe_compiler` to get the recipe as a string.

- Declare at least one input and one output. CRC preserves port order and numbers vector pins from the least significant bit, so an 8-bit port named `data` becomes `data0` through `data7`.
- Pin names follow Regrow-8's identifier rules. CRC replaces unsupported characters with underscores and reports collisions after renaming or splitting a port.
- Regrow-8 flip-flops power up at zero. Use a reset input to set other state values. Connect ROM and RAM through pins, as in the CPU example.

## Verify the generated CPU

Run the compiler tests, then point the integration test at a local Regrow-8 checkout. The integration test uses Node.js 22 or later.

```sh
python -m unittest discover -s tests
node tests/verify_regrow8.mjs ../Regrow-8
```

The integration test checks 2,097,152 CPU transitions and a 16-edge ROM/RAM program on clean fabric and after 15% permanent crater and scattered damage. It also grows the recipe in the browser demo's runtime, applies the demo's repeatable permanent fault sample, and checks the repaired CPU. When damage destroys a flip-flop, the demo restarts its registers.

To check another recipe's placement, routing, and timing, run `node ../Regrow-8/examples/machine_recipe/chip.mjs check circuit path/to/recipe.txt`.
