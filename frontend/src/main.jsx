import { createRoot } from 'react-dom/client';
import ReactDOM from 'react-dom/client';
import CreateServerList from './pages/CreatedServiceList.jsx';
// // 集計の表
// const summaryRoot = document.getElementById('service-summary-root');
// if (summaryRoot) {
//   ReactDOM.createRoot(summaryRoot).render(<ServiceSummaryPanel />);
// }
const root = document.getElementById('root');
if (root) {
  createRoot(root).render(<CreateServerList />);
}