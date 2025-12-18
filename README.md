# Designing a Scalable Factory Equipment Health and Maintenance Platform

This project presents a system design and data architecture for monitoring factory equipment health and maintenance status at scale.

The goal is to demonstrate how raw telemetry, maintenance workflows, and operator input can be combined to produce a clear, real time operational view of machine status and health.

This repository is structured as a technical design report rather than a full production system.

## What this project answers

This report answers the following core question:

**How can we determine the latest operational status and health of each machine when many telemetry records are continuously produced per machine?**

The solution focuses on:
- Resolving the current machine status using clear precedence rules
- Computing a rolling machine health score
- Maintaining a fast, query friendly current state store
- Supporting real time dashboards without scanning historical data

## Why Quarto

Quarto was used to author this report because it allows:

- One source of truth for HTML and PDF outputs
- Clear technical documentation mixed with SQL and pseudocode
- Reproducible, version controlled reporting
- Easy publishing to GitHub Pages

This approach makes the design easy to review, share, and extend.

## Outputs

- **Website (HTML)**  
  https://jim-franklin.github.io/intelbyte/

- **PDF Report**  
  Available via the website at https://jim-franklin.github.io/intelbyte/report.pdf
