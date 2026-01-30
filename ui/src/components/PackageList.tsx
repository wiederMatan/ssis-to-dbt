import { useState } from 'react';
import {
  Package,
  ChevronDown,
  ChevronRight,
  Database,
  FileCode,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { cn } from '../lib/utils';
import type { SSISPackage, MigrationStatus } from '../types';

interface PackageListProps {
  packages: SSISPackage[];
  migrationStatus: Record<string, MigrationStatus>;
  onPackageSelect: (pkg: SSISPackage) => void;
  selectedPackage: SSISPackage | null;
}

const statusConfig: Record<MigrationStatus, { icon: typeof CheckCircle; color: string; bg: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-500/10', label: 'Pending' },
  migrated: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Migrated' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Failed' },
  warning: { icon: AlertTriangle, color: 'text-orange-500', bg: 'bg-orange-500/10', label: 'Needs Review' },
};

export function PackageList({ packages, migrationStatus, onPackageSelect, selectedPackage }: PackageListProps) {
  const [expandedPackages, setExpandedPackages] = useState<Set<string>>(new Set());

  const toggleExpand = (pkgName: string, e: React.MouseEvent | React.KeyboardEvent) => {
    e.stopPropagation();
    const newExpanded = new Set(expandedPackages);
    if (newExpanded.has(pkgName)) {
      newExpanded.delete(pkgName);
    } else {
      newExpanded.add(pkgName);
    }
    setExpandedPackages(newExpanded);
  };

  const handleKeyDown = (e: React.KeyboardEvent, pkg: SSISPackage) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onPackageSelect(pkg);
    }
    if (e.key === 'ArrowRight' && !expandedPackages.has(pkg.name)) {
      e.preventDefault();
      toggleExpand(pkg.name, e);
    }
    if (e.key === 'ArrowLeft' && expandedPackages.has(pkg.name)) {
      e.preventDefault();
      toggleExpand(pkg.name, e);
    }
  };

  const formatSize = (bytes: number) => {
    return (bytes / 1024).toFixed(1) + ' KB';
  };

  return (
    <div className="space-y-2" role="listbox" aria-label="SSIS Packages">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Package className="h-5 w-5" aria-hidden="true" />
        SSIS Packages
        <span className="text-sm font-normal text-muted-foreground">({packages.length})</span>
      </h2>

      {packages.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Package className="h-8 w-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
          <p>No packages loaded</p>
        </div>
      ) : (
        packages.map((pkg) => {
          const status = migrationStatus[pkg.name] || 'pending';
          const StatusIcon = statusConfig[status].icon;
          const isExpanded = expandedPackages.has(pkg.name);
          const isSelected = selectedPackage?.name === pkg.name;

          return (
            <div
              key={pkg.name}
              className="border rounded-lg overflow-hidden"
              role="option"
              aria-selected={isSelected}
            >
              {/* Package Header */}
              <div
                className={cn(
                  "flex items-center gap-3 p-3 cursor-pointer transition-colors",
                  isSelected ? "bg-primary/10 ring-1 ring-primary/50" : "hover:bg-muted/50",
                  statusConfig[status].bg
                )}
                onClick={() => onPackageSelect(pkg)}
                onKeyDown={(e) => handleKeyDown(e, pkg)}
                tabIndex={0}
                role="button"
                aria-label={`${pkg.name}, ${statusConfig[status].label}, ${formatSize(pkg.file_size_bytes)}`}
              >
                <button
                  onClick={(e) => toggleExpand(pkg.name, e)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleExpand(pkg.name, e);
                    }
                  }}
                  className="p-1 hover:bg-muted rounded focus-visible:ring-2 focus-visible:ring-primary"
                  aria-expanded={isExpanded}
                  aria-label={isExpanded ? `Collapse ${pkg.name} details` : `Expand ${pkg.name} details`}
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <ChevronRight className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>

                <StatusIcon
                  className={cn("h-5 w-5 shrink-0", statusConfig[status].color)}
                  aria-hidden="true"
                />
                <span className="sr-only">{statusConfig[status].label}</span>

                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate" title={pkg.name}>
                    {pkg.name}
                  </div>
                  <div className="text-xs text-muted-foreground truncate" title={pkg.description || 'No description'}>
                    {pkg.description || 'No description'}
                  </div>
                </div>

                <div className="text-xs text-muted-foreground shrink-0">
                  {formatSize(pkg.file_size_bytes)}
                </div>
              </div>

              {/* Package Details */}
              {isExpanded && (
                <div
                  className="border-t bg-muted/20 p-3 space-y-3"
                  role="region"
                  aria-label={`${pkg.name} details`}
                >
                  {/* Connection Managers */}
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                      <Database className="h-3 w-3" aria-hidden="true" />
                      Connection Managers ({pkg.connection_managers.filter(c => c.name).length})
                    </div>
                    {pkg.connection_managers.filter(c => c.name).length === 0 ? (
                      <div className="text-sm text-muted-foreground pl-4">No connections defined</div>
                    ) : (
                      <ul className="space-y-1" aria-label="Connection managers">
                        {pkg.connection_managers.filter(c => c.name).map((cm) => (
                          <li key={cm.id || cm.name} className="text-sm pl-4">
                            <span className="font-mono text-xs">{cm.name}</span>
                            {cm.database && (
                              <span className="text-muted-foreground"> → {cm.database}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Tasks Summary */}
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                      <FileCode className="h-3 w-3" aria-hidden="true" />
                      Tasks
                    </div>
                    <dl className="grid grid-cols-2 gap-2 text-sm pl-4">
                      <div>
                        <dt className="sr-only">Execute SQL Tasks</dt>
                        <dd>Execute SQL: {pkg.execute_sql_tasks.length}</dd>
                      </div>
                      <div>
                        <dt className="sr-only">Data Flow Tasks</dt>
                        <dd>Data Flow: {pkg.data_flow_tasks.length}</dd>
                      </div>
                      {pkg.script_tasks.length > 0 && (
                        <div className="text-orange-500 flex items-center gap-1 col-span-2">
                          <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                          <dt className="sr-only">Script Tasks requiring review</dt>
                          <dd>Script: {pkg.script_tasks.length} (review needed)</dd>
                        </div>
                      )}
                    </dl>
                  </div>

                  {/* Warnings */}
                  {pkg.parsing_warnings.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-orange-500 mb-1 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                        Warnings ({pkg.parsing_warnings.length})
                      </div>
                      <ul className="space-y-1 pl-4" aria-label="Parsing warnings">
                        {pkg.parsing_warnings.map((warning, idx) => (
                          <li key={idx} className="text-xs text-orange-500">
                            {warning}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Metadata */}
                  <div className="pt-2 border-t text-xs text-muted-foreground">
                    {pkg.creator_name && <div>Created by: {pkg.creator_name}</div>}
                    {pkg.creation_date && (
                      <div>Created: {new Date(pkg.creation_date).toLocaleDateString()}</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
