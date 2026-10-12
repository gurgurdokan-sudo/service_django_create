import { createRoot } from 'react-dom/client';
import ServiceSummaryPanel from './components/ServiceSummaryPanel.jsx';
import ReactDOM from 'react-dom/client';

// 集計の表
const summaryRoot = document.getElementById('service-summary-root');
if (summaryRoot) {
  ReactDOM.createRoot(summaryRoot).render(<ServiceSummaryPanel />);
}