import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import DatasetUpload from './pages/DatasetUpload';
import StudentAnalytics from './pages/StudentAnalytics';
import RiskPredictions from './pages/RiskPredictions';
import ModelPerformance from './pages/ModelPerformance';
import Explainability from './pages/Explainability';
import Interventions from './pages/Interventions';
import Settings from './pages/Settings';
import { AppStoreProvider } from './hooks/AppStore';

export default function App() {
  return (
    <AppStoreProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="upload" element={<DatasetUpload />} />
          <Route path="analytics" element={<StudentAnalytics />} />
          <Route path="predictions" element={<RiskPredictions />} />
          <Route path="performance" element={<ModelPerformance />} />
          <Route path="explainability" element={<Explainability />} />
          <Route path="interventions" element={<Interventions />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AppStoreProvider>
  );
}
