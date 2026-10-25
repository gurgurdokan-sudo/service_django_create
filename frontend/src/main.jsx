import { createRoot } from 'react-dom/client';
import ThisPlanChoice from "./components/ThisPlanChoice.jsx";

console.info("[main] bundle executed");

const rootElement = document.getElementById("this-plan-root");
console.info("[main] root:", rootElement);

if (rootElement) {
  console.info("[main] mounting");
  createRoot(rootElement).render(
    <ThisPlanChoice careLevel={rootElement.dataset.careLevel} />
  );
}