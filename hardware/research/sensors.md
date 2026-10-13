# Best Sensors (Owner-Programmable / Self-Calibrating)

Ranked by measurement type. Criteria: public datasheet, I2C/SPI/SDI-12/analog (no locked consumer firmware), **we** write the driver and calibration. Researched 2026-10-12; verify prices before ordering.

## Ranked shortlist

### Temperature / Humidity
| Rank | Part | Specs | Notes |
|---|---|---|---|
| 1 | **SHT41** (Sensirion) | ±1.8% RH, ±0.2 °C, I2C | Best price/accuracy, clean raw-register driver |
| 2 | **HDC3021** (TI) | ±2% RH, ±0.1 °C, I2C | TI accuracy edge, parylene-filtered version available for dirty environments |
| 3 | SHT35 | older SHT4x sibling | fine, no reason over SHT41 |

### Soil moisture
| Rank | Part | Interface | Notes |
|---|---|---|---|
| 1 | **Vegetronix VH400** | Analog | Corrosion-resistant dielectric probe, minimal calibration, ~$30 |
| 2 | **Truebner SMT100** | SDI-12 | ±3%, soil-independent, moderate calibration |
| 3 | METER **TEROS 12** | Modbus/SDI-12 | Research-grade (~$271) — the "real" answer if budget allows |
| alt | bare capacitive PCB probe | Analog | $1–5; we own the full dry/wet curve — most "ours" but least accurate |

### EC / conductivity / nutrients
| Rank | Part | Notes |
|---|---|---|
| 1 | **Raw EC probe (K=1.0, e.g. DFRobot Gravity) + ADS1115** | ~$15–25; we do excitation waveform, temp comp (β≈2.1%/°C), K-factor cal. Fully ours. |
| 2 | Atlas Scientific EZO conductivity kit | ~$89; lab-grade probe, but EZO chip is closed firmware — we'd rather take the probe and skip the chip |
| 3 | Atlas Wi-Fi Hydroponics Kit | $149, same caveat |

**Rule of thumb: buy Atlas Scientific *probes*, skip Atlas *circuits*.** Their electrodes are excellent; their EZO modules are firmware black boxes.

### pH
| Rank | Part | Notes |
|---|---|---|
| 1 | **Generic lab glass electrode (BNC) + ADS1115 high-Z front end** | $5–15 probe; we implement 2–3 pt buffer calibration + temp comp |
| 2 | Atlas consumer pH probe | $49 probe-only |

### Light
| Rank | Part | Notes |
|---|---|---|
| 1 | **OPT4048** (TI) | Tristimulus XYZ (color-accurate lux), I2C, public datasheet, essentially no calibration |
| 2 | TSL2591 | Broadband + IR, good dynamic range |
| 3 | BH1750 | Cheapest, lux only |

### Spectral / plant-level
- **AS7341** — 11 channels (405–680 nm + clear + NIR). Best cheap spectral tool; our own channel-crosstalk handling. ~$15.
- Hamamatsu S1336 photodiodes — research-grade, expensive.
- **Apogee SQ-500** — research quantum PAR sensor, ~$400+; the gold standard if we want true µmol/m²/s.
- BME688 — VOC/IAQ for plant-stress/mold detection; note Bosch's BSEC2 algorithm library is *not* fully open — raw gas resistance channel is, and that's what we'd use.

### Flow / dosing feedback
| Rank | Part | Notes |
|---|---|---|
| 1 | **Sensirion SLF3S-1300F** | I2C liquid flow, 0.04–40 ml/min, public datasheet — ideal fertigation dosing feedback |
| 2 | YF-S201 hall turbine | $5, pulse-count, coarse but fine for irrigation lines |

### Specialty (nice-to-have research-grade)
- **Leaf wetness**: bare interdigitated gold-plated PCB (we can even etch) + ADC — fully our own device.
- **Dendrometer (stem growth)**: OPEnSLab open-source magnetic dendrometer — 3D-printed, cheap.
- **Sap flow**: open heat-pulse designs (dotmote/sapflow).
- **Nitrate**: ISE membrane electrode + ADS1115 — slow (minutes) but ours.

## Top 3 overall picks
1. **SHT41 + Vegetronix VH400 + raw EC probe (ADS1115)** — complete environmental suite, all public datasheets, all calibration ours. ~$60.
2. **AS7341 + BME688 + SLF3S-1300F** — advanced spectral + gas + dosing feedback tier. ~$80.
3. **OPT4048 + HDC3021 + VH400** — simplest robust tier, almost no calibration needed.

See also: [README.md](README.md) (MCUs/power/connectivity), [cameras.md](cameras.md).
