# TITAN Documentation Index (v1.0 RC1)

## Overview
- **Document Purpose**: Central repository mapping the operational, architectural, and structural guidelines for the TITAN ecosystem.
- **Audience**: Systems Operators, Quantitative Researchers, Algorithmic Engineers, and DevOps personnel.
- **Current Version**: v1.0 Release Candidate 1
- **Last Reviewed Milestone**: M8.5.1

## Core Documentation

### System Operation & Deployment
- `README.md` (Root): High-level system overview, capabilities, and entry-point directions.
- `docs/INSTALLATION.md`: Prerequisites, environment setup, and dependency management.
- `docs/OPERATIONS.md`: Daily operational workflows, configuration overrides, and general lifecycle management.
- `docs/PRODUCTION.md`: Hardened institutional pre-flight deployment checklists and validation frameworks.
- `docs/OPERATIONAL_EXCELLENCE.md`: The canonical operator handbook covering pause/resume logic, failure scenarios, and disaster recovery.

### Interfaces
- `docs/CLI_REFERENCE.md`: Comprehensive mapping of all `titan` command-line interfaces, including JSON formatting outputs and dry-run behaviors.
- `docs/TUI.md`: Keybindings, view navigation models, and visual telemetry descriptions for the Text User Interface.

### Architecture & Engine Design
- `docs/ARCHITECTURE.md`: Foundational architecture guidelines focusing on separation of concerns, the Broker layer, and the Runtime orchestration boundaries.
- `docs/RISK_ENGINE.md`: Positional limits, portfolio constraints, and charm/vanna exposure mechanisms.
- `docs/PORTFOLIO_ANALYTICS.md`: Overview of institutional reporting, drawdown evaluations, and read-only exposure snapshots.

## Certification Reports (M8.5.1 RC1)
- `docs/ARCHITECTURE_CERTIFICATION.md`: Verification of strict modular boundaries.
- `docs/CODE_QUALITY_REPORT.md`: Findings on codebase health, large modules, and logging consistency.
- `docs/DEPENDENCY_AUDIT.md`: Third-party risk assessment and version constraints.
- `docs/TEST_CERTIFICATION.md`: Regression confidence and suite categorizations.
- `docs/RELEASE_CERTIFICATION.md`: Fresh installation and runtime startup validations.

## Architectural Decision Records (ADRs)
- `docs/adr/ADR-001` through `ADR-038`: Historical progression of technical pivots, from initial layout (001) through TUI additions (034) and final reliability supervisors (035-038).

## Certification Conclusion
All documents have been checked for cross-reference integrity, version consistency, CLI command accuracy, and procedural flows. The TITAN documentation suite is **FROZEN** and **CERTIFIED** for v1.0 Release Candidate 1.
