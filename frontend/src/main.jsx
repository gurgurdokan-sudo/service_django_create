import { createRoot } from 'react-dom/client';
import ServiceSummaryPanel from './components/ServiceSummaryPanel.jsx';

const rootElement = document.getElementById('react-summary-root');

if (rootElement) {
  createRoot(rootElement).render(<ServiceSummaryPanel />);
}