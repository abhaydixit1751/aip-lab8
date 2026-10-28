# Git and GitHub for this course

**Who needs it:** everyone, **before Lab 8** (§1–§2 are the setup). Used in
Labs 8–21: you commit, pull, push and tag every week. Lab 10 leans on §5
(branches), Lab 12 on §7 (revert) and §2.2 (the runner).

> **The minimum**
> ```bash
> git config --global user.name "Your Name"; git config --global user.email you@example.com  # laptop AND container
> git status                                    # before and after everything
> git add -A && git commit -m "Lab 8: what and why"
> git pull --no-rebase --no-edit && git push    # on the laptop
> git tag lab08 && git push origin lab08        # deliverables are graded by tag
> ```

Every output below is real (trimmed with `...`): git 2.47.3 in the course container,
git 2.50.1 on a macOS laptop, a bare repo standing in for GitHub and two clones
for two teammates. Anything that needs GitHub itself is marked **(not run here)**.

## 0 · Where git runs

| | Laptop | Course container |
|---|---|---|
| `status`, `add`, `commit`, `diff`, `log`, `tag`, `revert` | yes | yes: the same repo, mounted at `/workspace` |
| `clone`, `pull`, `push`, `fetch` (talk to GitHub) | **yes** | no: no GitHub credentials, on purpose |
| Editor for commit messages | `vi` (macOS default) | **none**: anything that opens one fails (§1.3) |

## 1 · One-time setup

**Install** (not run here). macOS: `xcode-select --install` (gives `git` and
`make`). WSL Ubuntu: `sudo apt update && sudo apt install -y git make unzip`.
`git --version` must be 2.28 or later for `git init -b main`.

### 1.1 Who you are, in both places

```bash
git config --global user.name "Asha Rao"
git config --global user.email "asha@example.com"   # the email on your GitHub account
```

Run it **on the laptop** and **inside the container** (`make shell`; it
survives `make down`). Use your GitHub email so commits are credited to you:
`CONTRIBUTIONS.md` is checked against the commit history. In the container,
without it, the commit fails:

```
*** Please tell me who you are.
...
fatal: unable to auto-detect email address (got 'student@78efde246f0f.(none)')
```

On a **macOS laptop it does not fail**, which is worse: the commit goes through
under an invented address GitHub cannot link to you (`Committer: Your Name
<you@Your-Mac.lan>` ... `configured automatically based on your username and
hostname`). If you have not pushed yet, set the identity, then
`git commit --amend --reset-author --no-edit` rewrites that commit.

### 1.2 Two defaults, also in both places

```bash
git config --global pull.rebase false        # git pull merges; it never stops to ask (§3)
git config --global init.defaultBranch main  # without it, git init makes "master"
git config --global --list                   # check
```

### 1.3 The container has no editor

Any git command that wants to open an editor fails in an interactive container shell:

```
$ git revert HEAD
hint: Waiting for your editor to close the file... error: cannot run editor: No such file or directory
error: unable to start editor 'editor'
```

A merging `git pull`, and `git commit` without `-m`, fail the same way. The
rule: **`-m` on every commit, `--no-edit` on every pull, merge and revert.**
If you already hit the error, the change is staged but not committed:
`git commit --no-edit` finishes it with git's default message (measured for a
merge and a revert). On a macOS laptop the same commands open `vi` instead
(`Esc`, `:wq`, Enter; not run here). `git log` opens a pager: `q` quits.

## 2 · GitHub

### 2.1 Log in on the laptop (not run here)

GitHub refuses your account password for git. Use the GitHub CLI:

```bash
brew install gh                              # macOS
sudo apt update && sudo apt install -y gh    # Ubuntu / WSL (if apt has none: cli.github.com's apt repo)
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git                            # git now asks gh for credentials
gh auth status
```

`--web` shows a one-time code and opens a browser (on WSL, if none opens, paste
the URL into a Windows browser). The `workflow` scope matters in Lab 12: GitHub
refuses a push that changes `.github/workflows/ci.yml` from a token without it.

**Alternative:** a personal access token, *classic*, scopes `repo` and
`workflow` (GitHub → Settings → Developer settings). Paste it when git asks for
a password. Homebrew's git on macOS keeps it in the Keychain (measured:
`credential.helper=osxkeychain` is preset); on WSL, install Git Credential
Manager so you are not asked every time. A fine-grained token cannot reach a
repo owned by another person's account. Never give the container credentials.

### 2.2 The team repo: one teammate creates it

**Who:** the teammate whose laptop will be *production* in Lab 12. Registering
the runner (Settings → Actions → Runners) needs **admin**, and on a personal
repository only the owner has it; collaborators do not see Settings at all.

On github.com (not run here): **New repository** → Private → leave **Add a
README**, `.gitignore` and licence **unticked** → Create. **Settings →
Collaborators → Add people**: two teammates, the instructor, the TA. Each must
**accept the invitation** (e-mail, or `github.com/<owner>/<repo>/invitations`);
until then their `git clone` says `Repository not found`.

Then, in the unzipped course folder, **on the laptop** (START_HERE_LAB8 §1):

```bash
git init -b main
git add -A
git commit -m "Course drop, week 1"
git ls-files | grep parquet       # must print nothing
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main           # -u: plain git push / git pull use origin main from now on
```

**If you ticked "Add a README"**, GitHub has a commit you do not: the push is
`rejected (fetch first)`, and `git pull --no-rebase --no-edit origin main` says
`fatal: refusing to merge unrelated histories`. Fix:
`git pull --no-rebase --no-edit --allow-unrelated-histories origin main`, then
`git push -u origin main`. The other two: `git clone <the URL> aip2`.

## 3 · The daily loop

```bash
git pull --no-rebase --no-edit      # laptop: before you start a part
# ... work and run things in the container ...
git status                          # what changed? anything that should not go in?
git add -A                          # everything not ignored (or name the files)
git commit -m "Lab 8: fix row order in load_data"
git pull --no-rebase --no-edit      # laptop: take your teammates' work first
git push                            # laptop. The driver commits as themselves: history is evidence
```

**`! [rejected] main -> main (fetch first)`**: someone pushed since your last
pull ("the remote contains work that you do not have locally"). Pull, then
push. `(non-fast-forward)` is the same, when you have fetched their commits but
not merged them.

**`fatal: Need to specify how to reconcile divergent branches`**: you both
committed since the last pull, and without `pull.rebase false` (§1.2) git will
not choose how to combine them. `git pull --no-rebase --no-edit` joins the two
lines with a merge commit (`Merge made by the 'ort' strategy`):

```
$ git log --oneline --graph
*   2755d77 Merge branch 'main' of /tmp/gp/team
|\
| * a90fbfe Ben: notes
* | ce70b2d Asha: report
|/
* b4020aa Course drop
```

## 4 · Conflicts

A conflict is two commits changing the **same lines**. Asha set `lr: 0.2`,
Ben set `lr: 0.05` and pushed first:

```
$ git pull --no-rebase --no-edit
CONFLICT (content): Merge conflict in params.yaml
$ cat params.yaml
run_name: base
<<<<<<< HEAD
lr: 0.2
=======
lr: 0.05
>>>>>>> 96be630c4f2c37700eb3c819fbd9aeb1fb59017a
```

Above `=======` is yours (`HEAD`); below is what you pulled. Agree which is
right, edit the file to the final text **with the marker lines gone**, then
`git add params.yaml && git commit --no-edit && git push`. `git status` lists
every conflicted file as "both modified". To back out: `git merge --abort`.

### Lock files: never merge by hand

Take one side whole, then regenerate. In a merge, `--ours` is your laptop's
version and `--theirs` the one you pulled.

```bash
# uv.lock -- two people added dependencies
#   1. fix pyproject.toml by hand: keep both dependencies, remove the markers
git checkout --theirs uv.lock          # 2. either side, whole
uv lock                                # 3. in the container: re-resolve
git add pyproject.toml uv.lock && git commit --no-edit
```

Measured: `Resolved 4 packages ... Added certifi v2025.8.3`; the new lock names
both teammates' packages. Then `make rebuild` on every laptop (START_HERE).

```bash
# dvc.lock -- two people changed the pipeline
#   1. fix params.yaml by hand: the value you agreed
git checkout --ours dvc.lock metrics.json   # 2. either side, whole
dvc repro                                   # 3. in the container: "Updating lock file 'dvc.lock'"
git add params.yaml dvc.lock metrics.json && git commit --no-edit   # ("didn't change, skipping" is fine too)
dvc push
```

## 5 · Branches, safely

A branch is a movable name for a line of commits. **Uncommitted changes belong
to no branch**: they stay in your folder and follow you across `git switch`.
The Lab 10 Part A trap, measured:

```
$ git switch -c lab10-part-a
$ echo "def predict(): return 'starter'" > app.py   # stands in for the cp and the agent
$ echo "agent scratch" > scratch_notes.txt
$ git switch main
M	app.py
$ git branch -D lab10-part-a
Deleted branch lab10-part-a (was abdd4da).
$ git status --short
 M app.py
?? scratch_notes.txt
$ cat app.py                              # your Lab 9 solution is gone from the folder:
def predict(): return 'starter'
```

Recovery: `git restore app.py`, then `git clean -n` and `git clean -fd` (§7).
**The safe way is to commit on the branch before you leave it:**

```bash
git switch -c lab10-part-a
cp labs/lab10/part_a/lab09_app_starter.py labs/lab09/app.py
git commit -am "Lab 10 Part A: starter"     # the agent's diff is now against the starter
# ... the agent works; you review git diff --stat ...
git add -A -- ':!reports'                   # everything except your notes (they stay untracked)
git commit -m "Lab 10 Part A: the agent's attempt"
git switch main
git branch -D lab10-part-a                  # -D: delete although never merged
git status                                  # only reports/ is new; your Lab 9 app.py is back
```

Why `':!reports'`: a file committed only on the branch disappears from the
folder when you switch away, so `defects.md` and `agent_log.md`, written during
Part A, must not go into the branch's commit (measured: they survive this way).

`git branch -d` (lower case) refuses an unmerged branch (`not fully merged`):
that is the safety catch. **Or stash:** `git stash -u` shelves every
uncommitted change, untracked files included, and leaves the folder clean;
`git stash pop` brings it back, `git stash drop` throws it away. If an
uncommitted file differs between the branches, git refuses to switch at all
(`would be overwritten by checkout`): commit or stash.

## 6 · Tags

A tag is a fixed name for one commit: a branch moves when you commit, a tag
does not. **Deliverables are graded at the commit the tag on GitHub points to.**

```bash
git tag lab08                    # tags the commit you are on (HEAD)
git push origin lab08            # or git push --tags: all of them
git ls-remote --tags origin      # what the remote has
```

**A late fix.** Commit and push the fix, then move the tag:

```
$ git tag lab08
fatal: tag 'lab08' already exists
$ git tag -f lab08
Updated tag 'lab08' (was 979f3ca)
$ git push --tags
 ! [rejected]        lab08 -> lab08 (already exists)
$ git push origin -f refs/tags/lab08
 + 979f3ca...8e35769 lab08 -> lab08 (forced update)
```

Or delete and push again: `git push origin --delete lab08 && git push origin lab08`.

**Teammates keep the old tag.** Measured: `git pull` updated Ben's `main` but
silently left his `lab08` on the old commit, and `git fetch --tags` refused
with `(would clobber existing tag)`. He needs `git fetch --tags --force`.

## 7 · Undoing

| Situation | Command |
|---|---|
| Edited a file, want the committed version | `git restore <path>` (older spelling: `git checkout -- <path>`) |
| Staged it by mistake | `git restore --staged <path>` (keeps the edit) |
| New files you or an agent created | `git clean -n <dir>` to list, then `git clean -fd <dir>` |
| A bad commit, already pushed | `git revert --no-edit <sha>`, then push |

**`restore` and `checkout --` touch only files git already tracks.** Lab 10's
"revert the agent's test edits":

```
$ git checkout -- labs/lab10/tests
$ git status --short
?? labs/lab10/tests/test_agent_added.py       # the file the agent added survives
$ git clean -n labs/lab10/tests
Would remove labs/lab10/tests/test_agent_added.py
$ git clean -fd labs/lab10/tests                # deletes for good: always -n first
```

**Revert (Lab 12).** Find the sha, then revert that commit:

```
$ git log --oneline -3
44e40b0 Unrelated later commit
e61aeb8 Lab 12: learning_rate 0.5 (gate should catch)
7a14df1 Lab 10: spec and red tests
$ git revert --no-edit e61aeb8
[main 3a6b5e4] Revert "Lab 12: learning_rate 0.5 (gate should catch)"
```

A revert is a **new commit** that undoes an old one: history only grows,
teammates pull it like any other, and CI tests and ships it (Lab 12 D2).
`git reset --hard <sha>` instead removes commits from your copy; on a branch
others have pulled, your push is then rejected, and forcing it deletes their
work and the record of what was released. On `main`: revert, never reset.

**`git revert HEAD` reverts whatever is newest.** Straight after a revert, HEAD
*is* that revert, and reverting it puts the change back (measured:
`Reapply "Lab 12: learning_rate 0.5 ..."`). Read `git log --oneline -3` first.

## 8 · Reading history

| Question | Command |
|---|---|
| What happened, in order? | `git log --oneline --graph -10` |
| Which files did each commit touch? | `git log --stat -3` |
| Who changed this file, when? | `git log --oneline -- labs/lab08/params.yaml` |
| What have I changed, not committed? | `git diff` (staged: `git diff --staged`; summary: `--stat`) |
| What changed since the deliverable? | `git diff lab08 --stat` |
| A file as it was at a tag or commit | `git show lab09:labs/lab08/params.yaml` |
| Find a commit by its message | `git log --oneline --grep='spec and red tests'` |

Lab 10 D1 feeds the last one into `git diff` with `$(...)` (shell primer):
`git diff "$(git log --format=%H -1 --grep='spec and red tests')"`. `%H` is the
full sha, `-1` the newest match. If no message matches, `$(...)` is empty and git
fails with `fatal: ambiguous argument ''`: check with `--oneline --grep` first.

## Try it (10 minutes)

In the container (`make shell`), after §1. A bare repo plays GitHub; `asha` and
`ben` play two laptops. Nothing here touches your team repo.

```bash
cd /tmp && rm -rf try && mkdir try && cd try
git init -q --bare team.git
git clone -q team.git asha && cd asha
echo "lr: 0.1" > params.yaml && git add -A && git commit -m "start" && git push -u origin main
cd .. && git clone -q team.git ben
cd ben && echo "lr: 0.05" > params.yaml && git commit -am "Ben: lr" && git push && cd ../asha
echo "lr: 0.2" > params.yaml && git commit -am "Asha: lr"
git push                               # 1. rejected (fetch first)
git pull --no-rebase --no-edit         # 2. CONFLICT
cat params.yaml                        # 3. read the markers, then resolve:
echo "lr: 0.05" > params.yaml && git add params.yaml && git commit --no-edit
git push && git log --oneline --graph  # 4. the merge
git tag lab00 && git push origin lab00
(cd ../ben && git pull --no-edit)      # 5. Ben now has lab00 too
echo "lr: 0.07" > params.yaml && git commit -am "late fix" && git push
git tag -f lab00 && git push origin -f refs/tags/lab00               # 6. move the tag
git revert --no-edit HEAD && git log --oneline -3                    # 7. undo the late fix
```

Then: which commit is `lab00` in `git ls-remote --tags origin`, and in `../ben` after
`git pull --no-edit`, then after `git fetch --tags --force` (`git rev-parse --short lab00`)? Why?

## If it goes wrong

| You see | Meaning and fix |
|---|---|
| `*** Please tell me who you are.` | No identity in this place (laptop or container): §1.1 |
| `Committer: ... <you@Your-Mac.lan>` | macOS invented an identity: §1.1, then `git commit --amend --reset-author --no-edit` if not pushed |
| `unable to start editor 'editor'` / `Terminal is dumb, but EDITOR unset` | No editor in the container: `git commit --no-edit` finishes the half-done merge or revert; next time `-m` / `--no-edit` |
| A screen of `~` on the laptop (vi) | `Esc`, `:wq`, Enter (not run here). Next time `--no-edit` |
| `Need to specify how to reconcile divergent branches` | `git pull --no-rebase --no-edit`; set `pull.rebase false` (§1.2) |
| `! [rejected] main -> main (fetch first)` / `(non-fast-forward)` | Teammates pushed: pull, then push |
| `refusing to merge unrelated histories` | Repo created with a README: §2.2 |
| `Your local changes ... would be overwritten by merge` (or `checkout`) | Commit or `git stash -u` first |
| `CONFLICT (content)` / `you have unmerged files` | §4: edit, `git add`, `git commit --no-edit`; or `git merge --abort` |
| `Authentication failed`, `Permission denied`, `password authentication was removed` | No GitHub login here, or you are in the container: §2.1 on the laptop (not run here) |
| `Repository not found` | Invitation not accepted, wrong URL, or another account (`gh auth status`) (not run here) |
| `refusing to allow ... to create or update workflow` | Token lacks `workflow`: `gh auth refresh -s workflow` (not run here) |
| `tag 'lab08' already exists` / `! [rejected] lab08 -> lab08 (already exists)` | Moving it on purpose? `git tag -f lab08`, `git push origin -f refs/tags/lab08` (§6) |
| `(would clobber existing tag)` | `git fetch --tags --force` |
| `the branch '...' is not fully merged` | `git branch -D` if you mean to throw it away |
| `fatal: ambiguous argument ''` | An empty `$(...)`: the `--grep` matched nothing (§8) |
