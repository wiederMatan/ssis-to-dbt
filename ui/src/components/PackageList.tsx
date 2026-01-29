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

const statusConfig: Record<MigrationStatus, { icon: typeof CheckCircle; color: string; bg: string }> = {
  pending: { icon: Clock, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  migrated: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
  warning: { icon: AlertTriangle, color: 'text-orange-500', bg: 'bg-orange-500/10' },
};

export function PackageList({ packages, migrationStatus, onPackageSelect, selectedPackage }: PackageListProps) {
  const [expandedPackages, setExpandedPackages] = useState<Set<string>>(new Set());

  const toggleExpand = (pkgName: string) => {
    const newExpanded = new Set(expandedPackages);
    if (newExpanded.has(pkgName)) {
      newExpanded.delete(pkgName);
    } else {
      newExpanded.add(pkgName);
    }
    setExpandedPackages(newExpanded);
  };

  const formatSize = (bytes: number) => {
    return (bytes / 1024).toFixed(1) + ' KB';
  };

  return (
    <div className="space-y-2">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Package className="h-5 w-5" />
        SSIS Packages
      </h2>

      {packages.map((pkg) => {
        const status = migrationStatus[pkg.name] || 'pending';
        const StatusIcon = statusConfig[status].icon;
        const isExpanded = expandedPackages.has(pkg.name);
        const isSelected = selectedPackage?.name === pkg.name;

        return (
          <div key={pkg.name} className="border rounded-lg overflow-hidden">
            {/* Package Header */}
            <div
              className={cn(
                "flex items-center gap-3 p-3 cursor-pointer transition-colors",
                isSelected ? "bg-primary/10" : "hover:bg-muted/50",
                statusConfig[status].bg
              )}
              onClick={() => onPackageSelect(pkg)}
            >
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(pkg.name);
                }}
                className="p-1 hover:bg-muted rounded"
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>

              <StatusIcon className={cn("h-5 w-5", statusConfig[status].color)} />

              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{pkg.name}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {pkg.description || 'No description'}
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                {formatSize(pkg.file_size_bytes)}
              </div>
            </div>

            {/* Package Details */}
            {isExpanded && (
              <div className="border-t bg-muted/20 p-3 space-y-3">
                {/* Connection Managers */}
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                    <Database className="h-3 w-3" />
                    Connection Managers ({pkg.connection_managers.filter(c => c.name).length})
                  </div>
                  <div className="space-y-1">
                    {pkg.connection_managers.filter(c => c.name).map((cm) => (
                      <div key={cm.id || cm.name} className="text-sm pl-4">
                        <span className="font-mono text-xs">{cm.name}</span>
                        {cm.database && (
                          <span className="text-muted-foreground"> → {cm.database}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tasks Summary */}
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                    <FileCode className="h-3 w-3" />
                    Tasks
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm pl-4">
                    <div>Execute SQL: {pkg.execute_sql_tasks.length}</div>
                    <div>Data Flow: {pkg.data_flow_tasks.length}</div>
                    {pkg.script_tasks.length > 0 && (
                      <div className="text-orange-500 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        Script: {pkg.script_tasks.length}
                      </div>
                    )}
                  </div>
                </div>

                {/* Warnings */}
                {pkg.parsing_warnings.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-orange-500 mb-1 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      Warnings ({pkg.parsing_warnings.length})
                    </div>
                    <div className="space-y-1 pl-4">
                      {pkg.parsing_warnings.map((warning, idx) => (
                        <div key={idx} className="text-xs text-orange-500">
                          {warning}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
