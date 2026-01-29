import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Database,
  Key,
  Calculator,
  ArrowUpDown
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { ValidationReport, ModelValidation, ValidationStatus } from '../types';

interface ValidationViewProps {
  report: ValidationReport;
}

type SortField = 'model' | 'status' | 'rows';
type SortDirection = 'asc' | 'desc';

const statusConfig: Record<ValidationStatus, { icon: typeof CheckCircle; color: string; bg: string; text: string }> = {
  passed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', text: 'PASSED' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', text: 'FAILED' },
  warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', text: 'WARNING' },
  skipped: { icon: AlertTriangle, color: 'text-gray-500', bg: 'bg-gray-500/10', text: 'SKIPPED' },
};

export function ValidationView({ report }: ValidationViewProps) {
  const [expandedModels, setExpandedModels] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('model');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [filterStatus, setFilterStatus] = useState<ValidationStatus | 'all'>('all');

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
    .filter(m => filterStatus === 'all' || m.overall_status === filterStatus)
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

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-card border">
          <div className="text-2xl font-bold">{report.total_models}</div>
          <div className="text-sm text-muted-foreground">Total Models</div>
        </div>
        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
          <div className="text-2xl font-bold text-green-500">{report.models_passed}</div>
          <div className="text-sm text-green-500/70">Passed</div>
        </div>
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="text-2xl font-bold text-red-500">{report.models_failed}</div>
          <div className="text-sm text-red-500/70">Failed</div>
        </div>
        <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
          <div className="text-2xl font-bold text-yellow-500">{report.models_warning}</div>
          <div className="text-sm text-yellow-500/70">Warnings</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground">Filter:</span>
        <div className="flex gap-2">
          {(['all', 'passed', 'failed', 'warning'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={cn(
                "px-3 py-1 text-sm rounded-full border transition-colors",
                filterStatus === status
                  ? status === 'all'
                    ? "bg-primary text-primary-foreground"
                    : statusConfig[status].bg + " " + statusConfig[status].color
                  : "hover:bg-muted"
              )}
            >
              {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="w-8 p-3"></th>
              <th
                className="p-3 text-left cursor-pointer hover:bg-muted"
                onClick={() => handleSort('model')}
              >
                <div className="flex items-center gap-2">
                  Model
                  <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
                </div>
              </th>
              <th className="p-3 text-left">Legacy Table</th>
              <th
                className="p-3 text-right cursor-pointer hover:bg-muted"
                onClick={() => handleSort('rows')}
              >
                <div className="flex items-center justify-end gap-2">
                  Row Count
                  <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
                </div>
              </th>
              <th className="p-3 text-center">Diff</th>
              <th
                className="p-3 text-center cursor-pointer hover:bg-muted"
                onClick={() => handleSort('status')}
              >
                <div className="flex items-center justify-center gap-2">
                  Status
                  <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSorted.map((mv) => {
              const isExpanded = expandedModels.has(mv.model_name);
              const StatusIcon = statusConfig[mv.overall_status].icon;

              return (
                <>
                  <tr
                    key={mv.model_name}
                    className={cn(
                      "border-t cursor-pointer hover:bg-muted/30",
                      statusConfig[mv.overall_status].bg
                    )}
                    onClick={() => toggleExpand(mv.model_name)}
                  >
                    <td className="p-3">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </td>
                    <td className="p-3 font-mono text-sm">{mv.model_name}</td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {mv.legacy_table || '-'}
                    </td>
                    <td className="p-3 text-right font-mono text-sm">
                      {mv.row_count ? formatNumber(mv.row_count.dbt_count) : '-'}
                    </td>
                    <td className="p-3 text-center">
                      {mv.row_count && (
                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs font-mono",
                          mv.row_count.difference === 0
                            ? "bg-green-500/20 text-green-500"
                            : "bg-red-500/20 text-red-500"
                        )}>
                          {mv.row_count.difference === 0 ? '0' : `+${formatNumber(mv.row_count.difference)}`}
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      <div className="flex items-center justify-center gap-2">
                        <StatusIcon className={cn("h-4 w-4", statusConfig[mv.overall_status].color)} />
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
                        <div className="grid grid-cols-3 gap-4">
                          {/* Row Count Details */}
                          {mv.row_count && (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm font-medium">
                                <Database className="h-4 w-4" />
                                Row Count Comparison
                              </div>
                              <div className="pl-6 space-y-1 text-sm">
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Legacy:</span>
                                  <span className="font-mono">{formatNumber(mv.row_count.legacy_count)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">dbt:</span>
                                  <span className="font-mono">{formatNumber(mv.row_count.dbt_count)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Variance:</span>
                                  <span className="font-mono">{mv.row_count.difference_percent.toFixed(4)}%</span>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* PK Integrity */}
                          {mv.primary_key && (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm font-medium">
                                <Key className="h-4 w-4" />
                                Primary Key ({mv.primary_key.pk_column})
                              </div>
                              <div className="pl-6 space-y-1 text-sm">
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">NULL values:</span>
                                  <span className={cn(
                                    "font-mono",
                                    mv.primary_key.null_count > 0 ? "text-red-500" : "text-green-500"
                                  )}>
                                    {mv.primary_key.null_count}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Duplicates:</span>
                                  <span className={cn(
                                    "font-mono",
                                    mv.primary_key.duplicate_count > 0 ? "text-red-500" : "text-green-500"
                                  )}>
                                    {mv.primary_key.duplicate_count}
                                  </span>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Checksums */}
                          {mv.checksums.length > 0 && (
                            <div className="space-y-2">
                              <div className="flex items-center gap-2 text-sm font-medium">
                                <Calculator className="h-4 w-4" />
                                Numeric Checksums
                              </div>
                              <div className="pl-6 space-y-1 text-sm">
                                {mv.checksums.map((cs) => (
                                  <div key={cs.column} className="flex justify-between">
                                    <span className="text-muted-foreground font-mono">{cs.column}:</span>
                                    <span className={cn(
                                      "font-mono",
                                      cs.variance_percent === 0 ? "text-green-500" : "text-yellow-500"
                                    )}>
                                      {cs.variance_percent.toFixed(4)}%
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* SSIS Source Info */}
                        <div className="mt-4 pt-4 border-t text-sm text-muted-foreground">
                          <span className="font-medium">Source: </span>
                          {mv.ssis_package} → {mv.ssis_task}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
