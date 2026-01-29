import { useState } from 'react';
import {
  Package,
  Terminal,
  CheckSquare,
  FileCode,
  BarChart3,
  Settings,
  Moon,
  Sun,
  RefreshCw
} from 'lucide-react';
import { cn } from '../lib/utils';
import { PackageList } from './PackageList';
import { LiveLogs, generateSampleLogs } from './LiveLogs';
import { ValidationView } from './ValidationView';
import { DiffViewer } from './DiffViewer';
import type { SSISPackage, MigrationStatus, ValidationReport, TaskMapping, LogEntry } from '../types';

type TabId = 'packages' | 'logs' | 'validation' | 'diff';

interface DashboardProps {
  packages: SSISPackage[];
  validationReport: ValidationReport;
  taskMappings: TaskMapping[];
}

const tabs: { id: TabId; label: string; icon: typeof Package }[] = [
  { id: 'packages', label: 'Packages', icon: Package },
  { id: 'logs', label: 'Live Logs', icon: Terminal },
  { id: 'validation', label: 'Validation', icon: CheckSquare },
  { id: 'diff', label: 'SQL Diff', icon: FileCode },
];

export function Dashboard({ packages, validationReport, taskMappings }: DashboardProps) {
  const [activeTab, setActiveTab] = useState<TabId>('packages');
  const [darkMode, setDarkMode] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState<SSISPackage | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>(generateSampleLogs());

  // Derive migration status from packages
  const migrationStatus: Record<string, MigrationStatus> = {};
  packages.forEach(pkg => {
    if (pkg.script_tasks.length > 0) {
      migrationStatus[pkg.name] = 'warning';
    } else if (pkg.parsing_errors.length > 0) {
      migrationStatus[pkg.name] = 'failed';
    } else {
      migrationStatus[pkg.name] = 'migrated';
    }
  });

  // Toggle dark mode
  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark', !darkMode);
  };

  // Clear logs
  const handleClearLogs = () => {
    setLogs([]);
  };

  // Refresh data (simulate)
  const handleRefresh = () => {
    setLogs(prev => [...prev, {
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      level: 'info',
      message: 'Refreshing data...',
      source: 'ui'
    }]);
  };

  // Calculate stats
  const totalTasks = packages.reduce((sum, pkg) =>
    sum + pkg.execute_sql_tasks.length + pkg.data_flow_tasks.length, 0
  );
  const convertedModels = taskMappings.filter(t => t.status === 'converted').length;
  const manualReview = packages.reduce((sum, pkg) => sum + pkg.script_tasks.length, 0);

  return (
    <div className={cn("min-h-screen flex flex-col", darkMode && "dark")}>
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <BarChart3 className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold">SSIS to dbt Migration</h1>
                <p className="text-sm text-muted-foreground">Migration Factory Dashboard</p>
              </div>
            </div>

            {/* Stats Pills */}
            <div className="hidden md:flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted">
                <Package className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{packages.length} Packages</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted">
                <FileCode className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{totalTasks} Tasks</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10">
                <CheckSquare className="h-4 w-4 text-green-500" />
                <span className="text-sm font-medium text-green-500">{convertedModels} Converted</span>
              </div>
              {manualReview > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10">
                  <span className="text-sm font-medium text-yellow-500">{manualReview} Manual Review</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleRefresh}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
                title="Refresh"
              >
                <RefreshCw className="h-5 w-5" />
              </button>
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
                title="Toggle theme"
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
              <button
                className="p-2 rounded-lg hover:bg-muted transition-colors"
                title="Settings"
              >
                <Settings className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <aside className="w-64 border-r bg-card flex flex-col">
          {/* Navigation */}
          <nav className="p-4 space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                    activeTab === tab.id
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted"
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Package List (when packages tab is active) */}
          {activeTab === 'packages' && (
            <div className="flex-1 overflow-auto p-4 pt-0">
              <PackageList
                packages={packages}
                migrationStatus={migrationStatus}
                onPackageSelect={setSelectedPackage}
                selectedPackage={selectedPackage}
              />
            </div>
          )}

          {/* Stats Summary */}
          <div className="p-4 border-t bg-muted/30">
            <div className="text-xs text-muted-foreground mb-2">Migration Summary</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Conversion Rate</span>
                <span className="font-medium text-green-500">
                  {((convertedModels / Math.max(totalTasks, 1)) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{ width: `${(convertedModels / Math.max(totalTasks, 1)) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </aside>

        {/* Main Panel */}
        <main className="flex-1 overflow-auto">
          <div className="h-full p-6">
            {activeTab === 'packages' && selectedPackage && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold">{selectedPackage.name}</h2>
                <p className="text-muted-foreground">{selectedPackage.description}</p>

                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold">{selectedPackage.execute_sql_tasks.length}</div>
                    <div className="text-sm text-muted-foreground">Execute SQL Tasks</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold">{selectedPackage.data_flow_tasks.length}</div>
                    <div className="text-sm text-muted-foreground">Data Flow Tasks</div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="text-2xl font-bold">{selectedPackage.connection_managers.filter(c => c.name).length}</div>
                    <div className="text-sm text-muted-foreground">Connections</div>
                  </div>
                </div>

                {/* Execution Order */}
                {selectedPackage.precedence_constraints.length > 0 && (
                  <div className="p-4 border rounded-lg">
                    <h3 className="font-medium mb-2">Execution Order</h3>
                    <div className="flex flex-wrap items-center gap-2">
                      {selectedPackage.precedence_constraints.map((pc, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="px-2 py-1 bg-muted rounded text-sm font-mono">
                            {pc.from_task}
                          </span>
                          <span className="text-muted-foreground">→</span>
                          <span className="px-2 py-1 bg-muted rounded text-sm font-mono">
                            {pc.to_task}
                          </span>
                          {idx < selectedPackage.precedence_constraints.length - 1 && (
                            <span className="text-muted-foreground mx-2">|</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'packages' && !selectedPackage && (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Package className="h-16 w-16 mx-auto mb-4 opacity-50" />
                  <p className="text-lg">Select a package to view details</p>
                </div>
              </div>
            )}

            {activeTab === 'logs' && (
              <div className="h-full">
                <LiveLogs logs={logs} onClear={handleClearLogs} />
              </div>
            )}

            {activeTab === 'validation' && (
              <ValidationView report={validationReport} />
            )}

            {activeTab === 'diff' && (
              <div className="h-full">
                <DiffViewer
                  ssisPackage={selectedPackage}
                  taskMappings={taskMappings}
                />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
