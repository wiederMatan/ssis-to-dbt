import { useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import type { SSISPackage, ValidationReport, TaskMapping } from './types';

// Import data files
import parsedPackages from './data/parsed_packages.json';
import validationLog from './data/validation_log.json';
import migrationMapping from './data/migration_mapping.json';

function App() {
  // Set dark mode by default
  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  // Type assertions for imported JSON
  const packages = parsedPackages as SSISPackage[];
  const validationReport = validationLog as ValidationReport;

  // Extract task mappings from migration mapping
  const taskMappings: TaskMapping[] = (migrationMapping as any).packages.flatMap(
    (pkg: any) => pkg.tasks
  );

  return (
    <Dashboard
      packages={packages}
      validationReport={validationReport}
      taskMappings={taskMappings}
    />
  );
}

export default App;
