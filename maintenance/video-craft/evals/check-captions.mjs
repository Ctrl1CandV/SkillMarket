// End-to-end regression for the public SRT caption converter.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, rmdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const cli = fileURLToPath(new URL('../../../video-craft/kit/captions.mjs', import.meta.url));
const dir = mkdtempSync(join(tmpdir(), 'vc captions-'));
const source = join(dir, '台词 #1.srt');
const output = join(dir, 'captions.mjs');
const browserOutput = join(dir, 'captions.js');
const fixture = '\uFEFF' + [
  '1', '00:00:07,000 --> 00:00:08,500', 'Ends at in-point', '',
  '2', '00:00:07,200 --> 00:00:09,000', '雾沿着屋檐落下来', 'Mist falls along the eaves', '',
  '3', '00:00:08.750 --> 00:00:12.500 X1:0 X2:80 Y1:20 Y2:40', '<i>街灯</i>', 'The streetlights', '',
  '00:00:12,000 --> 00:00:13,250', 'Starts at out-point',
].join('\r\n');
const cues = [
  { start: 7, end: 8.5, text: 'Ends at in-point' },
  { start: 7.2, end: 9, text: '雾沿着屋檐落下来\nMist falls along the eaves' },
  { start: 8.75, end: 12.5, text: '<i>街灯</i>\nThe streetlights' },
  { start: 12, end: 13.25, text: 'Starts at out-point' },
];
const run = (...args) => spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', windowsHide: true });
const success = (target, ...options) => {
  const result = run(source, target, ...options);
  assert.equal(result.status, 0, result.stderr);
  return result.stdout;
};
const failure = (expected, ...args) => {
  const result = run(...args);
  assert.equal(result.status, 1);
  assert.match(result.stderr, expected);
};

try {
  writeFileSync(source, fixture, 'utf8');
  assert.match(success(output), /4 of 4 cues/);
  assert.deepEqual((await import(pathToFileURL(output).href)).default, cues);

  assert.match(success(output, '--from', '8.5', '--to', '12'), /2 of 4 cues/);
  const excerpt = new URL(pathToFileURL(output));
  excerpt.search = 'excerpt';
  assert.deepEqual((await import(excerpt.href)).default, [
    { ...cues[1], start: 0, end: 0.5 },
    { ...cues[2], start: 0.25, end: 3.5 },
  ]);

  assert.match(success(browserOutput, '--from', '30'), /0 of 4 cues/);
  assert.match(readFileSync(browserOutput, 'utf8'), /export default \[\];/);
  assert.match(success(browserOutput, '--to', '8.501'), /2 of 4 cues/);
  failure(/--to must be later than --from/, source, output, '--from', '8.5', '--to', '8.5');
  failure(/--from requires nonnegative seconds/, source, output, '--from', '-1');
  failure(/Unknown option --timing/, source, output, '--timing', '1');

  const previous = readFileSync(output);
  writeFileSync(source, '1\n00:61:03,000 --> 00:00:05,000\nBad minutes', 'utf8');
  failure(/Line 2: invalid timestamp/, source, output);
  writeFileSync(source, '1\n00:00:03,000 --> 00:00:03,000\nNo duration', 'utf8');
  failure(/Line 2: the end timestamp must be after/, source, output);
  writeFileSync(source, '1\n00:00:03,000 --> 00:00:04,000\n', 'utf8');
  failure(/Line 2: add at least one line/, source, output);
  writeFileSync(source, Buffer.from([0xff, 0xfe, 0x1]));
  failure(/not valid UTF-8/, source, output);
  failure(/Choose a different output/, output, output);
  assert.deepEqual(readFileSync(output), previous);

  console.log('PASS: UTF-8 SRT, bilingual lines, overlapping cues, clip boundaries, JS import, input errors and output preservation');
} finally {
  for (const file of [source, output, browserOutput]) rmSync(file, { force: true });
  rmdirSync(dir);
}
