// Convert UTF-8 SubRip captions to a JavaScript module for a timed scene.
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, extname } from 'node:path';

const usage = 'Usage: node captions.mjs <input.srt> <output.js|output.mjs> [--from seconds] [--to seconds] [--no-overlap] [--allow-draft]';

function excerptOptions(options) {
  const bounds = {};
  let noOverlap = false;
  let allowDraft = false;
  let i = 0;
  while (i < options.length) {
    const flag = options[i];
    if (flag === '--no-overlap') {
      noOverlap = true;
      i += 1;
      continue;
    }
    if (flag === '--allow-draft') {
      allowDraft = true;
      i += 1;
      continue;
    }
    if (flag !== '--from' && flag !== '--to') throw new Error(`Unknown option ${flag}. ${usage}`);
    if (flag in bounds) throw new Error(`Supply ${flag} only once.`);
    const value = options[i + 1];
    const seconds = Number(value);
    const milliseconds = Math.round(seconds * 1000);
    if (!/^(?:\d+(?:\.\d{1,3})?|\.\d{1,3})$/.test(value ?? '') || !Number.isSafeInteger(milliseconds)) {
      throw new Error(`${flag} requires nonnegative seconds with up to three decimal places, for example 8.5.`);
    }
    bounds[flag] = milliseconds;
    i += 2;
  }
  const from = bounds['--from'] ?? 0;
  const to = bounds['--to'] ?? Infinity;
  if (to <= from) throw new Error('--to must be later than --from. Both values refer to the original recording.');
  return { from, to, noOverlap, allowDraft };
}

function timestampMilliseconds(value, line) {
  const timestamp = /^(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})$/.exec(value);
  if (!timestamp) throw new Error(`Line ${line}: invalid timestamp ${JSON.stringify(value)}. Use HH:MM:SS,mmm.`);
  const [hours, minutes, seconds, milliseconds] = timestamp.slice(1).map(Number);
  const total = ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds;
  if (!Number.isSafeInteger(total)) throw new Error(`Line ${line}: timestamp is too large.`);
  return total;
}

function parseSrt(source) {
  const lines = source.split(/\r\n?|\n/);
  const cues = [];
  let cursor = 0;
  while (cursor < lines.length) {
    if (!lines[cursor].trim()) {
      cursor++;
      continue;
    }
    if (/^\d+$/.test(lines[cursor].trim())) cursor++;

    const line = cursor + 1;
    const range = /^(\S+)\s*-->\s*(\S+)(?:\s+[XY][12]:-?\d+)*$/.exec(lines[cursor]?.trim() ?? '');
    if (!range) throw new Error(`Line ${line}: expected a timing line such as 00:00:01,000 --> 00:00:03,000.`);
    const start = timestampMilliseconds(range[1], line);
    const end = timestampMilliseconds(range[2], line);
    if (end <= start) throw new Error(`Line ${line}: the end timestamp must be after the start.`);

    cursor++;
    const firstText = cursor;
    while (cursor < lines.length && lines[cursor].trim()) cursor++;
    if (firstText === cursor) throw new Error(`Line ${line}: add at least one line of text after the timing line.`);
    cues.push({ start, end, text: lines.slice(firstText, cursor).join('\n') });
  }
  if (!cues.length) throw new Error('No captions found. Provide a UTF-8 SRT file with timed text.');
  return cues;
}

function convert(input, output, options) {
  const { from, to, noOverlap, allowDraft } = excerptOptions(options);
  if (!['.js', '.mjs'].includes(extname(output).toLowerCase())) throw new Error('Output must end in .js or .mjs.');
  if (!allowDraft && /\.draft\.srt$/i.test(basename(input))) {
    throw new Error(`Refusing unverified machine transcript ${basename(input)}. Copy it to lyrics.srt, proofread against the real lyrics, then run captions.mjs on lyrics.srt (or pass --allow-draft for scratch previews).`);
  }

  const inputFile = statSync(input, { bigint: true });
  const outputFile = statSync(output, { bigint: true, throwIfNoEntry: false });
  if (!inputFile.isFile()) throw new Error(`Expected a plain SRT file: ${input}`);
  if (outputFile && inputFile.dev === outputFile.dev && inputFile.ino === outputFile.ino) {
    throw new Error('Choose a different output file to preserve the source SRT.');
  }

  const bytes = readFileSync(input);
  let source;
  try {
    source = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch {
    throw new Error(`${input} is not valid UTF-8. Re-save the SRT as UTF-8 and retry.`);
  }
  const parsed = parseSrt(source);
  if (!allowDraft) {
    const unedited = parsed.findIndex(({ text }) => /\(repeated,\s*check by ear\)/i.test(text));
    if (unedited >= 0) {
      throw new Error(`Cue ${unedited + 1} still contains Whisper placeholder "(repeated, check by ear)". Verify the lyric line by ear or against official lyrics before exporting.`);
    }
  }
  if (noOverlap) {
    for (let i = 1; i < parsed.length; i++) {
      if (parsed[i].start < parsed[i - 1].start) {
        throw new Error(`Cue ${i + 1} starts earlier than cue ${i} (${(parsed[i].start / 1000).toFixed(3)}s < ${(parsed[i - 1].start / 1000).toFixed(3)}s). Sort cues chronologically.`);
      }
      if (parsed[i - 1].end > parsed[i].start) {
        throw new Error(`Cue ${i} (${(parsed[i - 1].end / 1000).toFixed(3)}s) overlaps cue ${i + 1} (${(parsed[i].start / 1000).toFixed(3)}s) under --no-overlap. Trim cue ${i}'s end so single-slot MV lyrics do not mask each other.`);
      }
    }
  }
  const cues = parsed.filter(({ start, end }) => start < to && end > from).map(({ start, end, text }) => ({
    start: (Math.max(start, from) - from) / 1000,
    end: (Math.min(end, to) - from) / 1000,
    text,
  }));

  writeFileSync(output, `// Timed captions in seconds. Generated by video-craft/kit/captions.mjs.\nexport default ${JSON.stringify(cues, null, 2)};\n`);
  console.log(`${cues.length} of ${parsed.length} cues → ${output}`);
}

const args = process.argv.slice(2);
try {
  if (args.length === 1 && ['--help', '-h'].includes(args[0])) {
    console.log(usage);
  } else {
    const [input, output, ...options] = args;
    if (!input || !output) throw new Error(usage);
    convert(input, output, options);
  }
} catch (error) {
  console.error(`captions: ${error.message}`);
  process.exitCode = 1;
}
