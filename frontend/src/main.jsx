import { createRoot } from 'react-dom/client';
import ThisPlanChoice from "./components/ThisPlanChoice.jsx";
// import ServiceSummaryPanel from "./components/ServiceSummaryPanel.jsx";
// // 集計の表
// const summaryElement = document.getElementById('service-summary-root');
//
// if (summaryElement) {
//   const { userId, year, month } = summaryElement.dataset;
//
//   createRoot(summaryElement).render(
//     <ServiceSummaryPanel
//       userId={Number(userId)}
//       year={Number(year)}
//       month={Number(month)}
//     />
//   );
// }
console.info("[main] bundle executed");

const rootElement = document.getElementById("this-plan-root");
console.info("[main] root:", rootElement);

if (rootElement) {
  console.info("[main] mounting");
  createRoot(rootElement).render(
    <ThisPlanChoice careLevel={rootElement.dataset.careLevel} />
  );
}