import { useState, Fragment } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Database,
  Key,
  Calculator,
  ArrowUpDown,
  Search
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ValidationReport, ModelValidation, ValidationStatus } from '../types';

interface ValidationViewProps {
  report: ValidationReport;
}

type SortField = 'model' | 'status' | 'rows';
type SortDirection = 'asc' | 'desc';

const statusConfig: Record<ValidationStatus, { icon: typeof CheckCircle; color: string; bg: string; text: string; className: string }> = {
  passed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', text: 'PASSED', className: 'status-passed' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', text: 'FAILED', className: 'status-failed' },
  warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', text: 'WARNING', className: 'status-warning' },
  skipped: { icon: AlertTriangle, color: 'text-gray-500', bg: 'bg-gray-500/10', text: 'SKIPPED', className: 'bg-gray-500/20 text-gray-400' },
};

export function ValidationView({ report }: ValidationViewProps) {
  const [expandedModels, setExpandedModels] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('model');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [filterStatus, setFilterStatus] = useState<ValidationStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const toggleExpand = (modelName: string) => {
    const newExpanded = new Set(expandedModels);
    if (newExpanded.has(modelName)) {
      newExpanded.delete(modelName);
    } else {
      newExpanded.add(modelName);
    }
    setExpandedModels(newExpanded);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSorted = [...report.model_validations]
    .filter(m => {
      const matchesStatus = filterStatus === 'all' || m.overall_status === filterStatus;
      const matchesSearch = searchTerm === '' ||
        m.model_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (m.legacy_table && m.legacy_table.toLowerCase().includes(searchTerm.toLowerCase()));
      return matchesStatus && matchesSearch;
    })
    .sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'model':
          comparison = a.model_name.localeCompare(b.model_name);
          break;
        case 'status':
          comparison = a.overall_status.localeCompare(b.overall_status);
          break;
        case 'rows':
          comparison = (a.row_count?.dbt_count || 0) - (b.row_count?.dbt_count || 0);
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

  const formatNumber = (num: number) => num.toLocaleString();

  // Keyboard navigation for expand/collapse
  const handleRowKeyDown = (e: React.KeyboardEvent, modelName: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleExpand(modelName);
    }
  };

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
        role="region"
        aria-label="Validation summary"
      >
        <div className="p-4 rounded-lg bg-card border">
          <div className="text-2xl font-bold">{report.total_models}</div>
          <div className="text-sm text-muted-foreground">Total Models</div>
        </div>
        <div className="p-4 rounded-lg status-passed border border-green-500/20">
          <div className="text-2xl font-bold">{report.models_passed}</div>
          <div className="text-sm opacity-70">Passed</div>
        </div>
        <div className="p-4 rounded-lg status-failed border border-red-500/20">
          <div className="text-2xl font-bold">{report.models_failed}</div>
          <div className="text-sm opacity-70">Failed</div>
        </div>
        <div className="p-4 rounded-lg status-warning border border-yellow-500/20">
          <div className="text-2xl font-bold">{report.models_warning}</div>
          <div className="text-sm opacity-70">Warnings</div>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Filter:</span>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
            {(['all', 'passed', 'failed', 'warning'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                aria-pressed={filterStatus === status}
                className={cn(
                  "px-3 py-1 text-sm rounded-full border transition-colors",
                  filterStatus === status
                    ? status === 'all'
                      ? "bg-primary text-primary-foreground"
                      : statusConfig[status].className
                    : "hover:bg-muted"
                )}
              >
                {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            placeholder="Search models..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm bg-background border rounded-lg"
            aria-label="Search models"
          />
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <div className="table-responsive">
          <table className="w-full" role="grid" aria-label="Validation results">
            <thead className="bg-muted/50">
              <tr>
                <th scope="col" className="w-8 p-3">
                  <span className="sr-only">Expand</span>
                </th>
                <th
                  scope="col"
                  className="p-3 text-left cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => handleSort('model')}
                  aria-sort={sortField === 'model' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  <div className="flex items-center gap-2">
                    Model
                    <ArrowUpDown className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
                  </div>
                </th>
                <th scope="col" className="p-3 text-left hidden md:table-cell">Legacy Table</th>
                <th
                  scope="col"
                  className="p-3 text-right cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => handleSort('rows')}
                  aria-sort={sortField === 'rows' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  <div className="flex items-center justify-end gap-2">
                    <span className="hidden sm:inline">Row Count</span>
                    <span className="sm:hidden">Rows</span>
                    <ArrowUpDown className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
                  </div>
                </th>
                <th scope="col" className="p-3 text-center hidden sm:table-cell">Diff</th>
                <th
                  scope="col"
                  className="p-3 text-center cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => handleSort('status')}
                  aria-sort={sortField === 'status' ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  <div className="flex items-center justify-center gap-2">
                    Status
                    <ArrowUpDown className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSorted.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-muted-foreground">
                    No models match the current filter
                  </td>
                </tr>
              ) : (
                filteredAndSorted.map((mv) => {
                  const isExpanded = expandedModels.has(mv.model_name);
                  const StatusIcon = statusConfig[mv.overall_status].icon;

                  return (
                    <Fragment key={mv.model_name}>
                      <tr
                        className={cn(
                          "border-t cursor-pointer hover:bg-muted/30 transition-colors",
                          statusConfig[mv.overall_status].bg
                        )}
                        onClick={() => toggleExpand(mv.model_name)}
                        onKeyDown={(e) => handleRowKeyDown(e, mv.model_name)}
                        tabIndex={0}
                        role="row"
                        aria-expanded={isExpanded}
                      >
                        <td className="p-3">
                          <span aria-hidden="true">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-sm">
                          <span className="tooltip" data-tooltip={mv.model_name}>
                            {mv.model_name}
                          </span>
                        </td>
                        <td className="p-3 text-sm text-muted-foreground hidden md:table-cell">
                          {mv.legacy_table || '-'}
                        </td>
                        <td className="p-3 text-right font-mono text-sm">
                          {mv.row_count ? formatNumber(mv.row_count.dbt_count) : '-'}
                        </td>
                        <td className="p-3 text-center hidden sm:table-cell">
                          {mv.row_count && (
                            <span className={cn(
                              "px-2 py-0.5 rounded text-xs font-mono",
                              mv.row_count.difference === 0
                                ? "status-passed"
                                : "status-failed"
                            )}>
                              {mv.row_count.difference === 0 ? '0' : `+${formatNumber(mv.row_count.difference)}`}
                            </span>
                          )}
                        </td>
                        <td className="p-3">
                          <div className="flex items-center justify-center gap-2">
                            <StatusIcon className={cn("h-4 w-4", statusConfig[mv.overall_status].color)} aria-hidden="true" />
                            <span className={cn("text-xs font-medium", statusConfig[mv.overall_status].color)}>
                              {statusConfig[mv.overall_status].text}
                            </span>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Details */}
                      {isExpanded && (
                        <tr className="border-t bg-muted/20">
                          <td colSpan={6} className="p-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              {/* Row Count Details */}
                              {mv.row_count && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2 text-sm font-medium">
                                    <Database className="h-4 w-4" aria-hidden="true" />
                                    Row Count Comparison
                                  </div>
                                  <dl className="pl-6 space-y-1 text-sm">
                                    <div className="flex justify-between">
                                      <dt className="text-muted-foreground">Legacy:</dt>
                                      <dd className="font-mono">{formatNumber(mv.row_count.legacy_count)}</dd>
                                    </div>
                                    <div className="flex justify-between">
                                      <dt className="text-muted-foreground">dbt:</dt>
                                      <dd className="font-mono">{formatNumber(mv.row_count.dbt_count)}</dd>
                                    </div>
                                    <div className="flex justify-between">
                                      <dt className="text-muted-foreground">Variance:</dt>
                                      <dd className="font-mono">{mv.row_count.difference_percent.toFixed(4)}%</dd>
                                    </div>
                                  </dl>
                                </div>
                              )}

                              {/* PK Integrity */}
                              {mv.primary_key && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2 text-sm font-medium">
                                    <Key className="h-4 w-4" aria-hidden="true" />
                                    Primary Key ({mv.primary_key.pk_column})
                                  </div>
                                  <dl className="pl-6 space-y-1 text-sm">
                                    <div className="flex justify-between">
                                      <dt className="text-muted-foreground">NULL values:</dt>
                                      <dd className={cn(
                                        "font-mono",
                                        mv.primary_key.null_count > 0 ? "text-red-500" : "text-green-500"
                                      )}>
                                        {mv.primary_key.null_count}
                                      </dd>
                                    </div>
                                    <div className="flex justify-between">
                                      <dt className="text-muted-foreground">Duplicates:</dt>
                                      <dd className={cn(
                                        "font-mono",
                                        mv.primary_key.duplicate_count > 0 ? "text-red-500" : "text-green-500"
                                      )}>
                                        {mv.primary_key.duplicate_count}
                                      </dd>
                                    </div>
                                  </dl>
                                </div>
                              )}

                              {/* Checksums */}
                              {mv.checksums.length > 0 && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2 text-sm font-medium">
                                    <Calculator className="h-4 w-4" aria-hidden="true" />
                                    Numeric Checksums
                                  </div>
                                  <dl className="pl-6 space-y-1 text-sm">
                                    {mv.checksums.map((cs) => (
                                      <div key={cs.column} className="flex justify-between">
                                        <dt className="text-muted-foreground font-mono">{cs.column}:</dt>
                                        <dd className={cn(
                                          "font-mono",
                                          cs.variance_percent === 0 ? "text-green-500" : "text-yellow-500"
                                        )}>
                                          {cs.variance_percent.toFixed(4)}%
                                        </dd>
                                      </div>
                                    ))}
                                  </dl>
                                </div>
                              )}
                            </div>

                            {/* SSIS Source Info */}
                            <div className="mt-4 pt-4 border-t text-sm text-muted-foreground">
                              <span className="font-medium">Source: </span>
                              {mv.ssis_package} → {mv.ssis_task}
                            </div>

                            {/* Mobile-only: Show hidden columns */}
                            <div className="md:hidden mt-4 pt-4 border-t space-y-2 text-sm">
                              {mv.legacy_table && (
                                <div>
                                  <span className="text-muted-foreground">Legacy Table: </span>
                                  <span className="font-mono">{mv.legacy_table}</span>
                                </div>
                              )}
                              {mv.row_count && (
                                <div className="sm:hidden">
                                  <span className="text-muted-foreground">Diff: </span>
                                  <span className={cn(
                                    "font-mono",
                                    mv.row_count.difference === 0 ? "text-green-500" : "text-red-500"
                                  )}>
                                    {mv.row_count.difference === 0 ? '0' : `+${formatNumber(mv.row_count.difference)}`}
                                  </span>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Results count */}
      <div className="text-sm text-muted-foreground" role="status" aria-live="polite">
        Showing {filteredAndSorted.length} of {report.model_validations.length} models
      </div>
    </div>
  );
}
