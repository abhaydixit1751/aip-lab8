# Toolkit — local models with Ollama (and LM Studio)

**Who needs this.** Labs 14–18 and the capstone: every local model call in the
second half goes through Ollama on your laptop. Lab 15 needs the server
settings (`OLLAMA_NO_CLOUD`, `OLLAMA_HOST`); Lab 14 needs the context-length
setting; Lab 14 Part D needs LM Studio; Lab 21 starts with `ollama run`.

**Measured on:** Ollama **0.40.3** (the macOS desktop app, Apple M4 Max, 36 GB),
reached from the course container; LM Studio CLI (commit 6041ae0). Every command
below was run there unless marked *(not run here)*. Nothing was downloaded.

> **The minimum.**
> - `ollama --version`, `ollama list`, `ollama ps` (what is loaded, how big, at
>   what context), `ollama stop <model>`.
> - **Context length decides memory.** Measured: granite4 (a 2.1 GB download)
>   took **13 GB** at the app's 131,072-token default and **2.8 GB** at 8,192.
>   Check the CONTEXT column of `ollama ps`, and set it on purpose (§4).
> - From the course container, Ollama is `http://host.docker.internal:11434`,
>   never `localhost`.
> - The OpenAI-compatible endpoint is `/v1`. It ignores per-request
>   `num_ctx`: only the server default or a Modelfile changes it there.
> - Turn thinking off: `think: false` (native API) or `reasoning_effort: "none"`
>   (`/v1`).

---

## 1 · Is it running?

```bash
ollama --version                              # ollama version is 0.40.3
curl -s localhost:11434/api/version           # {"version":"0.40.3"}
```

From inside the course container (`make shell`):

```bash
echo $OLLAMA_HOST                             # http://host.docker.internal:11434
curl -s http://host.docker.internal:11434/api/version
curl -s http://localhost:11434/api/version    # nothing: curl exit 7. localhost is the container itself
```

The desktop app (menu-bar icon on macOS, tray on Windows) starts the server for
you. Without the app, start it in a terminal with `ollama serve` and leave that
terminal open. Not both: a second server fails with
`Error: listen tcp 127.0.0.1:11434: bind: address already in use` (measured).

## 2 · The everyday commands

| Command | Does | Note |
|---|---|---|
| `ollama pull qwen3.5:4b` | download a model | *(not run here)*. Resumes if you run it again |
| `ollama list` | what is on disk, with size | a size of `-` and a `:cloud` tag means it runs on Ollama's servers |
| `ollama ps` | what is **loaded**: SIZE, PROCESSOR, CONTEXT, UNTIL | the only honest memory number |
| `ollama show granite4:latest` | architecture, parameters, max context, quantisation, capabilities | |
| `ollama show granite4:latest --license \| head` | the licence | read it before a client builds on it |
| `ollama run granite4:latest "Reply with one word: ready"` | one prompt, one answer, then exit | without the prompt it is an interactive chat (`/bye` leaves) |
| `ollama stop granite4:latest` | unload it now | otherwise it unloads after 5 minutes idle |
| `ollama rm <model>` | delete from disk | frees the space; you would have to pull again |

`ollama ps` after loading granite4 with the app's defaults (measured):

```
NAME               ID              SIZE     PROCESSOR    CONTEXT    RUNNER      UNTIL
granite4:latest    4235724a127c    13 GB    100% GPU     131072     llamacpp    4 minutes from now
```

`PROCESSOR` should say `100% GPU` on Apple Silicon or a supported GPU. A split
such as `40%/60% CPU/GPU` means it did not fit, and it will be slow. Note that
`ollama show` prints the model's **maximum** context (`context length 131072`),
not what is loaded. Only `ollama ps` tells you that.

## 3 · Tags and quantisation names

A model name is `name:tag`. `qwen3.5:4b-q8_0` is Qwen 3.5, 4 billion parameters,
8-bit. No tag means `:latest`, whatever the publisher chose: `qwen3.5:2b`'s
default **is** the 8-bit build (Lab 14). Read the `quantization` line of
`ollama show`; measured here: granite4 `Q4_K_M`, qwen3.5:4b-q8_0 `Q8_0`,
gemma4:e4b-mlx `nvfp4`.

| Name | One line |
|---|---|
| **bf16 / f16** | 16 bits per weight: the unquantised reference, twice the size of Q8 |
| **Q8_0** | 8 bits per weight, one scale per block of 32 weights; near-lossless, half of f16 |
| **Q4_K_M** | about 4.85 bits per weight: a llama.cpp "k-quant" (K), medium mix (M), keeping some layers at higher precision; the usual default |
| **GGUF** | the single-file format llama.cpp (and so Ollama and LM Studio) loads: weights, tokenizer and settings together |
| **MLX** | Apple's array framework for Apple Silicon; an `-mlx` tag runs on Ollama's MLX engine, Mac only |
| **NVFP4** | a 4-bit floating-point format with fine-grained scales (from NVIDIA); what `gemma4:e4b-mlx` ships as |
| **`:cloud`** | not on your laptop at all: Ollama forwards the request to its servers. Not in this course |

## 4 · Context length: the setting that decides memory

The runtime reserves memory for the whole context when it loads the model, not
for the prompt you send. Measured, same model, same laptop:

| Model, loaded with | CONTEXT | SIZE in `ollama ps` |
|---|---|---|
| granite4, the desktop app's default | 131,072 | **13 GB** |
| granite4, `num_ctx: 8192` | 8,192 | **2.8 GB** |
| qwen3.5:4b, the desktop app's default | 131,072 | **8.0 GB** |
| qwen3.5:4b, `num_ctx: 4096` | 4,096 | **3.3 GB** |

**Where the default comes from.** `ollama serve --help` says
`OLLAMA_CONTEXT_LENGTH  Context length to use unless otherwise specified
(default: 4k/32k/256k based on VRAM)`. On this laptop the server log shows the
VRAM rule would give 32,768, but the desktop app starts its server with
`OLLAMA_CONTEXT_LENGTH=131072`, taken from the app's own Settings (its
context-length setting). Find out what yours does:

```bash
ollama ps                                                       # the CONTEXT column, after any request
grep -o -E 'OLLAMA_CONTEXT_LENGTH:[0-9]*|OLLAMA_NO_CLOUD:[a-z]*|default_num_ctx=[0-9]*' ~/.ollama/logs/server.log
```

On this machine that printed `OLLAMA_CONTEXT_LENGTH:131072`,
`OLLAMA_NO_CLOUD:false`, `default_num_ctx=32768`. (macOS log location. On Linux
with systemd, use `journalctl -u ollama` *(not run here)*.)

**Four ways to set it, measured on 0.40.3:**

| Way | Scope | Works? |
|---|---|---|
| `"options": {"num_ctx": 8192}` in a request to `/api/generate` or `/api/chat` | that request (the model reloads if it differs) | **yes**: CONTEXT 8192, 2.8 GB. This is what `speed.py --ctx` and `harness.py --ctx` send |
| the same `options` in a request to `/v1/chat/completions` | — | **no**: ignored, the model stayed at 131,072 |
| `OLLAMA_CONTEXT_LENGTH=8192 ollama serve` (or the app's setting) | every request that does not say otherwise, including `/v1` | **yes**: CONTEXT 8192 (tested on a second server on port 11500, so the app's server was not disturbed) |
| a Modelfile: `FROM granite4:latest` + `PARAMETER num_ctx 8192`, then `ollama create granite4-8k -f Modelfile` | every request for the new name, including `/v1` | **yes**: CONTEXT 8192 through `/v1` (the test model was then removed with `ollama rm`) |

Labs 17 and 18 call Ollama through `/v1` (`agent_common.resolve()`), so for
them only the server default or a Modelfile counts. On an 8 GB laptop, set the
default to 8,192 or 16,384 before Lab 14, and say in your report what it was.

## 5 · The KV cache, in two sentences

To produce each new token, the model attends to every earlier token's
attention **keys and values**; the runtime keeps those vectors in memory (the
KV cache) instead of recomputing them. It stores them per layer, per KV head,
for every position the context allows, so its size grows linearly with the
context the runtime **reserves**.

T8's formula, 2 bytes per number (f16):

    KV cache ≈ 2 × layers × kv_heads × head_dim × context × 2 bytes

llama3.1:8b (`ollama show llama3.1:8b --verbose`: `llama.block_count 32`,
`llama.attention.head_count_kv 8`; `llama.embedding_length 4096` over
`llama.attention.head_count 32` gives `head_dim` 128), in the course container:

```bash
python -c "print(2*32*8*128*8192*2/1e9, 2*32*8*128*131072*2/1e9)"     # 1.073741824 17.179869184
```

1.07 GB at 8K, beside 4.9 GB of weights: T8 measured 5.92 GB resident. At
131K the cache alone would be 17 GB. Hybrid models (qwen3.5) keep a KV cache in
only some layers, so the formula overestimates them. `ollama serve --help` also
lists `OLLAMA_KV_CACHE_TYPE` (default `f16`; `q8_0` halves the cache)
*(not tested here)*.

## 6 · Choosing a model by RAM

From `labs/lab14/START_HERE_LAB14.md`. The model must fit **with room to
spare**: the OS, a browser and the harness need memory too.

| Your laptop | Pull | Download |
|---|---|---|
| 8 GB | `granite4`, `qwen3.5:2b-q4_K_M`, `qwen3.5:2b`, `qwen3.5:4b` | 2.1 + 1.9 + 2.7 + 3.4 GB |
| 16 GB | the above, plus `qwen3.5:4b-q8_0`, `llama3.1:8b` | + 5.3 + 4.9 GB |
| 16 GB, Apple Silicon | also `gemma4:e4b-mlx` (tight: close everything else) | + 9.5 GB (8.8 GB resident) |
| 16 GB, Windows / Linux | also `gemma4:e4b`, if you have the room | + 9.6 GB |
| 32 GB+ | also `qwen3.5:9b` or `qwen2.5:14b-instruct` | 6.6 / 9 GB |

A rough check from §4–§5: resident ≈ download size + KV cache at your context
(T8 found it within 2% for llama3.1 and qwen2.5). If that comes close to your
RAM, choose the smaller model or the smaller context.

## 7 · Server settings: `OLLAMA_HOST` and `OLLAMA_NO_CLOUD`

**`OLLAMA_NO_CLOUD=1`** stops the server forwarding `:cloud` models to Ollama's
servers (Lab 15, "the seal ends at the runtime"). Measured on a server started
with it: a request for `minimax-m2.5:cloud` returned
`{"error":"ollama cloud is disabled: remote model is unavailable"}`.

**`OLLAMA_HOST`** on the **server** is the address it listens on (default
`127.0.0.1:11434`). On the **client** (the course container, `agent_common.py`)
the same name holds the URL to call. Same variable, two jobs.

**How the container reaches the host.** On Docker Desktop (macOS, Windows),
`host.docker.internal` leads to the laptop's own loopback, so the default
`127.0.0.1` works (measured on macOS). On **Linux**, `compose.yaml` maps
`host.docker.internal` to `host-gateway`, the Docker bridge address, and a
server listening only on `127.0.0.1` refuses it. Then start Ollama with
`OLLAMA_HOST=0.0.0.0`. That also exposes it to your Wi-Fi network: do it on a
network you trust, and turn it back off after the lab.

How to set either, per platform:

| You run | How |
|---|---|
| a terminal | quit the app, then `OLLAMA_NO_CLOUD=1 OLLAMA_HOST=0.0.0.0 ollama serve` |
| the macOS desktop app | its Settings. The app passes its own `OLLAMA_CONTEXT_LENGTH` and `OLLAMA_NO_CLOUD` to the server it starts (seen in the process environment here), so change these in the app, not with `launchctl setenv`. Its settings store also has an "expose to the network" switch, the app's form of `0.0.0.0` *(inferred, not toggled here)* |
| Linux, installed as a service | `sudo systemctl edit ollama.service`, add `[Service]` and `Environment="OLLAMA_HOST=0.0.0.0"` (one `Environment=` line per variable), then `sudo systemctl restart ollama` *(not run here)* |
| Windows app | quit Ollama from the tray; search Windows for "environment variables", choose *Edit environment variables for your account*, add the variable; start Ollama again *(not run here)* |

Check what the running server believes with the `grep` in §4.

## 8 · The OpenAI-compatible endpoint

Ollama serves the OpenAI chat-completions shape at `/v1`. From the container:

```bash
curl -s http://host.docker.internal:11434/v1/models | python -c "import json,sys; print([m['id'] for m in json.load(sys.stdin)['data']][:4])"
curl -s http://host.docker.internal:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"granite4:latest","messages":[{"role":"user","content":"Reply with one word: ready"}],"reasoning_effort":"none","max_tokens":5}'
```

The first printed `['qwen3.5:9b', 'qwen3.5:4b', 'qwen3.5:4b-q8_0',
'qwen2.5-coder:14b-instruct-q4_0']`; the second, `"content":"Ready"` in
`choices[0].message` and `"completion_tokens":2` in `usage`. On the laptop, use
`localhost:11434` instead. Tool calls come back
in the same shape as OpenAI's (see `async-and-protocols.md`).

LiteLLM model strings in the course: `ollama/<tag>` (Labs 14–15, Ollama's native
API) and `ollama_chat/<tag>` (Labs 17–18). `agent_common.resolve()` rewrites the
second to `openai/<tag>` with `api_base` `$OLLAMA_HOST/v1`, because LiteLLM
1.83's `ollama_chat` adapter dropped the assistant's `tool_calls` from the history.

## 9 · Thinking off

Reasoning models (qwen3.5, gemma4) think before they answer, and you wait for
every hidden token. Measured, qwen3.5:4b, "What is 17 + 25?", native `/api/chat`:

| `"think"` | answer | thinking characters | output tokens |
|---|---|---|---|
| `false` | `42` | 0 | **3** |
| `true` | `42` | 654 | **244** |

The switch is spelled differently per endpoint: `"think": false` on Ollama's
native API; `"reasoning_effort": "none"` on `/v1` (what `agent_common.py`
sends); LM Studio ignores `think` and honours `reasoning_effort` (Lab 14).
From the command line: `ollama run qwen3.5:4b --think=false "What is 17 + 25? Answer with the number only."` printed `42`.

## 10 · LM Studio and `lms`

LM Studio's server listens on `:1234/v1`. Its CLI lives in `~/.lmstudio/bin/lms`
and is **not** on your `PATH` after installing the app. Check it is there, then
bootstrap it:

```bash
ls ~/.lmstudio/bin                     # lms
~/.lmstudio/bin/lms bootstrap          # (not run here: it edits your shell profile; on this
                                       #  laptop ~/.zshrc already had the PATH line it adds)
```

Open a new terminal, then (measured):

```bash
lms ls                  # "You have 17 models, taking up 119.48 GB of disk space." and a table
lms server status       # "The server is running on port 1234."
lms ps                  # "No models are currently loaded."
```

`lms server start` and `lms load <model>` start the server and load a model
*(not run here)*. `lms ps` then shows the identifier the harness needs:
`--model lm_studio/<that id>`. On Windows the CLI is
`%USERPROFILE%\.lmstudio\bin\lms.exe` *(not run here)*.

---

## Try it

1. `ollama ps` now. Then load your smallest model with a small context and look
   again:
   `curl -s localhost:11434/api/generate -d '{"model":"granite4:latest","prompt":"Reply with one word: ready","stream":false,"options":{"num_ctx":8192,"num_predict":5}}'`.
   Compare SIZE and CONTEXT with what you got from `ollama run` of the same
   model. Then `ollama stop granite4:latest`.
2. Run the `grep` in §4. What context does your server use when nobody says?
3. Compute the KV cache for your largest model at your default context
   (`ollama show <model> --verbose` for the numbers) and compare with `ollama ps`.

## If it goes wrong

| Symptom | Cause and fix |
|---|---|
| `Connection refused` on 11434 from the laptop | Ollama is not running: open the app, or `ollama serve` |
| `Connection refused` from the container, laptop fine | You used `localhost` (the container), or on Linux the server listens on 127.0.0.1 only: `OLLAMA_HOST=0.0.0.0` (§7) |
| `bind: address already in use` on `ollama serve` | The app's server is already running. Quit the app first, or use the app |
| A small model makes the laptop swap | CONTEXT in `ollama ps` is huge. Lower the default (§4) |
| `/v1` calls ignore your `num_ctx` | Expected (measured). Use the server default or a Modelfile |
| `PROCESSOR` shows a CPU/GPU split | It did not fit. Smaller model, smaller context, or close other programs |
| Empty answers, or every call takes the whole token budget | Thinking is on: `think: false` / `reasoning_effort: "none"` (§9) |
| `ollama list` shows `:cloud` models | Not local. Do not use them; `OLLAMA_NO_CLOUD=1` makes the server refuse them |
| `gemma4:e4b-mlx` not found | Mac only, and needs a recent Ollama; on Windows/Linux use `gemma4:e4b` |
| `lms: command not found` | Not bootstrapped: `~/.lmstudio/bin/lms bootstrap`, then a new terminal |
| The first request after a pause is slow | The model was unloaded after 5 minutes idle; that is the load time |
