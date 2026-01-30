import { useState, useCallback, useEffect } from 'react';
import {
  Package,
  Terminal,
  CheckSquare,
  FileCode,
  BarChart3,
  Settings,
  Moon,
  Sun,
  RefreshCw,
  Menu,
  X,
  ChevronLeft,
  ChevronRight as ChevronRightIcon
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Tab navigation with keyboard
    if (e.altKey && e.key >= '1' && e.key <= '4') {
      e.preventDefault();
      const tabIndex = parseInt(e.key) - 1;
      if (tabs[tabIndex]) {
        setActiveTab(tabs[tabIndex].id);
      }
    }
    // Toggle sidebar with Ctrl+B
    if (e.ctrlKey && e.key === 'b') {
      e.preventDefault();
      setSidebarCollapsed(prev => !prev);
    }
    // Close mobile menu with Escape
    if (e.key === 'Escape' && mobileMenuOpen) {
      setMobileMenuOpen(false);
    }
  }, [mobileMenuOpen]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Close mobile menu when clicking outside
  useEffect(() => {
    if (mobileMenuOpen) {
      const handleClickOutside = (e: MouseEvent) => {
        const sidebar = document.getElementById('mobile-sidebar');
        if (sidebar && !sidebar.contains(e.target as Node)) {
          setMobileMenuOpen(false);
        }
      };
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [mobileMenuOpen]);

  // Calculate stats
  const totalTasks = packages.reduce((sum, pkg) =>
    sum + pkg.execute_sql_tasks.length + pkg.data_flow_tasks.length, 0
  );
  const convertedModels = taskMappings.filter(t => t.status === 'converted').length;
  const manualReview = packages.reduce((sum, pkg) => sum + pkg.script_tasks.length, 0);

  return (
    <div className={cn("min-h-screen flex flex-col", darkMode && "dark")}>
      {/* Skip to main content for accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Header */}
      <header className="border-b bg-card" role="banner">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Mobile menu button */}
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="md:hidden p-2 rounded-lg hover:bg-muted transition-colors"
                aria-label="Open navigation menu"
                aria-expanded={mobileMenuOpen}
              >
                <Menu className="h-5 w-5" />
              </button>

              <div className="p-2 rounded-lg bg-primary/10">
                <BarChart3 className="h-6 w-6 text-primary" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-xl font-bold">SSIS to dbt Migration</h1>
                <p className="text-sm text-muted-foreground hidden sm:block">Migration Factory Dashboard</p>
              </div>
            </div>

            {/* Stats Pills */}
            <div className="hidden lg:flex items-center gap-4" role="status" aria-label="Migration statistics">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted">
                <Package className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <span className="text-sm font-medium">{packages.length} Packages</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted">
                <FileCode className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <span className="text-sm font-medium">{totalTasks} Tasks</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10">
                <CheckSquare className="h-4 w-4 text-green-500" aria-hidden="true" />
                <span className="text-sm font-medium text-green-500">{convertedModels} Converted</span>
              </div>
              {manualReview > 0 && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/10">
                  <span className="text-sm font-medium text-yellow-500">{manualReview} Manual Review</span>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 sm:gap-2" role="toolbar" aria-label="Dashboard actions">
              <button
                onClick={handleRefresh}
                className="p-2 rounded-lg hover:bg-muted transition-colors focus-visible:ring-2 focus-visible:ring-primary"
                aria-label="Refresh data"
              >
                <RefreshCw className="h-5 w-5" aria-hidden="true" />
              </button>
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg hover:bg-muted transition-colors focus-visible:ring-2 focus-visible:ring-primary"
                aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
              >
                {darkMode ? <Sun className="h-5 w-5" aria-hidden="true" /> : <Moon className="h-5 w-5" aria-hidden="true" />}
              </button>
              <button
                className="p-2 rounded-lg hover:bg-muted transition-colors focus-visible:ring-2 focus-visible:ring-primary"
                aria-label="Open settings"
              >
                <Settings className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Stats Bar */}
      <div className="lg:hidden border-b bg-card/50 px-4 py-2 overflow-x-auto" role="status" aria-label="Migration statistics">
        <div className="flex items-center gap-3 min-w-max">
          <span className="text-xs text-muted-foreground">{packages.length} Packages</span>
          <span className="text-muted-foreground">|</span>
          <span className="text-xs text-muted-foreground">{totalTasks} Tasks</span>
          <span className="text-muted-foreground">|</span>
          <span className="text-xs text-green-500">{convertedModels} Converted</span>
          {manualReview > 0 && (
            <>
              <span className="text-muted-foreground">|</span>
              <span className="text-xs text-yellow-500">{manualReview} Review</span>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Mobile Sidebar Overlay */}
        <div
          className={cn(
            "sidebar-overlay md:hidden",
            mobileMenuOpen && "open"
          )}
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />

        {/* Sidebar */}
        <aside
          id="mobile-sidebar"
          className={cn(
            "sidebar bg-card flex flex-col border-r",
            sidebarCollapsed ? "w-16" : "w-64",
            mobileMenuOpen && "open"
          )}
          role="navigation"
          aria-label="Main navigation"
        >
          {/* Mobile close button */}
          <div className="md:hidden flex items-center justify-between p-4 border-b">
            <span className="font-semibold">Navigation</span>
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="p-2 rounded-lg hover:bg-muted"
              aria-label="Close navigation menu"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Collapse button (desktop only) */}
          <div className="hidden md:flex items-center justify-end p-2">
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-1.5 rounded-lg hover:bg-muted transition-colors"
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={sidebarCollapsed ? "Expand (Ctrl+B)" : "Collapse (Ctrl+B)"}
            >
              {sidebarCollapsed ? (
                <ChevronRightIcon className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          </div>

          {/* Navigation */}
          <nav className="p-2 md:p-4 space-y-1" role="tablist" aria-label="Dashboard sections">
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setMobileMenuOpen(false);
                  }}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                  aria-controls={`panel-${tab.id}`}
                  tabIndex={activeTab === tab.id ? 0 : -1}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                    activeTab === tab.id
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted focus-visible:bg-muted",
                    sidebarCollapsed && "justify-center"
                  )}
                  title={sidebarCollapsed ? `${tab.label} (Alt+${index + 1})` : `Alt+${index + 1}`}
                >
                  <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                  <span className={cn("sidebar-text", sidebarCollapsed && "hidden md:hidden")}>
                    {tab.label}
                  </span>
                </button>
              );
            })}
          </nav>

          {/* Package List (when packages tab is active) */}
          {activeTab === 'packages' && !sidebarCollapsed && (
            <div className="flex-1 overflow-auto p-4 pt-0">
              <PackageList
                packages={packages}
                migrationStatus={migrationStatus}
                onPackageSelect={(pkg) => {
                  setSelectedPackage(pkg);
                  setMobileMenuOpen(false);
                }}
                selectedPackage={selectedPackage}
              />
            </div>
          )}

          {/* Stats Summary */}
          <div className={cn(
            "p-4 border-t bg-muted/30",
            sidebarCollapsed && "hidden"
          )}>
            <div className="text-xs text-muted-foreground mb-2">Migration Summary</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Conversion Rate</span>
                <span className="font-medium text-green-500">
                  {((convertedModels / Math.max(totalTasks, 1)) * 100).toFixed(1)}%
                </span>
              </div>
              <div
                className="w-full h-2 bg-muted rounded-full overflow-hidden"
                role="progressbar"
                aria-valuenow={Math.round((convertedModels / Math.max(totalTasks, 1)) * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Conversion progress"
              >
                <div
                  className="h-full bg-green-500 rounded-full transition-all duration-500"
                  style={{ width: `${(convertedModels / Math.max(totalTasks, 1)) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </aside>

        {/* Main Panel */}
        <main id="main-content" className="flex-1 overflow-auto" role="main">
          <div className="h-full p-4 md:p-6">
            <div
              id={`panel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={activeTab}
              tabIndex={0}
              className="h-full"
            >
              {activeTab === 'packages' && selectedPackage && (
                <div className="space-y-4">
                  <h2 className="text-xl md:text-2xl font-bold">{selectedPackage.name}</h2>
                  <p className="text-muted-foreground">{selectedPackage.description}</p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
                    <div className="p-4 border rounded-lg overflow-x-auto">
                      <h3 className="font-medium mb-2">Execution Order</h3>
                      <div className="flex flex-wrap items-center gap-2">
                        {selectedPackage.precedence_constraints.map((pc, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            <span className="px-2 py-1 bg-muted rounded text-sm font-mono whitespace-nowrap">
                              {pc.from_task}
                            </span>
                            <span className="text-muted-foreground" aria-hidden="true">→</span>
                            <span className="px-2 py-1 bg-muted rounded text-sm font-mono whitespace-nowrap">
                              {pc.to_task}
                            </span>
                            {idx < selectedPackage.precedence_constraints.length - 1 && (
                              <span className="text-muted-foreground mx-2 hidden sm:inline">|</span>
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
                    <Package className="h-16 w-16 mx-auto mb-4 opacity-50" aria-hidden="true" />
                    <p className="text-lg">Select a package to view details</p>
                    <p className="text-sm mt-2">Choose from the sidebar or use the mobile menu</p>
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
          </div>
        </main>
      </div>
    </div>
  );
}
