# Credits and licences

Everything in the video and on the companion site is either original to this entry or used under a licence that allows it. No stock footage, stock photos, stock music or samples are used anywhere.

| Element | What it is | Source | Licence |
|---|---|---|---|
| Narration | Synthetic voice, generated line by line from the script | Kokoro 82M v1.0 by hexgrad, voice Bella (`af_bella`), open weights ([model card](https://huggingface.co/hexgrad/Kokoro-82M)), run with kokoro-onnx | Apache 2.0 (weights and voices). kokoro-onnx is MIT. The espeak-ng phonemizer it calls is GPL-3.0; it is used as a tool and its licence does not cover the audio it helps produce. |
| Speech check | Every narration take is transcribed to confirm it says the script exactly | faster-whisper with Whisper `medium.en` | MIT |
| Music | Original score: pads, plucked arpeggio, bass and light percussion | Synthesised from oscillators and noise in `src/audio/music.py` | Original to this entry |
| Sound effects | Whooshes, ticks, chimes, the lock and the "blocked" sound | Synthesised in `src/audio/music.py` | Original to this entry |
| Animation | Every frame of the video | HTML and SVG scenes in `src/video/`, rendered frame by frame with Chromium | Original to this entry |
| Redbelly logo | Horizontal negative lockup and isotype, unaltered | Official Redbelly brand kit, [redbelly.network/brand](https://redbelly.network/brand) | Provided by Redbelly Network for use in Redbelly material |
| Redbelly DAO logo | Site and PDF header only, unaltered | Redbelly DAO Task Board brand kit, [taskboard.redbellydao.network/brand](https://taskboard.redbellydao.network/brand) | Provided by the DAO for contributor deliverables |
| Colours, type scale, voice rules | Design tokens for the video, site and PDF | Redbelly DAO Task Board brand kit (`assets/brand/dao-tokens.css`) | As above |
| Be Vietnam Pro | Headings and body text | Google Fonts, self-hosted in `assets/fonts/` | SIL Open Font License 1.1 (`assets/fonts/OFL-BeVietnamPro.txt`) |
| JetBrains Mono | Machine values: status labels, timecodes, file names | Google Fonts, self-hosted in `assets/fonts/` | SIL Open Font License 1.1 (`assets/fonts/OFL-JetBrainsMono.txt`) |
| Icons | Line icons in the video, site and PDF | Lucide 0.460.0, copied into `assets/icons/` | ISC (`assets/icons/LICENSE-lucide.txt`) |

Names of organisations in the video (University of Sydney, CSIRO, Reserve Bank of Australia, AP+ HashSphere, Canvas Connect) appear as plain text only, to state facts from the sources listed in `submission/sources.md`. No third-party logos other than Redbelly's are used.
