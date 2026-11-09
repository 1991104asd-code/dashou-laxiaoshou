# 大手拉小手

一部手机、两个人一起玩的亲子小游戏合集，打开网页就能玩，不用安装。

- **拍拍乐**：手机平放，面对面比反应，看到目标动物就拍自己那一半屏幕
- **翻翻乐**：轮流翻牌找相同的，也可以两人商量着一起翻
- **戳泡泡**：合作戳泡泡，爱心泡泡要两个人同时按住才会破
- **挑战卡**：41 张线下互动卡片，放下手机一起动起来

可以按 3-4 岁 / 5-6 岁 / 7 岁以上调整难度。玩完一局全家攒星星，攒够了解锁贴纸；每玩 15 分钟会提醒休息眼睛。

游戏本身就是一个 `index.html` 文件，语音放在 `voice/` 文件夹里。星星和贴纸只保存在各自手机的浏览器里。

## 语音

语音是用开源模型 [Kokoro v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)（Apache 2.0）提前生成的 mp3，每台手机听起来都一样。语音里小朋友统一叫「宝贝」，大朋友用游戏里选的称呼。如果打不开 `voice/` 文件夹（比如直接双击本地的 index.html），游戏会退回使用手机自带的朗读。

改了台词（`index.html` 里的 `@voice-data` 区块）之后，重新生成语音：

```bash
node tools/voice-lines.js > lines.json
python tools/make_voice.py lines.json voice --model-dir <kokoro-multi-lang-v1_1 目录> --sid 19
```

需要先 `pip install sherpa-onnx numpy`，装好 ffmpeg，再从 [sherpa-onnx 的模型发布页](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models) 下载 `kokoro-multi-lang-v1_1`。已经生成过的句子会自动跳过。
