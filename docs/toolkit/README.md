# The toolkit

Short primers for the tools this course uses that no earlier course taught you
from zero. Each one covers the commands the labs actually run, the traps the
reference runs hit, a ten-minute exercise in the course container, and an "if it
goes wrong" table. Every command in them was run in the course container (or on
a laptop, where the primer says so) before it was written down.

They are not extra coursework. Read the one a lab needs **before** that lab; the
lab handouts link to the right section where a step needs it.

| Primer | What it covers | Read before |
|---|---|---|
| [`git-and-github.md`](git-and-github.md) | identity on the laptop and in the container, logging in to GitHub, the team repo, pull/push, conflicts (and lock files), branches without losing work, tags, revert | **Lab 8** |
| [`shell.md`](shell.md) | pipes, `tee`, redirects, environment-variable prefixes, `$(…)`, loops and timeouts, `curl`, `awk`; laptop vs container; WSL paths | **Lab 8** |
| [`dvc-and-mlflow.md`](dvc-and-mlflow.md) | data and pipelines under DVC, remotes, `repro`, metrics diff; MLflow runs and the UI | **Lab 8** |
| [`docker-compose-make.md`](docker-compose-make.md) | `docker run` and `build` flags, writing a Dockerfile (multi-stage, uv, non-root), registries, compose files, Makefiles | **Lab 9**; again for the capstone |
| [`testing-with-pytest.md`](testing-with-pytest.md) | writing tests: fixtures, `parametrize`, `TestClient`, loading a module from a path, red first | **Lab 10** |
| [`yaml-and-github-actions.md`](yaml-and-github-actions.md) | YAML and its traps; GitHub Actions workflow syntax; PromQL for Lab 13 | **Lab 12** |
| [`stats-for-measurement.md`](stats-for-measurement.md) | percentiles, standard error, bootstrap intervals, the sign test, PSI and KS, pass^k, noise floors | Lab 11; used through Lab 21 |
| [`local-models-ollama.md`](local-models-ollama.md) | Ollama commands, model tags and quantisation, context length, reaching the host from the container, LM Studio | **Lab 14** |
| [`async-and-protocols.md`](async-and-protocols.md) | just enough asyncio, JSON-RPC, MCP transports, proxies and `CONNECT`, tool-call message shapes | **Lab 16** |
| [`capstone-toolchain.md`](capstone-toolchain.md) | your capstone repository from the starter in `capstone/skeleton/`, a second runner, bringing Labs 16–18 code across, the clean-clone rehearsal | **Lab 19** |

## Lab by lab

| Lab | You will need |
|---|---|
| 8 | git and GitHub (team repo, identity, login), shell, DVC and MLflow |
| 9 | Docker: run and build flags, writing a Dockerfile |
| 10 | pytest (Part B is written by hand), git branches (Part A) |
| 11 | DVC stages, pytest fixtures, the bootstrap |
| 12 | YAML and GitHub Actions, Docker tag and push, `git revert --no-edit` |
| 13 | PromQL (if you skip Grafana), PSI and KS, percentiles |
| 14 | Ollama, the sign test |
| 15 | compose files (profiles, internal networks), proxies |
| 16–18 | asyncio and MCP, tool-call messages, pass^k |
| 19–21 | Makefile, compose and CI for your own repository: the capstone toolchain |

New to a tool and stuck? The primer's "If it goes wrong" table first, then your
TA. Environment problems are fixed for you at once; they are not what is being
taught.
