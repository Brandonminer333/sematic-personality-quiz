'use client';

import { useEffect, useRef, useState } from 'react';
import { colorForLabel } from '@/lib/colors';

const PLOTLY_CDN = 'https://cdn.plot.ly/plotly-2.35.2.min.js';
const FALLBACK_COLOR = '#cccccc';

let plotlyPromise = null;

function loadPlotly() {
  if (typeof window === 'undefined') return Promise.reject(new Error('SSR'));
  if (window.Plotly) return Promise.resolve(window.Plotly);
  if (plotlyPromise) return plotlyPromise;

  plotlyPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-plotly-cdn="true"]');
    if (existing) {
      existing.addEventListener('load', () => resolve(window.Plotly));
      existing.addEventListener('error', reject);
      return;
    }
    const script = document.createElement('script');
    script.src = PLOTLY_CDN;
    script.async = true;
    script.dataset.plotlyCdn = 'true';
    script.onload = () => resolve(window.Plotly);
    script.onerror = () => {
      plotlyPromise = null;
      reject(new Error('Failed to load Plotly from CDN'));
    };
    document.head.appendChild(script);
  });
  return plotlyPromise;
}

function buildTraces({ leaders, user, userType }) {
  const traces = [];
  const seenTypes = new Set();

  for (const leader of leaders) {
    const color = colorForLabel(leader.type) ?? FALLBACK_COLOR;
    const showInLegend = !seenTypes.has(leader.type);
    seenTypes.add(leader.type);

    traces.push({
      type: 'scatter3d',
      mode: 'lines',
      x: [0, leader.x],
      y: [0, leader.y],
      z: [0, leader.z],
      line: { color, width: 4 },
      opacity: 0.35,
      hoverinfo: 'skip',
      name: leader.type,
      legendgroup: leader.type,
      showlegend: showInLegend,
    });

    traces.push({
      type: 'scatter3d',
      mode: 'markers',
      x: [leader.x],
      y: [leader.y],
      z: [leader.z],
      marker: { size: 5, color, opacity: 0.9 },
      hovertemplate: `<b>${leader.name}</b><br>${leader.type}<extra></extra>`,
      name: leader.type,
      legendgroup: leader.type,
      showlegend: false,
    });
  }

  const userColor = colorForLabel(userType) ?? '#ffffff';

  traces.push({
    type: 'scatter3d',
    mode: 'lines',
    x: [0, user.x],
    y: [0, user.y],
    z: [0, user.z],
    line: { color: userColor, width: 9 },
    hoverinfo: 'skip',
    name: 'You',
    legendgroup: 'user',
    showlegend: true,
  });

  traces.push({
    type: 'scatter3d',
    mode: 'markers+text',
    x: [user.x],
    y: [user.y],
    z: [user.z],
    marker: {
      size: 12,
      color: userColor,
      symbol: 'diamond',
      line: { color: '#ffffff', width: 2 },
    },
    text: ['You'],
    textposition: 'top center',
    textfont: { color: '#ffffff', size: 13, family: 'Nunito, sans-serif' },
    hovertemplate: `<b>You</b><br>${userType}<extra></extra>`,
    name: 'You',
    legendgroup: 'user',
    showlegend: false,
  });

  return traces;
}

function buildLayout({ leaders, user }) {
  const xs = [user.x, ...leaders.map((l) => l.x)];
  const ys = [user.y, ...leaders.map((l) => l.y)];
  const zs = [user.z, ...leaders.map((l) => l.z)];
  const pad = 0.5;

  return {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    showlegend: true,
    legend: {
      bgcolor: 'rgba(26, 26, 46, 0.6)',
      bordercolor: '#2a2a40',
      borderwidth: 1,
      font: { color: '#f0f0f0', size: 11, family: 'Nunito, sans-serif' },
      itemsizing: 'constant',
      orientation: 'h',
      x: 0.5,
      xanchor: 'center',
      y: -0.05,
    },
    margin: { l: 0, r: 0, b: 0, t: 0 },
    scene: {
      bgcolor: 'rgba(0,0,0,0)',
      xaxis: {
        title: { text: 'PC1', font: { color: '#bbb' } },
        range: [Math.min(...xs) - pad, Math.max(...xs) + pad],
        gridcolor: '#2a2a40',
        zerolinecolor: '#444',
        color: '#888',
        backgroundcolor: 'rgba(0,0,0,0)',
      },
      yaxis: {
        title: { text: 'PC2', font: { color: '#bbb' } },
        range: [Math.min(...ys) - pad, Math.max(...ys) + pad],
        gridcolor: '#2a2a40',
        zerolinecolor: '#444',
        color: '#888',
        backgroundcolor: 'rgba(0,0,0,0)',
      },
      zaxis: {
        title: { text: 'PC3', font: { color: '#bbb' } },
        range: [Math.min(...zs) - pad, Math.max(...zs) + pad],
        gridcolor: '#2a2a40',
        zerolinecolor: '#444',
        color: '#888',
        backgroundcolor: 'rgba(0,0,0,0)',
      },
    },
  };
}

export default function PcaPlot({ projection, userType }) {
  const containerRef = useRef(null);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    if (!projection || !containerRef.current) return;

    let cancelled = false;
    let purgedTarget = null;

    setStatus('loading');

    loadPlotly()
      .then((Plotly) => {
        if (cancelled || !containerRef.current) return;
        const traces = buildTraces({
          leaders: projection.leaders,
          user: projection.user,
          userType,
        });
        const layout = buildLayout({
          leaders: projection.leaders,
          user: projection.user,
        });
        purgedTarget = containerRef.current;
        Plotly.react(purgedTarget, traces, layout, {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ['toImage', 'orbitRotation', 'resetCameraLastSave3d'],
        });
        setStatus('ready');
      })
      .catch(() => {
        if (cancelled) return;
        setStatus('error');
      });

    return () => {
      cancelled = true;
      if (purgedTarget && window.Plotly) {
        window.Plotly.purge(purgedTarget);
      }
    };
  }, [projection, userType]);

  if (!projection) return null;

  return (
    <div className="pca-plot">
      <div className="pca-plot__header">
        <div className="pca-plot__label">YOUR POSITION</div>
        <div className="pca-plot__title">Character map</div>
        <p className="pca-plot__subtitle">
          A 3D projection of each character&apos;s answer pattern. Your vector is
          highlighted — characters closest to it think most like you.
        </p>
      </div>
      <div ref={containerRef} className="pca-plot__canvas" />
      {status === 'loading' && (
        <div className="pca-plot__status">Loading visualization…</div>
      )}
      {status === 'error' && (
        <div className="pca-plot__status pca-plot__status--error">
          Couldn&apos;t load the visualization. Check your connection and try again.
        </div>
      )}
    </div>
  );
}
