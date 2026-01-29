// Types for SSIS to dbt migration dashboard

export type MigrationStatus = 'pending' | 'migrated' | 'failed' | 'warning';
export type ValidationStatus = 'passed' | 'failed' | 'warning' | 'skipped';

export interface SSISPackage {
  name: string;
  description: string | null;
  creation_date: string | null;
  creator_name: string | null;
  file_path: string;
  file_size_bytes: number;
  connection_managers: ConnectionManager[];
  variables: Variable[];
  execute_sql_tasks: ExecuteSQLTask[];
  data_flow_tasks: DataFlowTask[];
  script_tasks: ScriptTask[];
  send_mail_tasks: SendMailTask[];
  precedence_constraints: PrecedenceConstraint[];
  parsing_warnings: string[];
  parsing_errors: string[];
}

export interface ConnectionManager {
  id: string;
  name: string;
  description: string | null;
  connection_string: string;
  server: string | null;
  database: string | null;
  provider: string | null;
}

export interface Variable {
  namespace: string;
  name: string;
  data_type: string;
  value: string | null;
}

export interface ExecuteSQLTask {
  name: string;
  description: string | null;
  connection_manager: string;
  sql_statement: string;
  result_set: string;
}

export interface DataFlowTask {
  name: string;
  description: string | null;
  sources: DataFlowSource[];
  destinations: DataFlowDestination[];
  lookups: LookupTransform[];
  derived_columns: DerivedColumnDef[];
}

export interface DataFlowSource {
  name: string;
  component_type: string;
  sql_command: string | null;
  table_name: string | null;
  columns: ColumnInfo[];
}

export interface DataFlowDestination {
  name: string;
  component_type: string;
  table_name: string | null;
}

export interface LookupTransform {
  name: string;
  sql_command: string | null;
  output_columns: string[];
}

export interface DerivedColumnDef {
  name: string;
  expression: string;
  friendly_expression: string | null;
}

export interface ColumnInfo {
  name: string;
  ssis_type: string;
  sql_type: string;
}

export interface ScriptTask {
  name: string;
  description: string | null;
  manual_review_required: boolean;
  review_reason: string;
}

export interface SendMailTask {
  name: string;
  description: string | null;
  skip_reason: string;
}

export interface PrecedenceConstraint {
  from_task: string;
  to_task: string;
  constraint_type: string;
}

// Validation types
export interface ValidationReport {
  generated_at: string;
  model_validations: ModelValidation[];
  total_models: number;
  models_passed: number;
  models_failed: number;
  models_warning: number;
  overall_status: ValidationStatus;
}

export interface ModelValidation {
  model_name: string;
  ssis_package: string;
  ssis_task: string;
  legacy_table: string | null;
  row_count: RowCountValidation | null;
  primary_key: PrimaryKeyValidation | null;
  checksums: ChecksumValidation[];
  overall_status: ValidationStatus;
}

export interface RowCountValidation {
  legacy_table: string;
  legacy_count: number;
  dbt_model: string;
  dbt_count: number;
  difference: number;
  difference_percent: number;
  status: ValidationStatus;
}

export interface PrimaryKeyValidation {
  pk_column: string;
  null_count: number;
  duplicate_count: number;
  status: ValidationStatus;
}

export interface ChecksumValidation {
  column: string;
  legacy_sum: number;
  dbt_sum: number;
  variance_percent: number;
  status: ValidationStatus;
}

// Migration mapping types
export interface MigrationMapping {
  packages: PackageMapping[];
  summary: MigrationSummary;
  dbt_models_created: {
    staging: string[];
    core: string[];
  };
}

export interface PackageMapping {
  ssis_package: string;
  description: string;
  tasks: TaskMapping[];
}

export interface TaskMapping {
  ssis_task: string;
  ssis_type: string;
  dbt_model: string | null;
  dbt_layer?: string;
  dbt_file?: string;
  status: 'converted' | 'skipped' | 'manual_review' | 'converted_to_tests';
  manual_review_required?: boolean;
}

export interface MigrationSummary {
  total_ssis_tasks: number;
  converted: number;
  converted_to_tests: number;
  skipped: number;
  manual_review: number;
  conversion_rate: string;
}

// Log entry for live logs
export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
  source?: string;
}
