# Voice cards

Short reference reads that `narrate.py` clones, so a whole film keeps one speaker. Each card is a WAV plus a
`.txt` with exactly what is said in it. Made with VoxCPM2 voice design (Apache-2.0 model; the audio is
synthetic, no real person's voice), three tries per description, keeping the try whose pitch and pace fit.

| card | description given to VoxCPM2 | pitch | pace |
|---|---|---|---|
| `teacher` | 一位三十岁左右的女性老师，声音温暖清澈，语速从容，像在给朋友讲一道有意思的题 | ~205 Hz | 4.6 字/秒 |
| `promo` | 年轻男性，声音干净明亮，有活力，语速稍快，自信但不夸张 | ~148 Hz | 5.0 字/秒 |
| `story` | 中年男性，声音低沉温和，语速缓慢，带一点回忆的感情 | ~126 Hz | 4.1 字/秒 |

Add your own: any clean 5–10 s mono recording of one person speaking naturally, with its transcript in a
`.txt` of the same name. Use only voices you have the right to use.
