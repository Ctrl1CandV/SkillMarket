// Make a separate campaign input from the original showtime and minutes of advance.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const usage = '用法：node retime.mjs 原开场HH:MM 提前分钟数 输出文件.json\n例：node retime.mjs 20:20 10 out/spot.json';
const digits = '零一二三四五六七八九';
function chinese(n) {
  if (n < 10) return digits[n];
  const tens = Math.floor(n / 10), ones = n % 10;
  return (tens === 1 ? '' : digits[tens]) + '十' + (ones ? digits[ones] : '');
}
function clock(minutes) {
  return [Math.floor(minutes / 60), minutes % 60].map(n => String(n).padStart(2, '0')).join(':');
}
function durationCopy(minutes) {
  const h = Math.floor(minutes / 60), m = minutes % 60;
  if (!h) return { title: chinese(m) + '分', speech: chinese(m) + '分钟' };
  const hours = h === 2 ? '两' : chinese(h);
  return {
    title: hours + '小时' + (m ? chinese(m) + '分' : ''),
    speech: hours + '个小时' + (m ? chinese(m) + '分钟' : '')
  };
}
function posterTime(hour, minute) {
  const h = chinese(hour % 12 || 12);
  if (minute === 0) return h + '点整';
  if (minute === 30) return h + '点半';
  return h + '点' + (minute < 10 ? '零' : '') + chinese(minute);
}
function retime([original, advanceArg, output, ...extra]) {
  if (!original || !advanceArg || !output || extra.length) throw new Error(usage);
  const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(original);
  if (!match) throw new Error('原开场时间请用 24 小时制 HH:MM，例如 20:20。');
  const advance = Number(advanceArg);
  if (!/^\d+$/.test(advanceArg) || !Number.isSafeInteger(advance) || advance < 1 || advance > 1439) {
    throw new Error('提前量应是 1 至 1439 的整数分钟数。');
  }
  const hour = Number(match[1]), minute = Number(match[2]);
  const changed = hour * 60 + minute - advance;
  if (changed < 0) {
    throw new Error('新开场会落在前一天 ' + clock(changed + 1440) + '。本广告只展示同一天的改期；请选同一天的两次开场。');
  }
  const data = JSON.parse(readFileSync(resolve(here, 'spot.json'), 'utf8'));
  const words = durationCopy(advance);
  // For daytime or a change from evening to daytime, a 24-hour display keeps the daypart clear.
  const night = Math.floor(changed / 60) >= 18;
  data.early = original;
  data.late = clock(changed);
  data.title = '开场，提前' + words.title;
  data.copy.opening = night ? '今晚开场' : '本场开演';
  data.copy.before = night ? '定在' + posterTime(hour, minute) + '。' : '原定 ' + original + '。';
  data.copy.after = '提前' + words.title + '。';
  if (!night) data.copy.venue = data.copy.venue.replace('夜场', '演出');
  data.voice.find(line => line.id === '01').words = (night ? '今晚' : '本场') + '，开场提前' + words.speech + '。';
  const path = resolve(output);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(data, null, 2) + '\n', { flag: 'wx' });
  console.log(original + ' → ' + data.late + '　' + data.title + '\n' + path);
}
if (process.argv[2] === '--help') console.log(usage);
else try { retime(process.argv.slice(2)); } catch (error) {
  console.error(error.code === 'EEXIST' ? '输出文件已经存在，请换一个新文件名。' : error.message);
  process.exitCode = 1;
}
