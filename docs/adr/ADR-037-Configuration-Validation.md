# ADR 037: Configuration Validation

## Status
Accepted

## Context
Deploying TITAN with invalid API keys or missing directories leads to fatal runtime errors.

## Decision
We implement a comprehensive `ConfigurationValidator` suite that validates the environment, profile, directories, and broker configuration before startup.

## Consequences
TITAN refuses to boot in unsafe environments, protecting capital.
