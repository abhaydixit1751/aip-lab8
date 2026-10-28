# The capstone interface, in its generic shape. Run from your laptop, in this folder.
#
#   make up  test  eval  gate  gate-break  down
#
# Recipe lines start with a TAB, not spaces. Each line runs in its own shell.

# Every target here is a command, not a file. Without this line, `make eval`
# does nothing at all, because a directory called eval/ exists.
.PHONY: help up test eval gate gate-break down

COMPOSE  := docker compose
GATE_MIN ?= 1.0

help:
	@echo "make up          build, start, and wait until the service is healthy"
	@echo "make test        unit tests, in the test image"
	@echo "make eval        score the running service on eval/cases.jsonl"
	@echo "make gate        the same, and fail below GATE_MIN (now $(GATE_MIN))"
	@echo "make gate-break  a deliberate regression: the gate must go red"
	@echo "make down        stop and remove the containers (the volume stays)"

up:
	$(COMPOSE) up -d --build --wait api

test:
	$(COMPOSE) --profile test run --rm --build test

eval:
	$(COMPOSE) --profile eval run --rm evaluate

gate:
	$(COMPOSE) --profile eval run --rm evaluate \
	  python /eval/evaluate.py --url http://api:8000 --min $(GATE_MIN)

# Break, run the gate, ALWAYS restore, then exit with the gate's status:
# red (non-zero) means the gate caught the break. One shell line, so that
# $$status survives. In a recipe, $$ is how you write the shell's $.
gate-break:
	@echo ">> deliberate break: GREETING=Hullo. The gate must FAIL."
	GREETING=Hullo $(MAKE) --no-print-directory up gate; status=$$?; \
	$(MAKE) --no-print-directory up; \
	if [ $$status -eq 0 ]; then echo ">> the gate PASSED the break: add a case that catches it"; \
	else echo ">> the gate caught the break (and the service is restored)"; fi; \
	exit $$status

down:
	$(COMPOSE) down
