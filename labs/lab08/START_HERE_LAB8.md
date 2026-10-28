# Lab 8 — start here

Do this **before the lab**, as a team. It takes about 30 minutes, most of it
the first `make up`. If you arrive without it, you will spend Part A setting
up instead of measuring.

You need: Docker installed ([`START_HERE.md`](../../START_HERE.md) §1), a
GitHub account each, and the Lab 8 zip, `AI-in-Practice-2-Lab8.zip`.

---

## 1 · One teammate creates the team repo — 15 min

Pick one person. On **their** laptop:

```bash
unzip AI-in-Practice-2-Lab8.zip -d aip2
cd aip2
make up          # first time ~2 minutes: builds the course container
make check       # every line ok, except possibly "git identity" and "host Ollama"
```

Set your git identity **inside** the container, once. It persists across
restarts:

```bash
make shell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
exit
```

Now, **on your laptop** (not in the container), turn the folder into the team
repo and put it on GitHub. The laptop needs its own git identity and a GitHub
login (GitHub refuses passwords); if you have not done this before, do it once
([`docs/toolkit/git-and-github.md`](../../docs/toolkit/git-and-github.md) §1–2):

```bash
git config --global user.name "Your Name"          # on the laptop, too
git config --global user.email "you@example.com"
gh auth login                                      # GitHub.com → HTTPS → log in with a browser
gh auth setup-git
```

**Pick the owner carefully.** The person who creates the repository owns it,
and in Lab 12 only the owner can register the self-hosted runner. Make the owner
the teammate whose laptop will be "production" in Labs 12–13.

```bash
git init -b main
git add -A
git commit -m "Course drop, week 1"
git ls-files | grep parquet      # must print NOTHING -- data goes to DVC in Lab 8
```

On github.com: create a **private** repository named as the course channel
specifies. Leave **"Add a README" unticked** (an initialised repository rejects
your first push). Under *Settings → Collaborators*, add your two teammates, the
instructor and the TA; each must **accept the invitation** (e-mail or
github.com/notifications) before they can clone. Then:

```bash
git remote add origin <the repo's URL>
git push -u origin main
```

> **Why the data is not in git.** `.gitignore` excludes `data/claims/*.parquet`
> on purpose. In Part C you put it under DVC, which is the point of the lab.
> Each teammate gets the file from their own copy of the zip.

## 2 · The other two teammates — 10 min each

On **each** of the other two laptops, after accepting the invitation and
logging in once (`gh auth login`, `gh auth setup-git`; set your laptop's git
identity too, as in §1):

```bash
unzip AI-in-Practice-2-Lab8.zip -d aip2-drop        # only to get the data
git clone <the team repo's URL> aip2
cp aip2-drop/data/claims/*.parquet aip2/data/claims/
cd aip2
make up
make check
```

Then set your git identity inside the container, as in §1.

From now on **the clone is your working folder**. The `aip2-drop` folder has
done its job.

> **One course container per laptop.** It always serves the folder where you
> last ran `make up`. If `make check` says `claims dataset: missing`, you ran
> `make up` in the wrong folder, or skipped the `cp`.

## 3 · Everyone: a two-minute warm-up

Inside the container (`make shell`, or VS Code → *Reopen in Container* →
a terminal):

```bash
python labs/lab08/rebuild.py --runs 1
```

Under 10 seconds. It rebuilds the supplied model once and compares it with the
shipped pickle. **Do not analyse it yet.** This only confirms that your
environment runs the lab. If it prints a table, you are ready.

## 4 · Read, in this order

| # | File | When | What it is |
|---|---|---|---|
| 1 | `labs/lab08/OVERVIEW.md` | before | **start here.** Why this lab exists, how to approach it |
| 2 | `labs/lab08/README.md` | before | the brief: targets, deliverables, rubric |
| 3 | `theory/T5-notebook-to-production.md` | before | §1–§5 |
| 4 | `supplied_model/MODEL_CARD.md` and `data/claims/DATA_CARD.md` | before | what you were handed |
| 5 | `labs/lab08/RUNSHEET.md` | **in the lab** | the step-by-step. Follow it top to bottom |
| 6 | `labs/lab08/CONCEPTS.md` | **in the lab** | concept → code → theory, for when you are stuck |
| 7 | `labs/lab08/CODE_GUIDE.md` | **in the lab** | what is provided and what is yours, file by file |

Also included: `quizzes/lab8_quiz.html`. Open it in a browser after the lab.
It is not graded and shows no score; we go through the answers together.

## 5 · This lab is in teams of three

Three roles, **rotated at every part**: the *driver* types, the *navigator*
reads the runsheet aloud and says what comes next, the *skeptic* reads every
number aloud, asks "compared to what?", and keeps the notes. Three people
watching one screen and agreeing is not teamwork.

Every deliverable carries a **`CONTRIBUTIONS.md`** signed by all three.
Individual marks may be adjusted where it disagrees with the commit history,
so commit from your own laptop when you drive.

## 6 · Before the lab — checklist

- [ ] Team repo on GitHub, private, instructor and TA added
- [ ] **All three** laptops: repo cloned, data copied in, `make check` clean
- [ ] **All three**: git identity set inside the container
- [ ] **All three**: `rebuild.py --runs 1` prints a table
- [ ] `OVERVIEW.md` read, T5 §1–§5 skimmed

---

## Troubleshooting

### `make check`: `claims dataset ... missing`

The parquet files are not in *this* folder's `data/claims/`. Copy them from the
Lab 8 zip. If they are there, you ran `make up` in a different folder: run it
again here.

### `git ls-files | grep parquet` prints a file

The data was committed to git. Undo it before you push:
`git rm --cached data/claims/*.parquet && git commit -m "Data belongs in DVC"`.

### `git push` asks for a password, or fails inside the container

Push from your laptop's terminal, where your GitHub login lives. The
container deliberately has no GitHub credentials. Committing works in both
places. If the laptop asks for a password, you have not logged in: `gh auth
login`, then `gh auth setup-git`. GitHub does not accept account passwords.

### `git push` is rejected: "fetch first" or "non-fast-forward"

Someone pushed before you: `git pull --no-rebase --no-edit`, then push again.
If the repository was created with a README, this happens on the very first
push, and the pull fails with "refusing to merge unrelated histories": run
`git pull --no-rebase --no-edit --allow-unrelated-histories origin main` once,
then push. Conflicts:
[`docs/toolkit/git-and-github.md`](../../docs/toolkit/git-and-github.md) §4.

### `git commit`: "Please tell me who you are"

The laptop and the container each need the identity, once. In the container:
§1, and `make check` prints the exact command. On the laptop: the same two
`git config --global` lines, in the laptop's terminal. A Mac does not always
refuse: it may commit under a made-up address that GitHub cannot link to you.
Check with `git log -1 --format='%an <%ae>'`.

### Windows: `make: command not found`, or everything is very slow

You are in PowerShell or on `C:\`. Work in the **Ubuntu (WSL 2)** terminal,
with the repo in your Linux home folder. See `START_HERE.md`, *Windows notes*.

### `rebuild.py` fails with `No such file or directory: ... claims.parquet`

Same as the first item: the data is not in this folder.

**Stuck for more than ten minutes? Post on the course channel** with the exact
command and the full error. Do not lose the lab to setup.
