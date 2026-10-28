# Testing with pytest: writing tests from zero

**Who needs this:** everyone, from **Lab 10 Part B onward**. Until now you *ran*
tests somebody else wrote. In Lab 10 Part B you write `tests/test_history.py`
yourself, with no agent; in Lab 11 you write four guard tests against provided
fixtures; Lab 12's CI runs them all on every push. The example service below is
deliberately **not** any lab's solution.

> **The minimum**
> 1. A test is a function named `test_*` in a file named `test_*.py`, containing plain `assert` statements.
> 2. A fixture is a function marked `@pytest.fixture`; a test receives it by naming it as an argument.
> 3. `@pytest.mark.parametrize` turns one test into many, one per input.
> 4. Test a FastAPI app in-process with `with TestClient(app) as c:`; load `app.py` by path, as `labs/lab09/test_contract.py` does.
> 5. Watch every test fail once before you trust it. Never edit a provided test to make it pass.

Everything below was run in the course container (pytest 9.1.1, FastAPI 0.141.1,
Pydantic 2.13.5, Python 3.12.14) in a throwaway folder, `/tmp/pt`. Outputs are
trimmed, not edited. In the labs you run pytest the same way, inside the
container from `/workspace`: `MODEL_DIR=artifacts/bundle pytest -q labs/lab09/test_contract.py`.

## 1 · The example service

`POST /quote` takes a weight and a zone and returns a price in rupees; `GET /ready`
reports the rate card. The card is read at start-up from `RATES_PATH` (default
`rates.json` beside the app, here `{"A": 40, "B": 65, "C": 90}`), the way the
lab services read `MODEL_DIR` or `DATA_DIR`. Layout: `/tmp/pt/app.py`,
`/tmp/pt/rates.json`, and the tests in `/tmp/pt/tests/`. Test counts quoted
before section 8 are for the folder with every test file on this page except
section 8's.

```python
# app.py
"""Parcel quotes: the example service for the pytest primer."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

RATES: dict[str, float] = {}          # zone -> rupees per kg, loaded at startup


def price(weight_kg: float, zone: str, rates: dict[str, float], express: bool = False) -> float:
    """Rs 20 handling plus the zone's rate per kg; express costs 1.5 times as much."""
    if zone not in rates:
        raise ValueError(f"unknown zone {zone!r}")
    total = 20 + rates[zone] * weight_kg
    return round(total * 1.5 if express else total, 2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = Path(os.environ.get("RATES_PATH", Path(__file__).with_name("rates.json")))
    RATES.update(json.loads(path.read_text()))
    yield
    RATES.clear()


app = FastAPI(lifespan=lifespan)


class Parcel(BaseModel):
    weight_kg: float = Field(gt=0, le=30)
    zone: Literal["A", "B", "C"]
    express: bool = False


class Quote(BaseModel):
    zone: str
    price_inr: float


@app.get("/ready")
def ready() -> dict:
    return {"ready": bool(RATES), "zones": sorted(RATES)}


@app.post("/quote")
def quote(parcel: Parcel) -> Quote:
    return Quote(zone=parcel.zone,
                 price_inr=price(parcel.weight_kg, parcel.zone, RATES, parcel.express))
```

## 2 · First tests, and running them

**Discovery.** `pytest` (or `pytest some/folder`) collects files named
`test_*.py` or `*_test.py`, and in them functions named `test_*`. A test passes
if it returns without an exception; a failing `assert` is an exception. There is
no `assertEqual`: write the comparison you mean.

```python
# tests/test_price.py
import pytest

RATES = {"A": 40.0, "B": 65.0}


def test_zone_a(app_module):
    assert app_module.price(2, "A", RATES) == 100.0          # 20 + 40 x 2, by hand


def test_express_costs_half_as_much_again(app_module):
    assert app_module.price(2, "A", RATES, express=True) == 150.0


def test_unknown_zone_is_refused(app_module):
    with pytest.raises(ValueError, match="unknown zone"):
        app_module.price(1, "Z", RATES)
```

`app_module` is a fixture (section 4) holding the loaded `app.py`. The expected
values were **worked out by hand from the rule**, never copied from what the code
returned: a test that takes its answer from the code under test can only confirm
that the code does what it does. `pytest.raises` passes only if the block raises
that exception type; `match` is a regular expression searched in the message.

| You want | Type |
|---|---|
| everything, one line per file | `pytest` → `tests/test_price.py ...` and so on, then `18 passed in 0.06s` |
| quiet output (one character per test) | `pytest -q` → `18 passed in 0.04s` |
| list what would run, without running it | `pytest --collect-only -q` |
| one test | `pytest -q tests/test_price.py::test_zone_a` |
| one parametrized case (quote it) | `pytest -q "tests/test_quote.py::test_malformed_is_422[too heavy]"` |
| tests whose name matches an expression | `pytest -q -k "malformed and zone"` → `2 passed, 16 deselected` |
| stop at the first failure / rerun last failures | `pytest -x` / `pytest --lf` |
| see `print()` output | `pytest -s` |

In `-q` output, `.` is a pass, `F` a failed test, and `E` an **error in setup**
(usually a fixture) before the test body ran.

## 3 · Reading a failure

Change the express multiplier in `app.py` from 1.5 to 1.4 and run again:

```console
$ pytest -q
.F...F............                                                       [100%]
=================================== FAILURES ===================================
____________________ test_express_costs_half_as_much_again _____________________

    def test_express_costs_half_as_much_again(app_module):
>       assert app_module.price(2, "A", RATES, express=True) == 150.0
E       AssertionError: assert 140.0 == 150.0
E        +  where 140.0 = <function price at 0xffffacb7dc60>(2, 'A', {'A': 40.0, 'B': 65.0}, express=True)

tests/test_price.py:12: AssertionError
=========================== short test summary info ============================
FAILED tests/test_cases_yaml.py::test_case[express to zone C] - AssertionErro...
FAILED tests/test_price.py::test_express_costs_half_as_much_again - Assertion...
2 failed, 16 passed in 0.06s
```

Read it bottom-up: the summary names the failing tests; each block shows the
line marked `>`, then `E` lines with both sides (`140.0 == 150.0`) and where the
left one came from. Add a message after a comma (`assert r.status_code == 200, r.text`)
when the values alone will not explain the failure. With `-x` the run stops
at the first `F` (`1 failed, 1 passed`).

## 4 · Fixtures

A fixture builds something a test needs. The test asks for it by **naming it as
a parameter**; pytest runs the fixture and passes in the result. If it `yield`s,
the code after `yield` runs afterwards (tear-down). Fixtures in `conftest.py`
are visible to every test file in that folder without importing; Lab 9 and
Lab 11 put theirs in the test file itself. Both work.

```python
# tests/conftest.py
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture(scope="module")
def app_module():
    spec = importlib.util.spec_from_file_location("app", APP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def client(app_module):
    with TestClient(app_module.app) as c:
        yield c
```

**Scope** is how often a fixture is built. The default, `function`, builds a
fresh one per test; `scope="module"` builds it once per test file and shares it,
which is what you want for something slow, like loading a model:

```python
# tests/test_scope.py
import pytest

built = {"function": 0, "module": 0}


@pytest.fixture
def per_test():
    built["function"] += 1
    return built["function"]


@pytest.fixture(scope="module")
def per_module():
    built["module"] += 1
    return built["module"]


@pytest.mark.parametrize("i", [1, 2, 3])
def test_scopes(i, per_test, per_module):
    print(f"test {i}: function fixture built {per_test}x, module fixture built {per_module}x")
```

```console
$ pytest -q -s tests/test_scope.py
test 1: function fixture built 1x, module fixture built 1x
.test 2: function fixture built 2x, module fixture built 1x
.test 3: function fixture built 3x, module fixture built 1x
.
3 passed in 0.00s
```

The price of sharing: a module-scoped fixture is **the same object** in every
test, so a test that changes it changes it for the tests after it.

**Two built-in fixtures.** `tmp_path` is a fresh, empty folder for this test.
`monkeypatch.setenv(NAME, value)` sets an environment variable **and undoes it
after the test**, which `os.environ[...] = ...` does not:

```python
# tests/test_config.py
import json

from fastapi.testclient import TestClient


def test_rate_card_comes_from_rates_path(app_module, tmp_path, monkeypatch):
    card = tmp_path / "rates.json"
    card.write_text(json.dumps({"A": 10}))
    monkeypatch.setenv("RATES_PATH", str(card))
    with TestClient(app_module.app) as c:
        assert c.get("/ready").json()["zones"] == ["A"]
        assert c.post("/quote", json={"weight_kg": 1, "zone": "A"}).json()["price_inr"] == 30.0
```

Both are function-scoped. A module-scoped fixture that asks for `tmp_path` gets
an `E`, not an `F`: `ScopeMismatch: You tried to access the function scoped
fixture tmp_path with a module scoped request object.` Use
`tmp_path_factory.mktemp("name")` there instead.

## 5 · One test, many inputs: `parametrize`

"Every malformed request gets a 422" is one rule with many cases. Write the rule
once and list the cases:

```python
# tests/test_quote.py
import pytest


def test_ready(client):
    assert client.get("/ready").json() == {"ready": True, "zones": ["A", "B", "C"]}


def test_quote_zone_b(client):
    r = client.post("/quote", json={"weight_kg": 1.5, "zone": "B"})
    assert r.status_code == 200, r.text
    assert r.json() == {"zone": "B", "price_inr": 117.5}       # 20 + 65 x 1.5


MALFORMED = {
    "missing zone":       {"weight_kg": 2},
    "unknown zone":       {"weight_kg": 2, "zone": "Z"},
    "zero weight":        {"weight_kg": 0, "zone": "A"},
    "too heavy":          {"weight_kg": 31, "zone": "A"},
    "string for weight":  {"weight_kg": "two", "zone": "A"},
    "empty object":       {},
}


@pytest.mark.parametrize("case", MALFORMED)
def test_malformed_is_422(client, case):
    r = client.post("/quote", json=MALFORMED[case])
    assert r.status_code == 422, f"{case}: got {r.status_code} {r.text[:200]}"
    assert r.json()["detail"], "a 422 must say what is wrong"
```

Each key becomes its own test with its own ID (`test_malformed_is_422[too heavy]`),
so a failure names the case. This is the shape of Lab 9's
`test_malformed_is_422_never_500`. FastAPI's 422 says what was wrong:
`{'type': 'less_than_equal', 'loc': ['body', 'weight_kg'], 'msg': 'Input should be less than or equal to 30', ...}`.

## 6 · Testing a FastAPI app: `TestClient`

`fastapi.testclient.TestClient(app)` calls your app **in the same process**, with
no server and no port; `client.get(...)` and `client.post(..., json=...)` return a
response with `.status_code`, `.json()` and `.text`. Lab 9's test uses it when
`BASE_URL` is unset, and an `httpx.Client` against the running container when it
is set; the tests themselves do not change.

**Use it in a `with` block**, which runs the app's start-up (`lifespan`), where a
service loads its model or data. Without it:

```python
def test_without_with(app_module):
    c = TestClient(app_module.app)          # no "with": start-up never runs
    print(c.get("/ready").json())
    r = c.post("/quote", json={"weight_kg": 1, "zone": "A"})
```

It prints `{'ready': False, 'zones': []}` and fails with
`ValueError: unknown zone 'A'`: the rate card is empty. Note that the error arrived **as a Python exception in
the test**, not as a 500: `TestClient` re-raises server errors so you get the
traceback. With `TestClient(app, raise_server_exceptions=False)` the same call
returns `500 Internal Server Error`, as a real caller would see.

## 7 · Loading `app.py` by its path: Lab 9's loader, line by line

`labs/lab09/test_contract.py`, lines 45–53 (Lab 10 asks you to copy this):

```python
        from fastapi.testclient import TestClient
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", Path(__file__).with_name("app.py"))
        mod = importlib.util.module_from_spec(spec)
        import sys
        sys.modules["app"] = mod          # Pydantic resolves annotations via sys.modules
        spec.loader.exec_module(mod)
        with TestClient(mod.app) as c:
            yield c
```

| Line | What it does |
|---|---|
| `spec_from_file_location("app", <path>)` | "a module called `app` whose source is **this file**". `with_name("app.py")` means `app.py` beside the test; from a `tests/` subfolder go up one level, as `conftest.py` above does |
| `module_from_spec(spec)` | creates an empty module object; nothing has run yet |
| `sys.modules["app"] = mod` | registers it under the name `app`, as `import` would |
| `spec.loader.exec_module(mod)` | runs `app.py` top to bottom inside `mod`: imports, models, `app = FastAPI(...)` |
| `with TestClient(mod.app) as c: yield c` | starts the app (section 6), lends the client to the tests, shuts it down after the last |

**Why not just `import app`?** Several labs have an `app.py`, and Python keeps
one module per name, so in one pytest session the first `app` imported wins.
Measured, with two folders each holding an `app.py` and a test doing `import app`:

```console
$ pytest -q lab_a          # 1 passed
$ pytest -q lab_b          # 1 passed
$ pytest -q lab_a lab_b
FAILED lab_b/test_b.py::test_name - AssertionError: assert 'lab_a' == 'lab_b'
```

`lab_b`'s test silently tested `lab_a`'s app. Loading by path removes the doubt.

**Why the `sys.modules` line?** Under `from __future__ import annotations` (top
of the example and the lab apps), type hints are stored as strings, and Pydantic
resolves them by finding the module in `sys.modules`. Delete that one line from
`conftest.py` and:

```console
E       pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[app.Parcel, ...]]` is not fully defined; you should define ...
11 failed, 7 passed in 1.49s
```

Loading succeeds; every test that posts a parcel then fails, while `/ready` and
the `price()` tests pass. The error surfaces far from its cause.

## 8 · Write the test first, and watch it fail

> A test you have never seen fail is a hope, not a test.

A new rule: *express parcels may weigh at most 20 kg*. Test first:

```python
# tests/test_express_limit.py
def test_express_over_20kg_is_422(client):
    r = client.post("/quote", json={"weight_kg": 25, "zone": "A", "express": True})
    assert r.status_code == 422, r.text
    assert "at most 20 kg" in r.text
```

```console
$ pytest -q tests/test_express_limit.py
E       AssertionError: {"zone":"A","price_inr":1530.0}
E       assert 200 == 422
1 failed in 0.02s
```

Red **for the right reason**: the service accepted the parcel. (Red because of an
`ImportError` or a typo in the test proves nothing.) Now the code, inside
`Parcel`, with `model_validator` added to the pydantic import:

```python
    @model_validator(mode="after")
    def express_weight_limit(self) -> Parcel:
        if self.express and self.weight_kg > 20:
            raise ValueError("express parcels may weigh at most 20 kg")
        return self
```

`pytest -q` → `19 passed in 0.05s`. This is Lab 10 Part B's order: spec, tests
run red and committed, then the code. For a test written after the code, break
the code on purpose (as in section 3) and check the test goes red.

## 9 · Contract tests driven by a file

When the cases are data, keep them as data: a YAML file lists requests and what
must come back, and one parametrized test runs them all. (Lab 16 does this for
MCP tools with `contracts/<pack>.yaml`, read by a provided script.)

```yaml
# tests/cases.yaml
# One case per line of the spec. Expected values worked out by hand.
cases:
  - name: two kilos to zone A
    request: {weight_kg: 2, zone: A}
    status: 200
    body: {price_inr: 100.0}
  - name: express to zone C
    request: {weight_kg: 1, zone: C, express: true}
    status: 200
    body: {zone: C, price_inr: 165.0}
  - name: over the weight limit
    request: {weight_kg: 30.5, zone: B}
    status: 422
```

```python
# tests/test_cases_yaml.py
from pathlib import Path

import pytest
import yaml

CASES = yaml.safe_load(Path(__file__).with_name("cases.yaml").read_text())["cases"]
KEYS = {"name", "request", "status", "body"}


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_case(client, case):
    assert not set(case) - KEYS, f"typo in cases.yaml? {set(case) - KEYS}"
    r = client.post("/quote", json=case["request"])
    assert r.status_code == case["status"], r.text
    for key, want in case.get("body", {}).items():
        assert r.json()[key] == want, key
```

**Why the `KEYS` line.** Without it, misspell `body` as `bdy` and that case
checks only the status code. Measured: with the 1.4 bug from section 3 in the app
*and* that typo, all 3 cases passed. With the line, the typo is caught:
`AssertionError: typo in cases.yaml? {'bdy'}`. A data-driven test must refuse
data it does not understand, or it passes on nothing.

## 10 · What not to do

- **Do not edit a provided test to make it pass.** Lab 9's contract test, Lab 10's
  client acceptance tests and Lab 8's checker say so at the top. A passing run
  against a test you changed proves nothing, and the Lab 10 runsheet checks that
  `git diff --stat -- '*test*'` is empty.
- Do not take expected values from the service under test, catch the exception
  you are testing for with `try/except: pass` (use `pytest.raises`), or set
  environment variables with `os.environ` in a test (use `monkeypatch.setenv`).
- Do not delete a red test, or leave Lab 11's `pytest.fail("yours ...")`
  placeholders in place. (Lab 16's `contract_test.py` is a script: run it with
  `python`, not `pytest`.)

## Try it (10 minutes)

In the container, in `/tmp` (not `/workspace`):

1. Create `/tmp/pt` with `app.py`, `rates.json` and `tests/conftest.py` from above.
2. Add `test_price.py` and `test_quote.py`; `pytest -q` should say `11 passed`.
3. Change the handling fee in `price()` from 20 to 25. Three tests should fail
   (`assert 105.0 == 100.0` is one). Which tests did not notice, and why? Put it back.
4. Write the express-limit test, see `assert 200 == 422`, add the validator,
   see it pass.
5. Add `cases.yaml` and `test_cases_yaml.py`; misspell a key and check the
   guard catches it.

## If it goes wrong

| Symptom | Cause and fix |
|---|---|
| `collected 0 items` | file not named `test_*.py`, or function not named `test_*` |
| `fixture 'client' not found` | the fixture is in another test file. Move it to `conftest.py` in the same folder, or define it here |
| `E` instead of `F`, `ERROR at setup of ...` | a fixture failed before the test ran. Read the fixture's traceback |
| `ScopeMismatch: ... function scoped fixture tmp_path with a module scoped request object` | a module-scoped fixture asked for `tmp_path` or `monkeypatch`. Use `tmp_path_factory`, or make it function-scoped |
| `PydanticUserError: ... is not fully defined` | `app.py` loaded by path without `sys.modules["app"] = mod` before `exec_module` |
| a test sees another lab's app | `import app` found the wrong `app.py`. Load it by path (section 7) |
| `/ready` not ready, or errors from empty start-up state | `TestClient(app)` used without `with`, so start-up never ran |
| `FileNotFoundError` for the model or data | the env var (`MODEL_DIR`, `DATA_DIR`, `HISTORY_PATH`) is not set. Put it before `pytest`, as each runsheet shows |
| green, but you never saw it fail | break the code on purpose and rerun. If it stays green, it tests nothing |
