import { useState, useEffect, useRef, useCallback } from 'react';
import { Terminal, Pause, Play, Filter, Trash2, Download } from 'lucide-react';
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
  const [searchTerm, setSearchTerm] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter(log => {
    const matchesLevel = filter === 'all' || log.level === filter;
    const matchesSearch = searchTerm === '' ||
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.source && log.source.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesLevel && matchesSearch;
  });

  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredLogs, isPaused]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.ctrlKey && e.key === 'k') {
      e.preventDefault();
      onClear?.();
    }
    if (e.key === ' ' && document.activeElement?.closest('.live-logs')) {
      e.preventDefault();
      setIsPaused(prev => !prev);
    }
  }, [onClear]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Export logs
  const handleExport = () => {
    const logText = filteredLogs
      .map(log => `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.source ? `[${log.source}] ` : ''}${log.message}`)
      .join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `migration-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const levelColors: Record<LogEntry['level'], string> = {
    info: 'log-info',
    warn: 'log-warn',
    error: 'log-error',
    success: 'log-success',
  };

  const levelBadge: Record<LogEntry['level'], { text: string; className: string }> = {
    info: { text: 'INFO', className: 'status-info' },
    warn: { text: 'WARN', className: 'status-warning' },
    error: { text: 'ERROR', className: 'status-failed' },
    success: { text: 'OK', className: 'status-passed' },
  };

  return (
    <div className="live-logs flex flex-col h-full border rounded-lg overflow-hidden" role="log" aria-label="Live migration logs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 border-b bg-muted/30 gap-2">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4" aria-hidden="true" />
          <span className="font-medium">Live Logs</span>
          <span className="text-xs text-muted-foreground" aria-live="polite">
            ({filteredLogs.length} entries)
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative">
            <input
              type="search"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-32 sm:w-40 text-xs bg-background border rounded px-2 py-1 pr-6"
              aria-label="Search logs"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-1 top-1/2 -translate-y-1/2 p-0.5 hover:bg-muted rounded"
                aria-label="Clear search"
              >
                <span className="text-xs text-muted-foreground">×</span>
              </button>
            )}
          </div>

          {/* Filter */}
          <div className="flex items-center gap-1">
            <Filter className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as LogLevel)}
              className="custom-select text-xs bg-background border rounded px-2 py-1"
              aria-label="Filter log level"
            >
              <option value="all">All Levels</option>
              <option value="info">Info</option>
              <option value="warn">Warnings</option>
              <option value="error">Errors</option>
              <option value="success">Success</option>
            </select>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-1" role="toolbar" aria-label="Log actions">
            {/* Export */}
            <button
              onClick={handleExport}
              className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              title="Export logs"
              aria-label="Export logs to file"
            >
              <Download className="h-4 w-4" />
            </button>

            {/* Pause/Play */}
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={cn(
                "p-1 rounded hover:bg-muted transition-colors",
                isPaused && "text-yellow-500"
              )}
              title={isPaused ? "Resume auto-scroll (Space)" : "Pause auto-scroll (Space)"}
              aria-label={isPaused ? "Resume auto-scroll" : "Pause auto-scroll"}
              aria-pressed={isPaused}
            >
              {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </button>

            {/* Clear */}
            {onClear && (
              <button
                onClick={onClear}
                className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                title="Clear logs (Ctrl+K)"
                aria-label="Clear all logs"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Log Content */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-3 terminal"
        tabIndex={0}
        role="region"
        aria-label="Log entries"
      >
        {filteredLogs.length === 0 ? (
          <div className="text-muted-foreground text-center py-8" role="status">
            {logs.length === 0 ? 'No logs to display' : 'No logs match the current filter'}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredLogs.map((log, idx) => (
              <div
                key={idx}
                className="flex gap-2 text-[var(--color-terminal-fg)] hover:bg-white/5 px-1 -mx-1 rounded"
                role="listitem"
              >
                <span className="text-muted-foreground select-none shrink-0" aria-hidden="true">
                  {log.timestamp}
                </span>
                <span
                  className={cn(
                    "px-1 rounded text-[10px] font-mono uppercase shrink-0",
                    levelBadge[log.level].className
                  )}
                  role="status"
                >
                  {levelBadge[log.level].text}
                </span>
                {log.source && (
                  <span className="text-muted-foreground shrink-0">[{log.source}]</span>
                )}
                <span className={cn(levelColors[log.level], "break-all")}>{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Status Bar */}
      {isPaused && (
        <div
          className="px-3 py-1 status-warning text-xs text-center"
          role="status"
          aria-live="polite"
        >
          Auto-scroll paused - Press Space or click play to resume
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
