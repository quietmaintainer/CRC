from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pyrtl

from circuit_recipe_compiler import RecipeError, compile_block


ROOT = Path(__file__).resolve().parents[1]


class CompilerTests(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.addCleanup(pyrtl.reset_working_block)

    def test_bus_order_and_wiring(self):
        data = pyrtl.Input(3, "data")
        enable = pyrtl.Input(1, "enable")
        out = pyrtl.Output(3, "out")
        ready = pyrtl.Output(1, "ready")
        out <<= pyrtl.concat(data[0], data[1], data[2])
        ready <<= enable

        block = pyrtl.working_block()
        original_logic = block.logic.copy()
        recipe = compile_block(block)
        self.assertEqual(
            recipe.splitlines()[1:],
            [
                "inputs data0 data1 data2 enable",
                "",
                "output out0 data2",
                "output out1 data1",
                "output out2 data0",
                "output ready enable",
            ],
        )
        self.assertIs(pyrtl.working_block(), block)
        self.assertEqual(block.logic, original_logic)

    def test_register_feedback_and_constant(self):
        enable = pyrtl.Input(1, "enable")
        state = pyrtl.Register(1, "state")
        q = pyrtl.Output(1, "q")
        fixed = pyrtl.Output(1, "fixed")
        state.next <<= state ^ enable
        q <<= state
        fixed <<= 1

        recipe = compile_block(pyrtl.working_block())
        self.assertIn("gate g1 XOR enable enable", recipe)
        self.assertIn("gate g2 NOT g1", recipe)
        self.assertIn("gate g0 DFF g3", recipe)
        self.assertIn("gate g3 XOR g0 enable", recipe)
        self.assertIn("output q g0", recipe)
        self.assertIn("output fixed g2", recipe)

    def test_rejects_memory_blocks(self):
        address = pyrtl.Input(1, "address")
        out = pyrtl.Output(1, "out")
        rom = pyrtl.RomBlock(bitwidth=1, addrwidth=1, romdata=[1, 0])
        out <<= rom[address]

        with self.assertRaisesRegex(RecipeError, "external ROM/RAM"):
            compile_block(pyrtl.working_block())

    def test_rejects_nonzero_register_initial_value(self):
        data = pyrtl.Input(1, "data")
        q = pyrtl.Output(1, "q")
        state = pyrtl.Register(1, "state", reset_value=1)
        state.next <<= data
        q <<= state

        with self.assertRaisesRegex(RecipeError, "nonzero initial value"):
            compile_block(pyrtl.working_block())

    def test_rejects_pin_collision(self):
        data = pyrtl.Input(2, "data")
        first_bit = pyrtl.Input(1, "data0")
        out = pyrtl.Output(1, "out")
        out <<= data[0] ^ first_bit

        with self.assertRaisesRegex(RecipeError, "duplicate recipe pin 'data0'"):
            compile_block(pyrtl.working_block())

    def test_cli_runs_design_with_local_import(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "helper.py").write_text(
                "def invert(signal):\n    return ~signal\n", encoding="utf-8"
            )
            design = folder / "inverter.py"
            design.write_text(
                "import pyrtl\n"
                "from helper import invert\n"
                "if __name__ == '__main__':\n"
                "    a = pyrtl.Input(1, 'a')\n"
                "    y = pyrtl.Output(1, 'y')\n"
                "    y <<= invert(a)\n",
                encoding="utf-8",
            )
            output = folder / "inverter.txt"
            self.run_compiler(design, output)
            self.assertIn("gate g0 NOT a\n", output.read_text(encoding="utf-8"))

    def test_cli_reproduces_cpu_recipe(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "cpu.txt"
            self.run_compiler(ROOT / "examples" / "regrow8_cpu.py", output)
            self.assertEqual(output.read_bytes(), (ROOT / "recipes" / "cpu.txt").read_bytes())

    def run_compiler(self, design, output):
        result = subprocess.run(
            [sys.executable, "-m", "circuit_recipe_compiler", str(design), "-o", str(output)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
