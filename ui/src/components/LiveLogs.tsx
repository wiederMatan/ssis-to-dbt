import { useState, useEffect, useRef } from 'react';
import { Terminal, Pause, Play, Filter, Trash2 } from 'lucide-react';
import { cn } from '../lib/utils';
import type { LogEntry } from '../types';

interface LiveLogsProps {
  logs: LogEntry[];
  onClear?: () => void;
}

type LogLevel = 'all' | 'info' | 'warn' | 'error' | 'success';

export function LiveLogs({ logs, onClear }: LiveLogsProps) {
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState<LogLevel>('all');
  const scrollRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter(log =>
    filter === 'all' || log.level === filter
  );

  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredLogs, isPaused]);

  const levelColors: Record<LogEntry['level'], string> = {
    info: 'log-info',
    warn: 'log-warn',
    error: 'log-error',
    success: 'log-success',
  };

  const levelBadge: Record<LogEntry['level'], { text: string; bg: string }> = {
    info: { text: 'INFO', bg: 'bg-blue-500/20 text-blue-400' },
    warn: { text: 'WARN', bg: 'bg-yellow-500/20 text-yellow-400' },
    error: { text: 'ERROR', bg: 'bg-red-500/20 text-red-400' },
    success: { text: 'OK', bg: 'bg-green-500/20 text-green-400' },
  };

  return (
    <div className="flex flex-col h-full border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4" />
          <span className="font-medium">Live Logs</span>
          <span className="text-xs text-muted-foreground">
            ({filteredLogs.length} entries)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter */}
          <div className="flex items-center gap-1">
            <Filter className="h-3 w-3 text-muted-foreground" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as LogLevel)}
              className="text-xs bg-background border rounded px-2 py-1"
            >
              <option value="all">All</option>
              <option value="info">Info</option>
              <option value="warn">Warnings</option>
              <option value="error">Errors</option>
              <option value="success">Success</option>
            </select>
          </div>

          {/* Pause/Play */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={cn(
              "p-1 rounded hover:bg-muted",
              isPaused && "text-yellow-500"
            )}
            title={isPaused ? "Resume auto-scroll" : "Pause auto-scroll"}
          >
            {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </button>

          {/* Clear */}
          {onClear && (
            <button
              onClick={onClear}
              className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
              title="Clear logs"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Log Content */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-3 bg-slate-950 terminal"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-muted-foreground text-center py-8">
            No logs to display
          </div>
        ) : (
          <div className="space-y-1">
            {filteredLogs.map((log, idx) => (
              <div key={idx} className="flex gap-2 text-slate-300">
                <span className="text-slate-500 select-none">
                  {log.timestamp}
                </span>
                <span className={cn(
                  "px-1 rounded text-[10px] font-mono uppercase",
                  levelBadge[log.level].bg
                )}>
                  {levelBadge[log.level].text}
                </span>
                {log.source && (
                  <span className="text-slate-400">[{log.source}]</span>
                )}
                <span className={levelColors[log.level]}>{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Status Bar */}
      {isPaused && (
        <div className="px-3 py-1 bg-yellow-500/20 text-yellow-500 text-xs text-center">
          Auto-scroll paused - Click play to resume
        </div>
      )}
    </div>
  );
}

// Generate sample logs for demonstration
export function generateSampleLogs(): LogEntry[] {
  const now = new Date();
  const logs: LogEntry[] = [];

  const entries = [
    { level: 'info' as const, message: 'Starting SSIS to dbt migration...', source: 'main' },
    { level: 'info' as const, message: 'Found 3 SSIS packages to process', source: 'parser' },
    { level: 'info' as const, message: 'Parsing CustomerDataLoad.dtsx...', source: 'parser' },
    { level: 'success' as const, message: 'CustomerDataLoad.dtsx parsed successfully', source: 'parser' },
    { level: 'info' as const, message: 'Parsing SalesFactETL.dtsx...', source: 'parser' },
    { level: 'success' as const, message: 'SalesFactETL.dtsx parsed successfully', source: 'parser' },
    { level: 'info' as const, message: 'Parsing InventorySync.dtsx...', source: 'parser' },
    { level: 'warn' as const, message: 'Script Task "Call Inventory API" requires manual review', source: 'parser' },
    { level: 'success' as const, message: 'InventorySync.dtsx parsed with warnings', source: 'parser' },
    { level: 'info' as const, message: 'Generating dbt project structure...', source: 'scaffolder' },
    { level: 'info' as const, message: 'Created models/staging/stg_crm__customers.sql', source: 'scaffolder' },
    { level: 'info' as const, message: 'Created models/staging/stg_sales__transactions.sql', source: 'scaffolder' },
    { level: 'info' as const, message: 'Created models/core/dim_customer.sql', source: 'scaffolder' },
    { level: 'info' as const, message: 'Created models/core/fct_sales.sql', source: 'scaffolder' },
    { level: 'success' as const, message: 'dbt project scaffolding complete', source: 'scaffolder' },
    { level: 'info' as const, message: 'Running dbt deps...', source: 'dbt' },
    { level: 'success' as const, message: 'dbt deps completed', source: 'dbt' },
    { level: 'info' as const, message: 'Running dbt run...', source: 'dbt' },
    { level: 'success' as const, message: '7 models materialized successfully', source: 'dbt' },
    { level: 'info' as const, message: 'Running validation checks...', source: 'validator' },
    { level: 'success' as const, message: 'dim_customer: Row count PASSED (15,000 rows)', source: 'validator' },
    { level: 'success' as const, message: 'fct_sales: Row count PASSED (1,250,000 rows)', source: 'validator' },
    { level: 'success' as const, message: 'All validation checks passed', source: 'validator' },
    { level: 'success' as const, message: 'Migration completed successfully!', source: 'main' },
  ];

  entries.forEach((entry, idx) => {
    const timestamp = new Date(now.getTime() + idx * 1000);
    logs.push({
      ...entry,
      timestamp: timestamp.toLocaleTimeString('en-US', { hour12: false }),
    });
  });

  return logs;
}
