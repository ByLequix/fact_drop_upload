# FactDrop – daily fact video pipeline

Everything a fresh session needs to produce one FactDrop video. Follow the steps in order.

## Fixed settings

| What | Value |
|---|---|
| Channel / brand | FactDrop – "Facts that sound fake – but aren't." Language: **English** |
| Voice | ElevenLabs connector, `creative_generate_speech`, voice_id `TX3LPaxmHKxFdv7VOQHJ` (Liam), model_id `eleven_v4`, **generations_count 1** |
| Video | 1080×1920, 30 fps, ~11 Mbit/s with grain (handled by `core.render_scene`) |
| Google Drive | parent folder **Content**, id `1sbr895oqc1uiUZT6B98J3E6wgRYPW5RX` |
| YouTube | Windsor.ai for Social Media connector, connector `youtube`, account `122940` (channel FactDrop) |
| Upload repo | `bylequix/fact_drop_upload` (public, temporary video hosting only) |

## 1. Setup
- `add_repo` bylequix/fact_drop_upload with access "push", clone with `git clone --depth 1 https://github.com/bylequix/fact_drop_upload /home/claude/fact_drop_upload`.
- Work in a new folder, e.g. `/home/claude/work`, and copy `template/*` into it.
- Check: `ffmpeg`, Python `PIL` and `numpy`, fonts `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf`, `Poppins-Medium.ttf`, `/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf`.

## 2. Topic (random, no repeats)
- List past topics: Drive `search_files` with `'1sbr895oqc1uiUZT6B98J3E6wgRYPW5RX' in ancestors and title contains 'Upload-Infos'`. Titles start with the topic.
- Pick a NEW topic from a varied pool (animals, space, human body, history, geography, food, technology, physics, ocean, everyday life …). Avoid the category used yesterday if possible.
- Choose 3 surprising facts. **Verify each fact with WebSearch** against at least one reliable source (NASA, encyclopedias, universities, museums, reputable science outlets). Drop any fact you cannot verify. Note the sources.

## 3. Script (English)
Structure, 13–14 short lines, max ~480 characters total:
1. Hook (2 lines): "<Subject> is/are <surprising claim>." / "Here are three facts that prove it."
2. Fact 1 (2–3 lines), Fact 2 (2–3 lines), Fact 3 (2–4 lines)
3. Outro (2 lines): "Which fact surprised you?" / "Follow for more facts!"

- In the **text sent to ElevenLabs**, write numbers and units as words ("two hundred forty-three", "degrees Celsius").
- In the **captions**, use digits ("243", "465 °C").
- If a word may be mispronounced, change the spelling only in the TTS text (e.g. "Octopusses" for "Octopuses"); check unusual words with `espeak-ng -q --ipa "<word>"` if espeak-ng exists.

## 4. Voice
- One `creative_generate_speech` call (generations_count 1). Never call it a second time to retry: it charges again.
- `sleep 25`, then `creative_get_generations` with the flow_id and generation_id. Download `full_res_url` with curl to `voice.mp3`.

## 5. Timing → timeline.json
- `ffmpeg -i voice.mp3 -af silencedetect=noise=-38dB:d=0.12 -f null - 2>&1 | grep -oE "silence_(start|end): [0-9.]+"`
- Speech segments = the gaps between silences. Map them to the caption lines in order. If one segment holds two lines, split it by character share; if one line was spoken in two segments, merge them.
- LEAD = 0.3 s (voice is delayed by 0.3 s in the mix). Add LEAD to every time.
- Scene cuts at the middle of the pause between the last line of one scene and the first line of the next. Last scene ends at voice end + 0.6 s.
- Format (5 scenes): `[{"dur": 5.49, "caps": [[start, end, "Caption text", ""], ...]}, ...]`, caption times relative to the scene start. See `example_venus_timeline.json`.

## 6. Scenes
- Copy `example_venus.py` to `video.py` and replace the 5 scene functions (`s_hook`, fact 1, fact 2, fact 3, `s_outro`) and `FNS`.
- Keep the layout: `M.draw_label(f, t, n, a)` for "FACT n/3" at the top (facts only), headline with `M.headline(...)` around y 470–520, one simple drawn visual centered around y≈1000 (keep inside y 650–1320), captions are drawn by core at y 1440. Use `M.paste_shape` with 2× layers for smooth shapes.
- Palette: navy background (built in), `M.CORAL`, `M.YEL`, `M.WHITE`, `M.SOFT`; add topic colors if useful.
- Simple original shapes only (planets, bars, rings, thermometers, icons, numbers counting up). No logos, brands, copyrighted characters or real people.
- Time each reveal to the moment the voice mentions it (use the caption start times).
- Preview: `python3 video.py timeline.json preview 2,3,2.5,3,2 prev_` and look at all 5 PNGs (Read tool). Fix overlaps or text running off screen before rendering.

## 7. Render & mix
```bash
for i in 0 1 2 3 4; do python3 video.py timeline.json $i scene$i.mp4 & done; wait
printf "file 'scene%d.mp4'\n" 0 1 2 3 4 > list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -c copy joined.mp4
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 joined.mp4)
python3 music.py $D            # writes music.wav (original lo-fi bed)
ffmpeg -y -loglevel error -i voice.mp3 -i music.wav -filter_complex "[0:a]aresample=48000,aformat=channel_layouts=stereo,adelay=300|300,apad,atrim=0:$D,asplit=2[v][key];[1:a]volume=0.30[m];[m][key]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=450[md];[v][md]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-15:TP=-1.5,aresample=48000[out]" -map "[out]" -c:a aac -b:a 192k mix.m4a
ffmpeg -y -loglevel error -i joined.mp4 -i mix.m4a -map 0:v -map 1:a -c:v copy -c:a copy -shortest -movflags +faststart FactDrop_<YYYY-MM-DD>_<Topic>.mp4
```
Check one frame per scene from the final file and the video/audio durations with ffprobe.

## 8. Deliver
- Send the MP4 to the user with SendUserFile (status "proactive").
- Drive: create folder `<YYYY-MM-DD>` in Content (check first that it does not exist), then a text file `<Topic> – Upload-Infos.txt` (text/plain, disableConversionToGoogleType true) with: YouTube title (≤100 chars, ends with #shorts), YouTube description with hashtags, tags, TikTok caption with hashtags, the script, and the fact sources.
- Drive uploads are limited to ~3 MB per call, so the video itself does NOT go to Drive.

## 9. YouTube upload (private only)
1. Copy the MP4 into the repo, commit, `git -c push.negotiate=true push origin main`.
2. Check `https://raw.githubusercontent.com/bylequix/fact_drop_upload/main/<file>.mp4` returns 200.
3. Windsor `execute_action`: connector `youtube`, action `upload_video`, account `122940`, params: video_url (raw URL), title, description, tags, category_id "27", made_for_kids false, **privacy_status "private"**. Never public.
4. If YouTube answers "rate-limited": wait 60 s, try exactly once more. Do not loop.
5. **Always** remove the video from the repo afterwards, success or not: `git reset --hard HEAD~1 && git push -f origin main`. The repo must end with only README.md and template/.

## 10. Report
Final message (SendUserMessage) in **German**: topic, the 3 facts, YouTube status (link if uploaded, "privat – bitte prüfen und freischalten"), Drive folder link, and anything that went wrong.
