# Daily Operational Checklist

## Pre-Market (08:30 - 09:00)
- [ ] Verify system time synchronization (NTP).
- [ ] Confirm network connectivity to broker API.
- [ ] Ensure previous day's journals are archived.
- [ ] Start TITAN Runtime in Paper Mode (`titan runtime start --env paper`).
- [ ] Launch TUI (`titan monitor tui`).
- [ ] Verify no orphan positions from previous day (unless swing trading).
- [ ] Confirm memory and CPU baselines are stable.

## Market Open (09:15)
- [ ] Monitor first 15 minutes for execution latency.
- [ ] Verify Market Data streams are active and gapless.
- [ ] Check Decision Engine log for active evaluation.

## Intraday (Periodic)
- [ ] Spot-check Journal consistency against Broker Positions.
- [ ] Verify resource usage (RAM/CPU) remains within limits.
- [ ] Confirm Kill Switch is accessible and functional.

## Market Close (15:30)
- [ ] Verify no new orders are placed post-close.
- [ ] Ensure open day-trading positions are squared off.

## Post-Market (15:45 - 16:00)
- [ ] Shutdown Runtime (`titan runtime stop`).
- [ ] Complete `DAILY_SUMMARY.md` entry.
- [ ] Rotate and back up logs and journals.
- [ ] Log any unexpected behavior in `INCIDENT_LOG.md`.
