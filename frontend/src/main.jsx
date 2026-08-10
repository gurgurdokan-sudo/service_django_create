import React from 'react'
import ReactDOM from 'react-dom/client'
import Breadcrumb from './components/Breadcrumb'

const breadEl = document.getElementById('bread');

if (breadEl) {
  try {
    const itemsStr = breadEl.getAttribute('data-items');
    const items = itemsStr ? JSON.parse(itemsStr) : [];
    
    console.log("Reactが受け取ったデータ:", items); // ブラウザのコンソールに表示されます

    ReactDOM.createRoot(breadEl).render(
      <React.StrictMode>
        <Breadcrumb items={items} />
      </React.StrictMode>
    );
  } catch (error) {
    console.error("JSONの解析に失敗しました:", error);
  }
}