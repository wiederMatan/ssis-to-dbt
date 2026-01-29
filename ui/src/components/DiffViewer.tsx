import { useState } from 'react';
import { Code, FileCode, ArrowRight, Copy, Check } from 'lucide-react';
import { cn } from '../lib/utils';
import type { SSISPackage, TaskMapping } from '../types';

interface DiffViewerProps {
  ssisPackage: SSISPackage | null;
  taskMappings: TaskMapping[];
}

interface CodeBlockProps {
  title: string;
  code: string;
  language: 'sql' | 'xml' | 'jinja';
}

function CodeBlock({ title, code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 flex flex-col border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b">
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4" />
          <span className="font-medium text-sm">{title}</span>
          <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
            {language.toUpperCase()}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="p-1 rounded hover:bg-muted transition-colors"
          title="Copy code"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4 text-muted-foreground" />
          )}
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4 bg-slate-950">
        <pre className="text-sm font-mono text-slate-300 whitespace-pre-wrap">
          {code}
        </pre>
      </div>
    </div>
  );
}

export function DiffViewer({ ssisPackage, taskMappings }: DiffViewerProps) {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);

  if (!ssisPackage) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <Code className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Select a package to view SQL comparisons</p>
        </div>
      </div>
    );
  }

  // Get all SQL tasks and data flows
  const sqlTasks = ssisPackage.execute_sql_tasks;
  const dataFlows = ssisPackage.data_flow_tasks;

  const currentTask = selectedTask || sqlTasks[0]?.name || dataFlows[0]?.name;

  // Find the selected SQL task or data flow
  const selectedSqlTask = sqlTasks.find(t => t.name === currentTask);
  const selectedDataFlow = dataFlows.find(t => t.name === currentTask);

  // Find corresponding dbt model
  const taskMapping = taskMappings.find(
    tm => tm.ssis_task === currentTask && tm.dbt_model
  );

  // Generate dbt SQL preview
  const generateDbtPreview = (): string => {
    if (selectedSqlTask) {
      // For Execute SQL tasks, show a simplified dbt model
      const sql = selectedSqlTask.sql_statement;
      return `{{
    config(
        materialized='table',
        schema='core'
    )
}}

/*
    Converted from: ${ssisPackage.name}
    Task: ${selectedSqlTask.name}
    Description: ${selectedSqlTask.description || 'N/A'}
*/

WITH source_data AS (
    -- Original SSIS SQL transformed to dbt
    ${sql.split('\n').map(line => '    ' + line).join('\n')}
),

final AS (
    SELECT *
    FROM source_data
)

SELECT * FROM final`;
    }

    if (selectedDataFlow) {
      // For Data Flow tasks, show staging model structure
      const source = selectedDataFlow.sources[0];
      const derivedCols = selectedDataFlow.derived_columns;

      let dbtCode = `{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Converted from: ${ssisPackage.name}
    Task: ${selectedDataFlow.name}
    Description: ${selectedDataFlow.description || 'N/A'}
*/

WITH source_data AS (
    SELECT
        *
    FROM {{ source('source_system', 'source_table') }}
)`;

      if (derivedCols.length > 0) {
        dbtCode += `,

derived AS (
    SELECT
        *,
${derivedCols.map(dc =>
  `        -- ${dc.friendly_expression || dc.expression}
        ${dc.expression.replace(/\[(\w+)\]/g, '$1')} AS ${dc.name.toLowerCase()}`
).join(',\n')}
    FROM source_data
)

SELECT * FROM derived`;
      } else {
        dbtCode += `

SELECT * FROM source_data`;
      }

      return dbtCode;
    }

    return '-- Select a task to view conversion';
  };

  // Get original SSIS SQL
  const getOriginalSql = (): string => {
    if (selectedSqlTask) {
      return selectedSqlTask.sql_statement;
    }

    if (selectedDataFlow) {
      let xml = `<!-- Data Flow Task: ${selectedDataFlow.name} -->
<!-- Description: ${selectedDataFlow.description || 'N/A'} -->

`;
      // Show source query
      selectedDataFlow.sources.forEach(src => {
        if (src.sql_command) {
          xml += `<!-- Source: ${src.name} -->
${src.sql_command}

`;
        }
      });

      // Show derived columns
      if (selectedDataFlow.derived_columns.length > 0) {
        xml += `<!-- Derived Columns -->
`;
        selectedDataFlow.derived_columns.forEach(dc => {
          xml += `-- ${dc.name}: ${dc.expression}
`;
        });
      }

      // Show lookups
      if (selectedDataFlow.lookups.length > 0) {
        xml += `
<!-- Lookup Transforms -->
`;
        selectedDataFlow.lookups.forEach(lk => {
          xml += `-- ${lk.name}
${lk.sql_command || '-- No SQL command'}

`;
        });
      }

      return xml;
    }

    return '-- Select a task';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Task Selector */}
      <div className="flex items-center gap-4 p-4 border-b">
        <span className="text-sm font-medium">Task:</span>
        <select
          value={currentTask}
          onChange={(e) => setSelectedTask(e.target.value)}
          className="flex-1 max-w-md px-3 py-2 border rounded-lg bg-background"
        >
          {sqlTasks.length > 0 && (
            <optgroup label="Execute SQL Tasks">
              {sqlTasks.map(task => (
                <option key={task.name} value={task.name}>
                  {task.name}
                </option>
              ))}
            </optgroup>
          )}
          {dataFlows.length > 0 && (
            <optgroup label="Data Flow Tasks">
              {dataFlows.map(task => (
                <option key={task.name} value={task.name}>
                  {task.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>

        {taskMapping && (
          <div className="flex items-center gap-2 text-sm">
            <ArrowRight className="h-4 w-4" />
            <span className="font-mono px-2 py-1 bg-primary/10 rounded">
              {taskMapping.dbt_model}
            </span>
            <span className={cn(
              "px-2 py-0.5 rounded text-xs",
              taskMapping.status === 'converted' ? "bg-green-500/20 text-green-500" :
              taskMapping.status === 'manual_review' ? "bg-yellow-500/20 text-yellow-500" :
              "bg-gray-500/20 text-gray-500"
            )}>
              {taskMapping.status}
            </span>
          </div>
        )}
      </div>

      {/* Side-by-side Code View */}
      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        <CodeBlock
          title={`SSIS: ${currentTask}`}
          code={getOriginalSql()}
          language={selectedSqlTask ? 'sql' : 'xml'}
        />
        <CodeBlock
          title={`dbt: ${taskMapping?.dbt_model || 'preview'}`}
          code={generateDbtPreview()}
          language="jinja"
        />
      </div>
    </div>
  );
}
