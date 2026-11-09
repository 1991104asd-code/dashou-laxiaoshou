"""把 voice-lines.js 输出的台词合成为 mp3，放进 voice/ 文件夹，并写好 voice/index.json。

依赖：pip install sherpa-onnx numpy；电脑上要有 ffmpeg。
模型：https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models 里的 kokoro-multi-lang-v1_1

用法：
  node tools/voice-lines.js > lines.json
  python tools/make_voice.py lines.json voice --model-dir <kokoro-multi-lang-v1_1 目录> --sid 19

现在游戏用的是 Kokoro v1.1-zh 的 19 号声音（sid 19）。

已经生成过的句子会跳过；台词表里没有的旧文件会被删掉。加 --force 全部重新生成。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np
import sherpa_onnx

DIGITS = '零一二三四五六七八九'
MEASURES = '个下次种样步秒只张对遍'


def num_zh(n: int) -> str:
    if n < 10:
        return DIGITS[n]
    if n < 20:
        return '十' + (DIGITS[n - 10] if n % 10 else '')
    if n < 100:
        return DIGITS[n // 10] + '十' + (DIGITS[n % 10] if n % 10 else '')
    return ''.join(DIGITS[int(c)] for c in str(n))


def normalize(text: str) -> str:
    """把"跳 5 下""2 个优点"这类写法变成"跳五下""两个优点"，让朗读更自然。"""
    def rep(m):
        n, nxt = int(m.group(1)), m.group(2)
        word = '两' if n == 2 and nxt and nxt in MEASURES else num_zh(n)
        return word + nxt

    t = re.sub(r'\s*(\d+)\s*(\S?)', rep, text)
    t = t.replace('"', '').replace('“', '').replace('”', '').replace('：', '，')
    return t


def build_tts(args):
    d = args.model_dir
    if args.engine == 'kokoro':
        model = sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=os.path.join(d, 'model.onnx'),
                voices=os.path.join(d, 'voices.bin'),
                tokens=os.path.join(d, 'tokens.txt'),
                lexicon=','.join(os.path.join(d, f) for f in ('lexicon-us-en.txt', 'lexicon-zh.txt')),
            ),
            num_threads=args.threads, provider='cpu')
        fsts = ','.join(os.path.join(d, f) for f in ('date-zh.fst', 'phone-zh.fst', 'number-zh.fst'))
    else:
        model = sherpa_onnx.OfflineTtsModelConfig(
            matcha=sherpa_onnx.OfflineTtsMatchaModelConfig(
                acoustic_model=os.path.join(d, 'model-steps-3.onnx'),
                vocoder=args.vocoder,
                lexicon=os.path.join(d, 'lexicon.txt'),
                tokens=os.path.join(d, 'tokens.txt'),
                dict_dir=os.path.join(d, 'dict'),
            ),
            num_threads=args.threads, provider='cpu')
        fsts = ','.join(os.path.join(d, f) for f in ('date.fst', 'phone.fst', 'number.fst'))
    cfg = sherpa_onnx.OfflineTtsConfig(model=model, rule_fsts=fsts, max_num_sentences=1)
    if not cfg.validate():
        sys.exit('模型配置不完整，请检查 --model-dir / --vocoder')
    return sherpa_onnx.OfflineTts(cfg)


def to_mp3(samples, rate, out_path, ffmpeg):
    pcm = (np.clip(np.asarray(samples, dtype=np.float32), -1, 1) * 32767).astype('<i2')
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        tmp = f.name
    try:
        with wave.open(tmp, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm.tobytes())
        trim = 'silenceremove=start_periods=1:start_threshold=-45dB'
        af = f'{trim},areverse,{trim},areverse,loudnorm=I=-15:TP=-1.5:LRA=11,apad=pad_dur=0.08'
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', tmp, '-af', af,
                        '-ar', '24000', '-ac', '1', '-codec:a', 'libmp3lame', '-b:a', '48k', out_path], check=True)
    finally:
        os.remove(tmp)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('lines')
    p.add_argument('out_dir')
    p.add_argument('--engine', choices=['kokoro', 'matcha'], default='kokoro')
    p.add_argument('--model-dir', required=True)
    p.add_argument('--vocoder', default='', help='matcha 需要的 vocos-22khz-univ.onnx')
    p.add_argument('--sid', type=int, default=3)
    p.add_argument('--speed', type=float, default=1.0)
    p.add_argument('--threads', type=int, default=4)
    p.add_argument('--name', default='', help='写进 index.json 的声音名称')
    p.add_argument('--force', action='store_true')
    p.add_argument('--no-prune', action='store_true', help='不删除台词表里没有的旧文件')
    args = p.parse_args()

    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        sys.exit('找不到 ffmpeg')
    with open(args.lines, encoding='utf-8') as f:
        lines = json.load(f)
    os.makedirs(args.out_dir, exist_ok=True)

    tts = None
    done = []
    for i, line in enumerate(lines, 1):
        out = os.path.join(args.out_dir, line['key'] + '.mp3')
        if args.force or not os.path.exists(out):
            tts = tts or build_tts(args)
            audio = tts.generate(normalize(line['text']), sid=args.sid, speed=args.speed)
            if len(audio.samples) == 0:
                print(f'[{i}/{len(lines)}] 失败：{line["text"]}', flush=True)
                continue
            to_mp3(audio.samples, audio.sample_rate, out, ffmpeg)
            print(f'[{i}/{len(lines)}] {line["text"]}', flush=True)
        done.append(line['key'])

    if not args.no_prune:
        keep = set(done)
        for fn in os.listdir(args.out_dir):
            if fn.endswith('.mp3') and fn[:-4] not in keep:
                os.remove(os.path.join(args.out_dir, fn))

    with open(os.path.join(args.out_dir, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump({'voice': args.name, 'keys': sorted(done)}, f, ensure_ascii=False)
    print(f'完成：{len(done)} / {len(lines)} 句')


if __name__ == '__main__':
    main()
