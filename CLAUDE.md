# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This project converts SSIS (SQL Server Integration Services) packages to dbt (data build tool) models. SSIS packages are XML-based ETL workflows (.dtsx files) that need to be parsed and transformed into dbt SQL models and YAML configurations.

## Key Concepts

- **SSIS packages (.dtsx)**: XML files containing data flow tasks, control flow logic, connection managers, and transformations
- **dbt models**: SQL SELECT statements that define transformations, organized with YAML schema files for documentation and testing
- SSIS Data Flow Tasks map to dbt models; Control Flow orchestration maps to dbt DAG dependencies
