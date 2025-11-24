# CPU Thermal Throttling Analysis Case Study

## Overview

This document captures a real-world thermal throttling investigation that revealed a critical insight: **CPU package temperature can be significantly higher than average core temperature**, causing throttling even when core temps appear acceptable.

## Initial Investigation

### Initial Findings

Analysis of the sensor data revealed severe thermal throttling:

```
=== CPU THROTTLING ANALYSIS ===

Analyzed 100 samples from the sensor log

1. THERMAL THROTTLING: 97/100 samples (97.0%)
2. POWER LIMIT EXCEEDED: 12/100 samples (12.0%)

=== TEMPERATURE ===
Average: 74.8°C
Maximum: 89.0°C
Minimum: 66.0°C

=== IA THROTTLING REASONS (Active) ===
  - IA: Thermal Event: 89/100 (89.0%)
  - IA: Package-Level RAPL/PBM PL2,PL3: 12/100 (12.0%)
  - IA: Max Turbo Limit: 100/100 (100.0%)

=== POWER CONSUMPTION ===
Average: 25.1W
Maximum: 55.6W
PL1 Limit: 115.0W
PL2 Limit: 115.0W
```

**Initial Diagnosis**: Thermal throttling due to high temperatures, NOT power limits.

## Monitoring Setup

To investigate further, a multi-pane monitoring setup was configured using `hwinfo-tui`:

### Recommended Dashboard Layout

**1. Temperature Monitoring**
```bash
hwinfo-tui monitor sensors.csv "Core Temperatures (avg)" "CPU Package" --time-window 120 --refresh-rate 1
```

**2. Power Analysis**
```bash
hwinfo-tui monitor sensors.csv "CPU Package Power" "IA Cores Power" --time-window 120 --refresh-rate 1
```

**3. Performance Metrics**
```bash
hwinfo-tui monitor sensors.csv "Total CPU Usage" "Core Clocks (avg)" --time-window 120 --refresh-rate 1
```

**4. Throttling Status**
```bash
hwinfo-tui monitor sensors.csv "Core Thermal Throttling (avg)" "Package/Ring Thermal Throttling" --time-window 120 --refresh-rate 1
```

## Critical Discovery

### The Package-Core Temperature Delta Problem

Real-time monitoring revealed an unexpected finding:

**Observed Metrics:**
| Metric | Value | Status |
|--------|-------|--------|
| Core Temperatures (avg) | 69°C | ✅ Appears acceptable |
| CPU Package | **91.8°C** | 🔴 CRITICAL |
| CPU Package Max | **105.0°C** | 🔴 EXTREME |
| CPU Package P95 | 98.08°C | 🔴 CRITICAL |
| **Temperature Delta** | **~23°C** | 🔴 ABNORMAL |

### Why This Matters

The CPU throttling system responds to **package temperature**, not just average core temperature. A large delta between these values indicates:

#### Normal System (Healthy)
```
Core avg:    65°C
Package:     70-75°C
Delta:       ~5-10°C  ✅
Result:      No throttling
```

#### Observed System (Problem)
```
Core avg:    69°C
Package:     91.8°C
Delta:       ~23°C    ⚠️
Result:      Throttling engaged despite "acceptable" core temps
```

### Power Validation

The power analysis confirmed this was NOT a power limit issue:

- **Average consumption**: 25.1W
- **Peak consumption**: 55.6W
- **PL1/PL2 limits**: 115.0W
- **Conclusion**: Operating at only 48% of power limit

## Root Cause Analysis

The large package-to-core temperature delta (23°C) is a diagnostic indicator of:

### 1. Poor Thermal Contact
- CPU cooler not properly seated
- Uneven mounting pressure
- Warped heatsink base or CPU IHS

### 2. Thermal Paste Issues
- Dried out thermal paste
- Insufficient paste application
- Uneven paste spread
- Air gaps between surfaces

### 3. Hotspot Formation
- One or more cores running significantly hotter than others
- Localized hotspot pulling package temperature up
- Heat not spreading evenly across CPU package

### 4. Cooler Inadequacy
- Insufficient cooler capacity for CPU TDP
- Poor airflow over heatsink
- Fan malfunction or incorrect fan curve

## Diagnostic Approach

### Key Sensors to Monitor

For thermal troubleshooting, focus on these critical sensors:

**Primary Temperature Sensors:**
- `Core Temperatures (avg) [°C]` - Overall core thermal state
- `CPU Package [°C]` - **Most important** - actual throttle trigger
- `Core Distance to TjMAX (avg) [°C]` - Thermal headroom remaining

**Throttling Indicators:**
- `Core Thermal Throttling (avg) [Yes/No]` - Core-level throttling status
- `Package/Ring Thermal Throttling [Yes/No]` - Package-level throttling

**Power Validation:**
- `CPU Package Power [W]` - Actual power draw
- `PL1 Power Limit (Static) [W]` - Power limit reference
- `PL2 Power Limit (Static) [W]` - Turbo power limit reference

**Limit Reasons (Advanced):**
- `IA: Thermal Event [Yes/No]` - Thermal throttling trigger
- `IA: Running Average Thermal Limit [Yes/No]` - RATL throttling
- `IA: Package-Level RAPL/PBM PL2,PL3 [Yes/No]` - Power limit throttling

### Analysis Pattern

When investigating throttling:

1. **Check power first**: If power consumption << limits, not a power issue
2. **Compare core vs package temps**: Large delta (>15°C) = thermal contact problem
3. **Check individual cores**: Look for outliers that might create hotspots
4. **Monitor throttling correlation**: Note when throttling engages relative to temps
5. **Test thermal response**: Observe temperature rise/fall rates under load changes

## Recommended Solutions

### Immediate Actions

1. **Re-seat CPU Cooler**
   - Remove cooler completely
   - Clean old thermal paste from CPU and cooler
   - Apply fresh thermal paste (pea-sized amount or line method)
   - Ensure even mounting pressure (tighten screws in cross pattern)

2. **Verify Individual Core Temperatures**
   ```bash
   hwinfo-tui monitor sensors.csv "P-core 0" "P-core 1" "P-core 2" "P-core 3" "P-core 4" "P-core 5"
   ```
   Look for cores running 10-15°C hotter than others

3. **Check Cooling System**
   - Verify fans are spinning at appropriate RPM
   - Clean dust from heatsink fins
   - Ensure adequate case airflow
   - Check fan curves in BIOS

### Long-term Solutions

1. **Upgrade Cooling** (if re-seating doesn't help)
   - Consider larger heatsink or AIO liquid cooler
   - Improve case airflow with additional fans
   - Verify cooler TDP rating matches or exceeds CPU TDP

2. **Monitor After Changes**
   - Re-run thermal analysis after each change
   - Target: Package-to-core delta < 10°C
   - Goal: Package temps < 85°C under load

## Key Takeaways

### For Users Troubleshooting Throttling

1. **Don't rely on core temps alone** - Always monitor package temperature
2. **Check power consumption** - Rule out power limits before assuming thermal issues
3. **Look for temperature deltas** - Large gaps between sensors indicate contact problems
4. **Use multiple monitoring panes** - Correlate temps, power, clocks, and throttling status

### For hwinfo-tui Usage

1. **Temperature monitoring requires package temp** - Core avg alone can be misleading
2. **Multi-pane setup is essential** - See the full picture with 4+ simultaneous views
3. **Unit limits matter** - Remember the 2-unit maximum per chart
4. **Throttling sensors are binary** - Best viewed in dedicated chart to see state changes

### For System Diagnostics

The combination of:
- High package temperature (90°C+)
- "Normal" core temperatures (70°C)
- Low power consumption (50% of limit)
- Constant throttling (97% of samples)

...is a **strong diagnostic signature** of thermal contact failure, not cooling capacity or power delivery issues.

## Tools and Commands Reference

### Analysis Commands

**List temperature-related sensors:**
```bash
hwinfo-tui list-sensors sensors.csv --limit 450 | grep -E "Temperature|Thermal|TjMAX"
```

**List throttling and limit sensors:**
```bash
hwinfo-tui list-sensors sensors.csv --limit 450 | grep -E "Throttling|Limit|IA:"
```

**Find power sensors:**
```bash
hwinfo-tui list-sensors sensors.csv --limit 450 | grep -E "Power.*\[W\]"
```

## Conclusion

This investigation demonstrates the importance of:

1. **Comprehensive monitoring** - Multiple sensors tell the complete story
2. **Understanding thermal architecture** - Package vs core temperature distinctions
3. **Proper diagnostics** - Distinguishing between thermal, power, and contact issues
4. **Tool capabilities** - Leveraging hwinfo-tui's real-time visualization

The key insight—that package temperature can significantly exceed core temperature—is critical for anyone troubleshooting thermal issues. This delta is often the "hidden" problem that causes throttling when core temps appear acceptable.

---

**Date**: October 24, 2025
**Analysis Tool**: hwinfo-tui
**Hardware**: Intel hybrid architecture CPU (P-cores + E-cores)
**Finding**: 23°C package-to-core temperature delta causing throttling at seemingly normal temps
