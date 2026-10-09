// Exercise the real CLI, with pg and all external actions blocked by a preload.
const { test, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'reconcile-args-'));
after(() => fs.rmSync(temp, { recursive: true, force: true }));
const preload = path.join(temp, 'offline.cjs');
fs.writeFileSync(preload, `
const Module = require('node:module');
const original = Module._load;
Module._load = function(name, parent, main) {
  if (name === 'pg') return { Client: class {
    constructor() { throw new Error('TEST_EXTERNAL_ACCESS_BLOCKED'); }
  }};
  return original.call(this, name, parent, main);
};
require('node:child_process').execFileSync = () => { throw new Error('TEST_EXTERNAL_ACCESS_BLOCKED'); };
global.fetch = () => { throw new Error('TEST_EXTERNAL_ACCESS_BLOCKED'); };
`);
const script = path.resolve(__dirname, '..', 'reconcile-indexer.js');
function run(args) {
  return spawnSync(process.execPath, ['--require', preload, script, ...args], {
    cwd: temp, env: { PATH: process.env.PATH }, encoding: 'utf8', timeout: 5000,
  });
}
for (const args of [
  ['--sample', 'abc'], ['--sample=abc'], ['--sample'], ['--sample='],
  ['--sample', '0'], ['--sample', '-1'], ['--sample', '1.5'],
  ['--sample', 'NaN'], ['--sample', 'Infinity'], ['--sample', '9007199254740992'],
  ['--sample', '--json'], ['--sample', ' '],
  ['--tables'], ['--tables='], ['--tables', ''], ['--tables', ' '],
  ['--tables', '--json'], ['--tables', 'players,'], ['--tables', ',players'],
  ['--tables', 'unknown'], ['--tables=players,,scouts'],
]) {
  test(`invalid arguments ${JSON.stringify(args)} fail before configuration or I/O`, () => {
    const result = run(args);
    assert.ifError(result.error);
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Configuration error:/);
    assert.ok(result.stderr.includes(args[0].split('=')[0]));
    assert.doesNotMatch(result.stderr, /TypeError|TEST_EXTERNAL_ACCESS_BLOCKED|Missing required/);
    assert.equal(result.stdout, '');
  });
}
for (const args of [
  [], ['--sample', '1'], ['--sample=25'], ['--sample', '9007199254740991'],
  ['--tables', 'players, scouts'], ['--tables=indexer_cursor'],
  ['--sample', '2', '--tables', 'players', '--json'],
]) {
  test(`valid arguments ${JSON.stringify(args)} reach the existing environment gate`, () => {
    const result = run(args);
    assert.ifError(result.error);
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Missing required environment variable/);
    assert.doesNotMatch(result.stderr, /TEST_EXTERNAL_ACCESS_BLOCKED/);
    assert.equal(result.stdout, '');
  });
}
