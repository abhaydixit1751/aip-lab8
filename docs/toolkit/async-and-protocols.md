# Toolkit — asyncio, JSON-RPC, MCP transports, proxies, tool calls

**Who needs this.** Lab 15 (the egress log: proxies and `CONNECT`), Lab 16
(`client.py`, `mcp_connect.py`: asyncio, JSON-RPC, stdio vs HTTP), Labs 17–18
(`agent_loop.py`, `sdk_agent.py`: asyncio and tool-call messages), and the
capstone if it uses MCP or an agent.

**Measured with** Python 3.12.14, mcp 2.2.0, openai-agents 0.22.3 and litellm
1.83.0 in the course container; Ollama 0.40.3 (granite4) on the laptop for the
tool-call example. Every output below is real.

> **The minimum.**
> - `async def` makes a coroutine; `await` runs one and waits for its result;
>   `asyncio.run(main())` starts everything, once, at the bottom of the script;
>   `async with` opens and closes something that needs awaiting (an MCP session).
> - MCP messages are JSON-RPC: a request has `id`, `method`, `params`; the reply
>   has the same `id` and either `result` or `error`.
> - stdio: the client **starts** the server and talks over its stdin/stdout.
>   Streamable HTTP: the server is **already running**; the client POSTs to `/mcp`.
> - A forward proxy receives `CONNECT host:443` for HTTPS and `GET http://...` for
>   HTTP. It sees where you are going, not what you send.
> - Tool calling: append the assistant message **with its `tool_calls`**, then
>   one `{"role": "tool", "tool_call_id": ..., "content": ...}` per call.

---

## 1 · asyncio, just enough to read the code

A network call spends most of its time waiting. asyncio lets one thread start
something, wait for it, and run other work meanwhile. Four pieces of syntax:

| Syntax | Means |
|---|---|
| `async def f(): ...` | `f()` returns a **coroutine**: a paused computation. Nothing runs yet |
| `x = await f()` | run it, and pause **this** coroutine until it finishes; only inside `async def` |
| `asyncio.run(main())` | start the event loop, run `main()` to the end, close the loop. Once per program |
| `async with thing() as s:` | like `with`, but opening and closing are awaited (start a process, a handshake) |

Run in the course container:

```python
import asyncio, time
from contextlib import asynccontextmanager

async def fetch(name, secs):
    await asyncio.sleep(secs)          # waiting: other coroutines may run meanwhile
    return f"{name} done"

@asynccontextmanager
async def session():
    print("open")
    try:
        yield "s"
    finally:
        print("close")

async def main():
    t = time.perf_counter()
    a = await fetch("one", 0.5)
    b = await fetch("two", 0.5)
    print(a, b, f"{time.perf_counter() - t:.1f}s in sequence")
    t = time.perf_counter()
    print(await asyncio.gather(fetch("x", 0.5), fetch("y", 0.5)), f"{time.perf_counter() - t:.1f}s together")
    async with session() as s:
        print("using", s)

asyncio.run(main())
```

```
one done two done 1.0s in sequence
['x done', 'y done'] 0.5s together
open
using s
close
```

Now read `labs/lab16/client.py` with that table: `async def main()`, then
`async with connect(pack=a.pack, url=a.url) as s:` (start the server, or reach
it, and run the MCP handshake; close it all at the end of the block), then
`await s.list_tools()` inside, and `asyncio.run(main())` at the bottom. The
calls on `s` (`list_tools`, `call_tool`, `read_resource`, `get_prompt`) are all
coroutines: each needs `await`. Lab 17's `run(...)` is an `async def` for the
same reason, and calls the model with `await litellm.acompletion(...)`.

Two errors you will meet (both measured):

- `RuntimeWarning: coroutine 'f' was never awaited`: you wrote `f()` without
  `await`. You got a coroutine object, not a result, and the work never ran.
- `RuntimeError: asyncio.run() cannot be called from a running event loop`:
  `asyncio.run` inside something already async, such as a Jupyter notebook. In a
  notebook cell, write `await main()` instead.

## 2 · JSON-RPC in one paragraph

JSON-RPC 2.0 is a tiny convention for calling a function on another program by
sending JSON. A **request** carries `"jsonrpc": "2.0"`, an `id` the caller
chooses, a `method` name and `params`. The **response** carries the same `id`
and either a `result` or an `error` with a numeric `code` and a `message`. A
**notification** has no `id` and gets no reply. That is all; MCP defines which
methods exist (`initialize`, `tools/list`, `tools/call`, `resources/read`,
`prompts/get`) and what their params and results look like.

The real exchange with your Lab 16 server over stdio, one JSON object per line
(the starter `server.py --pack finance`, captured by piping three lines into it):

```
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"primer","version":"0"}}}
← {"jsonrpc":"2.0","id":1,"result":{"capabilities":{..."tools":{"listChanged":false}},"protocolVersion":"2025-06-18","serverInfo":{"name":"aip2-finance","version":"0.1"}}}
→ {"jsonrpc":"2.0","method":"notifications/initialized"}
→ {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"validate_gstin","arguments":{"gstin":"33XUGCK5579A1ZV"}}}
← {"jsonrpc":"2.0","id":2,"result":{"content":[{"text":"{\n  \"gstin\": \"33XUGCK5579A1ZV\",\n  \"valid\": true, ...}","type":"text"}],"isError":false}}
```

An unknown method: `← {"jsonrpc":"2.0","id":3,"error":{"code":-32601,"message":"Method not found","data":"tools/delete_everything"}}`.

Two kinds of failure, kept apart: a JSON-RPC `error` means the **protocol** call
failed (no such method, bad params); a tool that ran and failed returns a normal
`result` with `"isError": true`, which is what Lab 16's TODO 2 produces and
your contract cases' `is_error` expects. `mcp_connect.connect()` and `ClientSession` write
and read all of this for you; you never build these by hand in the labs.

## 3 · Transports: stdio and streamable HTTP

| | stdio | streamable HTTP |
|---|---|---|
| Who starts the server | the client, as a child process (`stdio_params()`: `python labs/lab16/server.py --pack <pack>`) | you, beforehand: `server.py --pack <pack> --http --port 18090` |
| Messages travel | one JSON object per line on the server's stdin and stdout | HTTP `POST /mcp`; the reply comes back as JSON or as a server-sent-event stream |
| Lifetime | dies with the client: a fresh server per session | lives until you stop it; many clients can share it |
| Environment (`PACK_LEDGER`) | the client passes it to the child | whatever the shell that started the server had |
| Typical host | Claude Desktop, your `client.py`, Lab 17's runner | a server on another machine or container |

What the HTTP transport looks like on the wire (measured, `initialize` posted
with `curl` to a server started with `--http --port 18097`):

```
HTTP/1.1 200 OK
content-type: text/event-stream
mcp-session-id: 2d85eed5e8d94efdb11c2541412301ff

event: message
data: {"jsonrpc":"2.0","id":1,"result":{..."serverInfo":{"name":"aip2-finance","version":"0.1"}}}
```

The same JSON-RPC as stdio, inside HTTP. The client must send
`Accept: application/json, text/event-stream`, and later requests carry the
`mcp-session-id` header back. A stdio server must never `print()` anything to
stdout except protocol messages, because stdout **is** the channel; log to stderr.

The runsheet starts the HTTP server in the background with `&` and stops it with
`kill %1`. If a run goes wrong in between, the server keeps port 18090 and the
next start fails with "address already in use": `jobs` lists it, `kill %1` stops it.

## 4 · Forward proxies and `CONNECT` (Lab 15)

A **forward proxy** is a server your programs send their outbound requests to,
instead of the destination. Libraries that honour `HTTPS_PROXY` / `HTTP_PROXY`
do this automatically. For an `http://` URL the client sends the proxy the whole
request (`GET http://example.com/ HTTP/1.1`). For `https://` it sends
`CONNECT example.com:443`, asking for a raw tunnel, and then speaks encrypted TLS
through it: the proxy learns the host and port, never the path or the content.
(A **reverse** proxy, like Lab 15's nginx gateway, sits in front of servers and
receives requests meant for them.)

`labs/lab15/egress_log.py` is a proxy that logs and refuses everything.
Measured in the course container:

```bash
python labs/lab15/egress_log.py --port 18899 --host 127.0.0.1 &
HTTPS_PROXY=http://127.0.0.1:18899 curl -sS https://example.com -o /dev/null
kill %1
```

```
BLOCKED  18:03:57  CONNECT example.com:443  (curl/8.14.1)
{"at": "18:03:57", "from": "127.0.0.1", "method": "CONNECT", "to": "example.com:443", "user_agent": "curl/8.14.1"}
curl: (56) CONNECT tunnel failed, response 403
```

**A trap, measured:** `curl` ignores upper-case `HTTP_PROXY` for `http://`
URLs (in CGI programs a request's `Proxy:` header arrives as `HTTP_PROXY`, so
curl refuses to trust it) and honours only lower-case `http_proxy`. With
`HTTP_PROXY` set, `curl http://example.com/` went straight out (status 200,
nothing logged); with `http_proxy` it was logged and refused. Python's `urllib`
honoured `HTTP_PROXY`, and curl honoured `HTTPS_PROXY`.
That is why the proxy alone proves only who *tried*; the `internal: true`
network is what stops a program that bypasses it. `NO_PROXY` lists hosts that
go direct (Lab 15: `gateway,localhost,127.0.0.1`).

## 5 · Tool-calling message shapes (Labs 16–18)

`to_openai()` turns each MCP tool into a function schema; the model receives
those as `tools`. Measured through Ollama's `/v1` with granite4 and one tool:

**Request**

```json
{"model": "granite4:latest",
 "messages": [{"role": "user", "content": "What is the status of claim CLM-1043272?"}],
 "tools": [{"type": "function", "function": {"name": "get_claim", "description": "Look up one claim by its ID.",
            "parameters": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}}}],
 "reasoning_effort": "none", "max_tokens": 100}
```

**Response**: an assistant message with no text and a tool call

```json
{"role": "assistant", "content": "",
 "tool_calls": [{"id": "call_o6bj1u0e", "index": 0, "type": "function",
                 "function": {"name": "get_claim", "arguments": "{\"claim_id\":\"CLM-1043272\"}"}}]}
```

with `"finish_reason": "tool_calls"`. Note that `arguments` is a **string** of
JSON, not an object: you `json.loads` it, and a small model sometimes writes
JSON that does not parse.

**Next request**: the history grows by two messages

```
{"role": "assistant", "content": "", "tool_calls": [ ...exactly as received... ]},
{"role": "tool", "tool_call_id": "call_o6bj1u0e",
 "content": "{\"claim_id\": \"CLM-1043272\", \"status\": \"under review\", \"amount_inr\": 48200}"}
```

The model answered: "The status of claim **CLM-1043272** is **under review**. The
claimed amount is **₹48,200** (INR).", `finish_reason` `stop`. Rules:

- The assistant message goes back **with** its `tool_calls`; the tool message
  refers to one of them by `tool_call_id`. Drop the first and the model never
  sees what it asked for, and asks again (Lab 17 CODE_GUIDE §1 measured 12
  identical calls).
- One `tool` message per tool call, and `content` is a string (JSON is fine).
- A denied action or a failed tool is still a `tool` message: say what happened,
  so the model can explain it to the user.
- No `tool_calls` in a reply means it is the final answer.

## If it goes wrong

| Symptom | Cause and fix |
|---|---|
| `coroutine ... was never awaited` | A missing `await` in front of an async call |
| `asyncio.run() cannot be called from a running event loop` | In a notebook: `await main()` instead |
| `'coroutine' object has no attribute 'tools'` | `s.list_tools().tools` without `await`: write `(await s.list_tools()).tools` |
| Client hangs at start over stdio | The server printed to stdout, or crashed: run `python labs/lab16/server.py --pack <pack>` alone and read its error |
| HTTP: `address already in use` on 18090 | A server from an earlier run: `jobs`, then `kill %1` |
| HTTP: every `ledger_tool` case fails | The server was started without the test's `PACK_LEDGER` |
| JSON-RPC `-32601 Method not found` | A misspelt method; the SDK's calls avoid this |
| Model repeats the same tool call | The assistant message was appended without its `tool_calls` |
| `json.decoder.JSONDecodeError` on arguments | The model wrote bad JSON: send it back as a tool message, do not crash |
| Egress log empty although something went out | The client ignored the proxy variables (for `curl http://`: set lower-case `http_proxy`) |
