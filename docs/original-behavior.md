# Original SeasonSwitch: observed behavior (owned by P3)

Built and run from `java/src/original/java/cse4392/SeasonSwitch.java`, JDK 17, Maven 3.10:

```bash
cd java && mvn -P original clean compile
java -Djava.awt.headless=true -cp target/classes cse4392.SeasonSwitch <off|cool|heat|anything>
```

## Command line

| Argument | Output | Exit |
|---|---|---|
| (none) | same as `cool` | never exits on its own |
| `cool` | `Cooling started. RmTemp=70`, then the cooling cycle below | never exits on its own |
| `heat` | `Heating started. RmTemp=70`, then the heating cycle below | never exits on its own |
| `off` | `System off. System exits.` | `System.exit(0)` |
| anything else | `Unknown command. System exits.` | `System.exit(1)` |

`main()` waits on `new CountDownLatch(5).await()`, and nothing ever counts the latch down, so the
program runs until it is killed (Ctrl-C). It does not stop after five seconds. Every command starts
with the banner `Enter off, cool or heat to run. Press Ctrl-c to exit.`

## Observed output (8 seconds each)

```
cool                              heat
Cooling started. RmTemp=70        Heating started. RmTemp=70
Cooling stopped. RmTemp=68        Heating started. RmTemp=72
Cooling started. RmTemp=71        Heating started. RmTemp=75
Cooling stopped. RmTemp=68        Heating stopped. RmTemp=78
Cooling started. RmTemp=71        Heating started. RmTemp=75
...                               Heating stopped. RmTemp=78
```

The room timer fires every 400 ms and the switch timer every 1200 ms, so the temperature moves about
3 degrees between checks. It overshoots the thresholds (78 when heating stops, 71 when cooling
restarts) instead of holding at them.

## Rules the code implements

State is `static int state`, one of `OFF=0`, `COOL=1`, `HEAT=2`, and starts at `OFF`.

| From \ call | `cool()` | `heat()` | `off()` |
|---|---|---|---|
| OFF | AC on, timer start, -> COOL, prints "Cooling started" | heater on, timer start, -> HEAT, prints "Heating started" | nothing |
| COOL | nothing | AC off, heater on, timer start, -> HEAT, prints "Heating started" | AC off, timer stop, -> OFF, prints "Cooling stopped" |
| HEAT | heater off, AC on, timer start, -> COOL, prints "Cooling started" | nothing | heater off, timer stop, -> OFF, prints "Heating stopped" |

`timerOff()` (also reached through `actionPerformed`) does not change the state:

| State | Condition | Effect |
|---|---|---|
| OFF | any | nothing |
| COOL | `room.temp > 68` | AC on, "Cooling started" |
| COOL | `room.temp <= 68` | AC off, "Cooling stopped" |
| HEAT | `room.temp < 77` | heater on, "Heating started" |
| HEAT | `room.temp >= 77` | heater off, "Heating stopped" |

`Room.actionPerformed` (the 400 ms tick): OFF leaves the temperature alone; COOL lowers it by 1 when
the AC is on and raises it by 1 when it's off; HEAT raises it by 1 when the heater is on and lowers it
by 1 when it's off.

Boundaries for BVA: cooling 67 / **68** / 69 (68 is "stop"), heating 76 / **77** / 78 (77 is "stop").

## Coverage baseline

JaCoCo counts 36 branches in the class. `main()` holds 8 of them and is excluded, because it blocks
forever and calls `System.exit`. That leaves **28 branches** to cover:

| Method | Branches |
|---|---|
| `cool()` | 4 |
| `heat()` | 4 |
| `off()` | 4 |
| `timerOff()` | 8 |
| `Room.actionPerformed()` | 8 |

`scripts/coverage.sh original` prints `original <covered> <missed> <pct>` over those 28.

## Things the test writers need to know

- `state` is **static**, so it leaks between tests. Reset `SeasonSwitch.state = SeasonSwitch.OFF`
  before each test.
- Each `SeasonSwitch` creates two Swing `Timer`s. `cool()` and `heat()` start `timer`, so stop it
  (`s.timer.stop()`) or call `off()` at the end of the test, and call `actionPerformed` /
  `timerOff()` directly instead of waiting on real time.
- `room.temp`, `ac.isOn` and `heater.isOn` are package-visible, so tests in package `cse4392` can
  set and read them directly.
- Run headless (`-Djava.awt.headless=true`); Swing `Timer` works without a display.
