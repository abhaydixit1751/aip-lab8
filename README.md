# AI in Practice 2

Plaksha University · MS in Artificial Intelligence · 5 Oct – 27 Nov 2026

From a working model to one somebody else can run, own and trust: reproducible
training, serving, containers, delivery and operations; sovereign (local)
models; agents; and a capstone delivered like a client engagement.

**New here? Read [`START_HERE.md`](START_HERE.md).** Everything runs in one
container, identical on macOS, Windows and Linux.

## The story

You are in Platform Engineering at **Aurora Health**, the insurer from Module 1.
**Arc A (Labs 8–13):** a colleague's claims model, taken from "please deploy" to
reproducible, served, shipped through CI and watched through a year of
production, until the honest verdict is to switch its automation off. **Arc B
(14–15):** Aurora's Module 1 AI on a client's own machines, with nothing
leaving. **Arc C (16–18):** a partner from another industry, its tools, an
agent that acts on them, and an attacker. **Arc D (19–21):** a client brief,
scoped, built, demonstrated and handed over. The whole story, lab by lab, and
what each lab hands to the next: [`docs/THE_STORY.md`](docs/THE_STORY.md).

**The tools.** Git with a team, DVC, MLflow, Docker, make, pytest, GitHub
Actions, Ollama and MCP are used from the first lab, and no earlier course
teaches all of them. [`docs/toolkit/`](docs/toolkit/README.md) has a short
primer for each, and says which lab needs it first.

| Folder | What is in it |
|---|---|
| `labs/labNN/` | one folder per lab: start with `START_HERE_LABn.md`, then `OVERVIEW.md` |
| `theory/` | the lecture notes, T5–T10 |
| `decks/` | the lecture decks: `html/` to present from, `.pptx` to file |
| `quizzes/` | end-of-lab quizzes: open in a browser |
| `data/claims/` | the Aurora Health claims dataset: read `DATA_CARD.md` |
| `docs/` | the course story, the toolkit primers, the syllabus |
| `supplied_model/` | the model you are handed in Lab 8 |

Material arrives week by week as a zip to unpack into this folder. A new drop
never contains the files you edit.
