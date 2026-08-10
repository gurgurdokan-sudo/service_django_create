import React from 'react'

export default function Breadcrumb({ items }) {
  if (!items || !Array.isArray(items)) return null;

  return (
    <nav className='bread' style={{ margin: '15px 0', fontSize: '14px' }}>
      {items.map((item, index) => (
        <span key={index}>
          {index < items.length - 1 ? (
            <>
              <a href={item.url} style={{ color: '#007bff', textDecoration: 'none' }}>
                {item.label}
              </a>
              <span style={{ margin: '0 8px', color: '#6c757d' }}>&nbsp;&gt;&nbsp;</span>
            </>
          ) : (
            <span style={{ color: '#6c757d' }}>{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
