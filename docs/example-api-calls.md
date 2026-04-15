# `/v1/models/load` 

## Request

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/models/load' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "model": "fullsong"
}'
```

## Response

```json
{
  "active_model": "fullsong",
  "status": "ready"
}
```

# `/v1/fullsong/generate`

## Request

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/fullsong/generate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "caption": "Genre: Eurodance, 90s dance-pop, upbeat electronic. Style: Catchy, energetic, nostalgic 90s Eurodance with a strong four-on-the-floor beat. Bright synth leads, punchy bassline, and rhythmic chord stabs. Mix of melodic female vocals for chorus and rhythmic male spoken/rap-style verses. Mood: Uplifting, euphoric, nostalgic club vibe. Tempo: ~130 BPM. Instrumentation: driving kick drum, eurodance bassline, bright saw synth leads, pads, dance piano accents, light vocal chops. Structure: Intro → Verse (male rap) → Pre-Chorus → Chorus (female melodic hook) → Verse → Chorus → Bridge → Final Chorus. Production: clean, polished, wide stereo, club-ready mix.",
    "lyrics": "[Intro]\nFeel the rhythm, feel the light\nWe come alive in neon night\n\n[Verse 1 – Male]\nStep in the scene, yeah the bassline drops\nHeartbeat racing when the strobe light pops\nHands up high, let the pressure go\nMove your body to the radio\n\nCity lights flashing in your eyes\nNo tomorrow, no disguise\nWe don’t stop, we don’t slow\nLet the energy overflow\n\n[Pre-Chorus – Female]\nTake me higher, don’t let go\nWe’re electric, feel the flow\n\n[Chorus – Female]\nWe are dancing in the neon in the night\nShining brighter than the stars in the sky\nFeel the fire, let it take you away\nWe will never fade\n\nWe are running through the rhythm of the sound\nLost together, never touching the ground\nIn this moment, we are wild and alive\nNeon in the night\n\n[Verse 2 – Male]\nTurn it up now, let the speakers explode\nFeel the vibration deep in your soul\nNo control when the DJ plays\nWe’re living fast in a laser haze\n\nEvery heartbeat syncs with the drum\nFeel the future, here it comes\nNo regret, just let it ride\nWe’re infinite tonight\n\n[Pre-Chorus – Female]\nTake me higher, don’t let go\nWe’re electric, feel the flow\n\n[Chorus – Female]\nWe are dancing in the neon in the night\nShining brighter than the stars in the sky\nFeel the fire, let it take you away\nWe will never fade\n\nWe are running through the rhythm of the sound\nLost together, never touching the ground\nIn this moment, we are wild and alive\nNeon in the night\n\n[Bridge]\nClose your eyes, feel the beat inside\nWe’re alive in the light\n\n[Final Chorus]\nWe are dancing in the neon in the night\nShining brighter than the stars in the sky\nFeel the fire, let it take you away\nWe will never fade\n\nWe are running through the rhythm of the sound\nLost together, never touching the ground\nIn this moment, we are wild and alive\nNeon in the night",
    "instrumental": false,
    "inference_steps": 8,
    "guidance_scale": 7.0,
    "use_random_seed": false,
    "seed": -1,
    "thinking": true,
    "batch_size": 1,
    "audio_format": "mp3"
}'
```

## Response

```json
{
  "data": {
    "task_id": "58e15e57-3022-4f43-8ada-64ea52a9064a",
    "status": "queued",
    "queue_position": 1
  },
  "code": 200,
  "error": null,
  "timestamp": 1776227065582,
  "extra": null
}
```

# `/v1/fullsong/result/{task_id}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/fullsong/result/58e15e57-3022-4f43-8ada-64ea52a9064a' \
  -H 'accept: application/json'
```

## Response

### Pending

```json
{
  "data": [
    {
      "task_id": "1fa3cec4-98b0-48b0-ab60-97be8e4306ab",
      "result": "[{\"file\": \"\", \"wave\": \"\", \"status\": 0, \"create_time\": 1776227246, \"env\": \"development\", \"progress\": 0.1, \"stage\": \"Phase 1: Generating CoT metadata (once for all items)...\"}]",
      "status": 0,
      "progress_text": "21:27:26 | INFO | Loaded LLM to cuda in 0.3896s"
    }
  ],
  "code": 200,
  "error": null,
  "timestamp": 1776227253257,
  "extra": null
}
```

### Finished

```json
{
  "data": [
    {
      "task_id": "1fa3cec4-98b0-48b0-ab60-97be8e4306ab",
      "result": "[{\"file\": \"/v1/audio?path=C%3A%5CArchive%5Crepo%5CK.G.One%5Cace-step%5C.cache%5Cacestep%5Ctmp%5Capi_audio%5Cddab3c48-b754-0bb1-7c5a-369344e1c308.mp3\", \"wave\": \"\", \"status\": 1, \"create_time\": 1776227246, \"env\": \"development\", \"prompt\": \"Genre: Eurodance, 90s dance-pop, upbeat electronic. Style: Catchy, energetic, nostalgic 90s Eurodance with a strong four-on-the-floor beat. Bright synth leads, punchy bassline, and rhythmic chord stabs. Mix of melodic female vocals for chorus and rhythmic male spoken/rap-style verses. Mood: Uplifting, euphoric, nostalgic club vibe. Tempo: ~130 BPM. Instrumentation: driving kick drum, eurodance bassline, bright saw synth leads, pads, dance piano accents, light vocal chops. Structure: Intro → Verse (male rap) → Pre-Chorus → Chorus (female melodic hook) → Verse → Chorus → Bridge → Final Chorus. Production: clean, polished, wide stereo, club-ready mix.\", \"lyrics\": \"[Intro]\\nFeel the rhythm, feel the light\\nWe come alive in neon night\\n\\n[Verse 1 – Male]\\nStep in the scene, yeah the bassline drops\\nHeartbeat racing when the strobe light pops\\nHands up high, let the pressure go\\nMove your body to the radio\\n\\nCity lights flashing in your eyes\\nNo tomorrow, no disguise\\nWe don’t stop, we don’t slow\\nLet the energy overflow\\n\\n[Pre-Chorus – Female]\\nTake me higher, don’t let go\\nWe’re electric, feel the flow\\n\\n[Chorus – Female]\\nWe are dancing in the neon in the night\\nShining brighter than the stars in the sky\\nFeel the fire, let it take you away\\nWe will never fade\\n\\nWe are running through the rhythm of the sound\\nLost together, never touching the ground\\nIn this moment, we are wild and alive\\nNeon in the night\\n\\n[Verse 2 – Male]\\nTurn it up now, let the speakers explode\\nFeel the vibration deep in your soul\\nNo control when the DJ plays\\nWe’re living fast in a laser haze\\n\\nEvery heartbeat syncs with the drum\\nFeel the future, here it comes\\nNo regret, just let it ride\\nWe’re infinite tonight\\n\\n[Pre-Chorus – Female]\\nTake me higher, don’t let go\\nWe’re electric, feel the flow\\n\\n[Chorus – Female]\\nWe are dancing in the neon in the night\\nShining brighter than the stars in the sky\\nFeel the fire, let it take you away\\nWe will never fade\\n\\nWe are running through the rhythm of the sound\\nLost together, never touching the ground\\nIn this moment, we are wild and alive\\nNeon in the night\\n\\n[Bridge]\\nClose your eyes, feel the beat inside\\nWe’re alive in the light\\n\\n[Final Chorus]\\nWe are dancing in the neon in the night\\nShining brighter than the stars in the sky\\nFeel the fire, let it take you away\\nWe will never fade\\n\\nWe are running through the rhythm of the sound\\nLost together, never touching the ground\\nIn this moment, we are wild and alive\\nNeon in the night\", \"metas\": {\"bpm\": 90, \"duration\": 174, \"genres\": \"N/A\", \"keyscale\": \"D minor\", \"timesignature\": \"4\", \"prompt\": \"Genre: Eurodance, 90s dance-pop, upbeat electronic. Style: Catchy, energetic, nostalgic 90s Eurodance with a strong four-on-the-floor beat. Bright synth leads, punchy bassline, and rhythmic chord stabs. Mix of melodic female vocals for chorus and rhythmic male spoken/rap-style verses. Mood: Uplifting, euphoric, nostalgic club vibe. Tempo: ~130 BPM. Instrumentation: driving kick drum, eurodance bassline, bright saw synth leads, pads, dance piano accents, light vocal chops. Structure: Intro → Verse (male rap) → Pre-Chorus → Chorus (female melodic hook) → Verse → Chorus → Bridge → Final Chorus. Production: clean, polished, wide stereo, club-ready mix.\", \"lyrics\": \"[Intro]\\nFeel the rhythm, feel the light\\nWe come alive in neon night\\n\\n[Verse 1 – Male]\\nStep in the scene, yeah the bassline drops\\nHeartbeat racing when the strobe light pops\\nHands up high, let the pressure go\\nMove your body to the radio\\n\\nCity lights flashing in your eyes\\nNo tomorrow, no disguise\\nWe don’t stop, we don’t slow\\nLet the energy overflow\\n\\n[Pre-Chorus – Female]\\nTake me higher, don’t let go\\nWe’re electric, feel the flow\\n\\n[Chorus – Female]\\nWe are dancing in the neon in the night\\nShining brighter than the stars in the sky\\nFeel the fire, let it take you away\\nWe will never fade\\n\\nWe are running through the rhythm of the sound\\nLost together, never touching the ground\\nIn this moment, we are wild and alive\\nNeon in the night\\n\\n[Verse 2 – Male]\\nTurn it up now, let the speakers explode\\nFeel the vibration deep in your soul\\nNo control when the DJ plays\\nWe’re living fast in a laser haze\\n\\nEvery heartbeat syncs with the drum\\nFeel the future, here it comes\\nNo regret, just let it ride\\nWe’re infinite tonight\\n\\n[Pre-Chorus – Female]\\nTake me higher, don’t let go\\nWe’re electric, feel the flow\\n\\n[Chorus – Female]\\nWe are dancing in the neon in the night\\nShining brighter than the stars in the sky\\nFeel the fire, let it take you away\\nWe will never fade\\n\\nWe are running through the rhythm of the sound\\nLost together, never touching the ground\\nIn this moment, we are wild and alive\\nNeon in the night\\n\\n[Bridge]\\nClose your eyes, feel the beat inside\\nWe’re alive in the light\\n\\n[Final Chorus]\\nWe are dancing in the neon in the night\\nShining brighter than the stars in the sky\\nFeel the fire, let it take you away\\nWe will never fade\\n\\nWe are running through the rhythm of the sound\\nLost together, never touching the ground\\nIn this moment, we are wild and alive\\nNeon in the night\"}, \"generation_info\": \"**🎵 Total generation time (1 song): 56.51s**\\n- 56.51s per song\\n- LM phase (1 song): 51.78s\\n- DiT phase (1 song): 4.72s\", \"seed_value\": \"827002500\", \"lm_model\": \"acestep-5Hz-lm-0.6B\", \"dit_model\": \"acestep-v15-turbo\", \"progress\": 1.0, \"stage\": \"succeeded\"}]",
      "status": 1,
      "progress_text": "21:28:26 | DEBUG | [AudioSaver] Fallback soundfile Saved audio to C:\\Archive\\repo\\K.G.One\\ace-step\\.cache\\acestep\\tmp\\api_audio\\ddab3c48-b754-0bb1-7c5a-369344e1c308.mp3 (mp3, 48000Hz)"
    }
  ],
  "code": 200,
  "error": null,
  "timestamp": 1776227311031,
  "extra": null
}
```

# `/v1/fullsong/audio/{task_id}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/fullsong/audio/1fa3cec4-98b0-48b0-ab60-97be8e4306ab?index=0' \
  -H 'accept: application/json'
```

## Response

Header:

```text
content-disposition: attachment; filename="1fa3cec4-98b0-48b0-ab60-97be8e4306ab.mp3" 
content-length: 3446400 
content-type: audio/mpeg 
date: Wed,15 Apr 2026 04:29:23 GMT 
server: uvicorn 
```

Body is the actual mp3 file payload

# `/v1/clip/generate`

## Request

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/clip/generate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Gritty, Acid, Bassline, 303, Synth Lead, FM, Sub, Upper Mids, High Phaser, High Reverb, Pitch Bend, 8 Bars, 140 BPM, E minor",
    "negative_prompt": "",
    "bars": 8,
    "bpm": 140,
    "note": "C",
    "scale": "minor",
    "steps": 75,
    "cfg_scale": 7,
    "seed": -1,
    "sampler_type": "dpmpp-2m-sde",
    "sigma_min": 0.03,
    "sigma_max": 500,
    "cfg_rescale": 0
}'
```

## Response

```json
{
  "task_id": "7ab55a6a-c478-45a0-bab7-1fd9cbd8597d"
}
```

# `/v1/clip/result/{task_id}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/clip/result/7ab55a6a-c478-45a0-bab7-1fd9cbd8597d' \
  -H 'accept: application/json'
```

## Response

When status == "complete", the generation is complete. otherwise the generation is still in progress.

```json
{
  "task_id": "7ab55a6a-c478-45a0-bab7-1fd9cbd8597d",
  "status": "complete"
}
```

# `/v1/clip/audio/{task_id}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/clip/audio/7ab55a6a-c478-45a0-bab7-1fd9cbd8597d' \
  -H 'accept: application/json'
```

## Response

Header

```text
content-length: 2419244 
content-type: audio/wav 
date: Wed,15 Apr 2026 04:47:41 GMT 
server: uvicorn
```

Body will be the actual wav payload

# `/v1/clip/midi/{task_id}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/clip/midi/7ab55a6a-c478-45a0-bab7-1fd9cbd8597d' \
  -H 'accept: application/json'
```

## Response

Header

```text
content-length: 1458 
content-type: audio/midi 
date: Wed,15 Apr 2026 04:50:52 GMT 
server: uvicorn 
```

Body will be the actual MIDI payload

# `/v1/separator/separate` 

## Request

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/v1/separator/separate' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@test.mp3;type=audio/mpeg' \
  -F 'model_filename=MDX23C-8KFFT-InstVoc_HQ.ckpt'
```

(Assume there is a `test.mp3` in the current folder)

## Response

```bash
{
  "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76"
}
```

# `/v1/separator/result/{task_id}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/separator/result/0b93cb76-616d-45f0-9580-61d615cd6a76' \
  -H 'accept: application/json'
```

## Response

### Working in Progress

```json
{
  "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76",
  "status": "running"
}
```

### Complete

```json
{
  "task_id": "0b93cb76-616d-45f0-9580-61d615cd6a76",
  "status": "complete",
  "files": [
    "0b93cb76-616d-45f0-9580-61d615cd6a76_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.mp3",
    "0b93cb76-616d-45f0-9580-61d615cd6a76_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3"
  ]
}
```

# `/v1/separator/download/{filename}`

## Request

```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/v1/separator/download/0b93cb76-616d-45f0-9580-61d615cd6a76_%28Vocals%29_MDX23C-8KFFT-InstVoc_HQ.mp3' \
  -H 'accept: application/json'
```

## Response

Header

```text
accept-ranges: bytes 
content-disposition: attachment; filename="0b93cb76-616d-45f0-9580-61d615cd6a76_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.mp3" 
content-length: 8274590 
content-type: audio/mpeg 
date: Wed,15 Apr 2026 04:55:46 GMT 
etag: "259510b3be99c4070c03c5da74976efd" 
last-modified: Wed,15 Apr 2026 04:53:21 GMT 
server: uvicorn 
```

Body will be the actual mp3 payload.
