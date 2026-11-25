import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [checkout] = process.argv.slice(2);
if (!checkout) throw Error('Usage: node tests/verify_regrow8.mjs <Regrow-8 checkout>');

const fromRegrow8 = path => import(pathToFileURL(resolve(checkout, path)));
const [
  { ComputerRecipe },
  { Fabric, machine },
  { grow },
  { mask },
  { pinout, verifyCpu },
] = await Promise.all([
  fromRegrow8('web/computer-recipe.mjs'),
  fromRegrow8('examples/machine_recipe/fabric.mjs'),
  fromRegrow8('examples/machine_recipe/grow.mjs'),
  fromRegrow8('examples/machine_recipe/damage.mjs'),
  fromRegrow8('examples/machine_recipe/verify.mjs'),
]);
const recipe = readFileSync(new URL('../recipes/cpu.txt', import.meta.url), 'utf8');
const seed = 20261125;
const { inputs, outputs } = pinout('cpu');

function check(label, chip) {
  const { vectors, programEdges } = verifyCpu(chip);
  assert.equal(vectors, 2_097_152);
  assert.equal(programEdges, 16);
  console.log(`${label}: ${vectors} CPU transitions and ${programEdges} ROM/RAM program edges`);
}

for (const shape of [null, 'crater', 'scatter']) {
  const board = new Fabric(64, inputs, outputs);
  grow(board, recipe);
  if (shape) {
    const dead = mask(board, shape, 15, seed);
    board.damage(dead, true);
    assert(grow(board, recipe).stats.gatesPlaced > 0);
  }
  check(shape ? `15% ${shape} repair` : 'Clean fabric', machine(board));
}

function advanceTo(computer, edge) {
  for (let ticks = 0; ticks < 128 && computer.edges < edge; ticks++) {
    computer.advance(1);
    assert.equal(computer.failure, undefined);
  }
  assert.equal(computer.edges, edge);
}

const demo = new ComputerRecipe(recipe, 'cpu');
advanceTo(demo, 16);
assert.deepEqual(demo.ram, [5, 0, 0, 0]);
demo.damage({ sample: true });
advanceTo(demo, 35);
assert.equal(demo.stats.repaired, true);
assert(demo.ram[0] > 5);
check('Browser runtime after its permanent fault sample', demo.chip);
