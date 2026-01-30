import { useState, useMemo } from 'react';
import { Code, FileCode, ArrowRight, Copy, Check, Maximize2, Minimize2 } from 'lucide-react';
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
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

// Simple syntax highlighting for SQL/Jinja
function highlightCode(code: string, language: 'sql' | 'xml' | 'jinja'): React.ReactNode[] {
  const lines = code.split('\n');

  const sqlKeywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|AS|CASE|WHEN|THEN|ELSE|END|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|UNION|ALL|DISTINCT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TABLE|INDEX|VIEW|WITH|CTE|CAST|COALESCE|NULLIF|COUNT|SUM|AVG|MIN|MAX|ROW_NUMBER|RANK|DENSE_RANK|PARTITION|OVER)\b/gi;
  const sqlFunctions = /\b(CAST|COALESCE|NULLIF|ISNULL|COUNT|SUM|AVG|MIN|MAX|LEN|SUBSTRING|UPPER|LOWER|TRIM|LTRIM|RTRIM|REPLACE|CONCAT|DATEADD|DATEDIFF|GETDATE|CONVERT|FORMAT)\s*\(/gi;
  const sqlStrings = /'[^']*'/g;
  const sqlNumbers = /\b\d+(\.\d+)?\b/g;
  const sqlComments = /(--.*$|\/\*[\s\S]*?\*\/)/gm;

  const jinjaBlocks = /(\{\{|\}\}|\{%|%\})/g;
  const jinjaVars = /\{\{\s*[\w.()]+\s*\}\}/g;
  const jinjaConfig = /\b(config|ref|source|var)\b/g;

  return lines.map((line, lineIndex) => {
    // Handle comments first (they take precedence)
    if (line.trim().startsWith('--') || line.trim().startsWith('/*') || line.trim().startsWith('<!--')) {
      return (
        <div key={lineIndex} className="syntax-comment">
          {line}
        </div>
      );
    }

    // Tokenize and highlight
    let result = line;
    const spans: { start: number; end: number; className: string; text: string }[] = [];

    // Find all matches and their positions
    const findMatches = (regex: RegExp, className: string) => {
      let match;
      const r = new RegExp(regex.source, regex.flags);
      while ((match = r.exec(line)) !== null) {
        spans.push({
          start: match.index,
          end: match.index + match[0].length,
          className,
          text: match[0]
        });
      }
    };

    if (language === 'sql' || language === 'jinja') {
      findMatches(sqlStrings, 'syntax-string');
      findMatches(sqlComments, 'syntax-comment');
      findMatches(sqlKeywords, 'syntax-keyword');
      findMatches(sqlFunctions, 'syntax-function');
      findMatches(sqlNumbers, 'syntax-number');
    }

    if (language === 'jinja') {
      findMatches(jinjaBlocks, 'syntax-jinja-block');
      findMatches(jinjaConfig, 'syntax-jinja-var');
    }

    // Sort spans by start position, then by length (longer matches first)
    spans.sort((a, b) => a.start - b.start || b.end - a.end);

    // Remove overlapping spans (keep the first one)
    const filteredSpans: typeof spans = [];
    let lastEnd = -1;
    for (const span of spans) {
      if (span.start >= lastEnd) {
        filteredSpans.push(span);
        lastEnd = span.end;
      }
    }

    // Build the highlighted line
    if (filteredSpans.length === 0) {
      return <div key={lineIndex}>{line || '\u00A0'}</div>;
    }

    const parts: React.ReactNode[] = [];
    let currentIndex = 0;

    filteredSpans.forEach((span, idx) => {
      // Add text before this span
      if (span.start > currentIndex) {
        parts.push(
          <span key={`text-${idx}`}>{line.slice(currentIndex, span.start)}</span>
        );
      }
      // Add the highlighted span
      parts.push(
        <span key={`span-${idx}`} className={span.className}>
          {span.text}
        </span>
      );
      currentIndex = span.end;
    });

    // Add remaining text
    if (currentIndex < line.length) {
      parts.push(<span key="rest">{line.slice(currentIndex)}</span>);
    }

    return <div key={lineIndex}>{parts.length > 0 ? parts : '\u00A0'}</div>;
  });
}

function CodeBlock({ title, code, language, isFullscreen, onToggleFullscreen }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const highlightedCode = useMemo(() => highlightCode(code, language), [code, language]);

  return (
    <div className={cn(
      "flex flex-col border rounded-lg overflow-hidden",
      isFullscreen ? "fixed inset-4 z-50" : "flex-1"
    )}>
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b">
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4" aria-hidden="true" />
          <span className="font-medium text-sm truncate" title={title}>{title}</span>
          <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
            {language.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center gap-1" role="toolbar" aria-label="Code actions">
          {onToggleFullscreen && (
            <button
              onClick={onToggleFullscreen}
              className="p-1 rounded hover:bg-muted transition-colors"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              aria-label={isFullscreen ? "Exit fullscreen" : "View fullscreen"}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Maximize2 className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-1 rounded hover:bg-muted transition-colors"
            title="Copy code"
            aria-label={copied ? "Copied!" : "Copy code to clipboard"}
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-500" />
            ) : (
              <Copy className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>
      <div
        className="flex-1 overflow-auto p-4 code-block font-mono text-sm"
        tabIndex={0}
        role="region"
        aria-label={`${title} code`}
      >
        <pre className="text-[var(--color-terminal-fg)] whitespace-pre leading-relaxed">
          {highlightedCode}
        </pre>
      </div>
    </div>
  );
}

export function DiffViewer({ ssisPackage, taskMappings }: DiffViewerProps) {
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [fullscreenPanel, setFullscreenPanel] = useState<'ssis' | 'dbt' | null>(null);

  if (!ssisPackage) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <Code className="h-12 w-12 mx-auto mb-4 opacity-50" aria-hidden="true" />
          <p className="text-lg">Select a package to view SQL comparisons</p>
          <p className="text-sm mt-2">Choose a package from the sidebar first</p>
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

  const hasNoTasks = sqlTasks.length === 0 && dataFlows.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Task Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 border-b">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label htmlFor="task-select" className="text-sm font-medium whitespace-nowrap">Task:</label>
          <select
            id="task-select"
            value={currentTask}
            onChange={(e) => setSelectedTask(e.target.value)}
            disabled={hasNoTasks}
            className="custom-select flex-1 sm:flex-initial sm:max-w-md px-3 py-2 border rounded-lg bg-background"
            aria-label="Select task to compare"
          >
            {hasNoTasks && (
              <option value="">No tasks available</option>
            )}
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
        </div>

        {taskMapping && (
          <div className="flex items-center gap-2 text-sm">
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
            <span className="font-mono px-2 py-1 bg-primary/10 rounded">
              {taskMapping.dbt_model}
            </span>
            <span className={cn(
              "px-2 py-0.5 rounded text-xs",
              taskMapping.status === 'converted' ? "status-passed" :
              taskMapping.status === 'manual_review' ? "status-warning" :
              "bg-gray-500/20 text-gray-400"
            )}>
              {taskMapping.status.replace('_', ' ')}
            </span>
          </div>
        )}
      </div>

      {/* Side-by-side Code View */}
      {fullscreenPanel && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={() => setFullscreenPanel(null)}
          aria-hidden="true"
        />
      )}

      <div className="flex-1 flex flex-col md:flex-row gap-4 p-4 overflow-hidden">
        {(!fullscreenPanel || fullscreenPanel === 'ssis') && (
          <CodeBlock
            title={`SSIS: ${currentTask}`}
            code={getOriginalSql()}
            language={selectedSqlTask ? 'sql' : 'xml'}
            isFullscreen={fullscreenPanel === 'ssis'}
            onToggleFullscreen={() => setFullscreenPanel(fullscreenPanel === 'ssis' ? null : 'ssis')}
          />
        )}
        {(!fullscreenPanel || fullscreenPanel === 'dbt') && (
          <CodeBlock
            title={`dbt: ${taskMapping?.dbt_model || 'preview'}`}
            code={generateDbtPreview()}
            language="jinja"
            isFullscreen={fullscreenPanel === 'dbt'}
            onToggleFullscreen={() => setFullscreenPanel(fullscreenPanel === 'dbt' ? null : 'dbt')}
          />
        )}
      </div>

      {/* Keyboard shortcuts hint */}
      <div className="px-4 py-2 border-t text-xs text-muted-foreground">
        <span className="hidden sm:inline">
          Tip: Click the maximize button to view code in fullscreen
        </span>
      </div>
    </div>
  );
}
