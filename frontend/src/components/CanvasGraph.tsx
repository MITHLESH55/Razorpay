import React, { useState } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Smartphone,
  Globe,
  User,
  Store,
} from 'lucide-react';
import { GraphNode, GraphEdge } from '../types';

interface CanvasGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onSelectNode?: (node: GraphNode) => void;
  selectedNodeId?: string;
}

export const CanvasGraph: React.FC<CanvasGraphProps> = ({
  nodes,
  edges,
  onSelectNode,
  selectedNodeId,
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Calculate deterministic layout coordinates for nodes
  const layoutNodes = React.useMemo(() => {
    const width = 680;
    const height = 440;
    const centerX = width / 2;
    const centerY = height / 2;

    if (nodes.length === 0) return [];

    const result = nodes.map((node, index) => {
      if (
        node.id.includes('FARMA-101') ||
        node.id.includes('CYCLE-202') ||
        node.role.includes('Primary') ||
        node.role.includes('Target')
      ) {
        return { ...node, x: centerX, y: centerY };
      }

      // Arrange other nodes in an ellipse around the center
      const count = Math.max(1, nodes.length - 1);
      const angle = (2 * Math.PI * index) / count;
      const radiusX = node.type === 'device' || node.type === 'ip' ? 220 : 170;
      const radiusY = node.type === 'device' || node.type === 'ip' ? 140 : 110;

      return {
        ...node,
        x: centerX + radiusX * Math.cos(angle),
        y: centerY + radiusY * Math.sin(angle),
      };
    });

    return result;
  }, [nodes]);

  const getNodeColor = (node: GraphNode) => {
    if (node.role.includes('Primary') || node.tier === 'PRIMARY') {
      return {
        bg: 'fill-red-50',
        stroke: 'stroke-[#C53030]',
        iconColor: 'text-[#C53030]',
        border: '#C53030',
      };
    }
    if (node.type === 'device') {
      return {
        bg: 'fill-amber-50',
        stroke: 'stroke-[#B7791F]',
        iconColor: 'text-[#B7791F]',
        border: '#B7791F',
      };
    }
    if (node.type === 'ip') {
      return {
        bg: 'fill-purple-50',
        stroke: 'stroke-purple-600',
        iconColor: 'text-purple-600',
        border: '#7C3AED',
      };
    }
    if (node.type === 'merchant') {
      return {
        bg: 'fill-blue-50',
        stroke: 'stroke-[#2563A6]',
        iconColor: 'text-[#2563A6]',
        border: '#2563A6',
      };
    }
    return {
      bg: 'fill-slate-100',
      stroke: 'stroke-[#183B67]',
      iconColor: 'text-[#183B67]',
      border: '#183B67',
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div className="relative w-full h-[460px] bg-[#F8FAFC] rounded-xl border border-[#D9DEE7] overflow-hidden select-none shadow-xs">
      {/* Canvas Top Bar Controls */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#D9DEE7] text-xs font-mono text-[#172033] shadow-sm">
        <span className="font-bold text-[#183B67]">Ring Subtopology</span>
        <span className="text-[#CBD5E1]">|</span>
        <span>{nodes.length} Entities</span>
        <span className="text-[#CBD5E1]">|</span>
        <span>{edges.length} Relational Links</span>
      </div>

      <div className="absolute top-3 right-3 z-10 flex items-center gap-1 bg-white/95 backdrop-blur-md p-1 rounded-lg border border-[#D9DEE7] shadow-sm">
        <button
          onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
          className="p-1.5 rounded hover:bg-[#F1F5F9] text-[#667085] hover:text-[#172033]"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
          className="p-1.5 rounded hover:bg-[#F1F5F9] text-[#667085] hover:text-[#172033]"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="p-1.5 rounded hover:bg-[#F1F5F9] text-[#667085] hover:text-[#172033]"
          title="Reset View"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* SVG Interactive Graph Canvas */}
      <svg
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <defs>
          <radialGradient id="ringGlowLight" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#C53030" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#C53030" stopOpacity="0" />
          </radialGradient>
          <marker
            id="arrowLight"
            viewBox="0 0 10 10"
            refX="22"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#94A3B8" />
          </marker>
        </defs>

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Background grid dots */}
          <pattern id="gridLight" width="28" height="28" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1" fill="#E2E8F0" />
          </pattern>
          <rect x="-1000" y="-1000" width="3000" height="3000" fill="url(#gridLight)" />

          {/* Central Ring Pulse for High Risk Cases */}
          {layoutNodes.length > 0 && (
            <circle
              cx={layoutNodes[0].x}
              cy={layoutNodes[0].y}
              r="180"
              fill="url(#ringGlowLight)"
              className="animate-pulse"
            />
          )}

          {/* Edges */}
          {edges.map((edge) => {
            const src = layoutNodes.find((n) => n.id === edge.source);
            const tgt = layoutNodes.find((n) => n.id === edge.target);
            if (!src || !tgt) return null;

            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;

            return (
              <g key={edge.id} className="group">
                <line
                  x1={src.x}
                  y1={src.y}
                  x2={tgt.x}
                  y2={tgt.y}
                  stroke={edge.weight > 0.8 ? '#C53030' : '#94A3B8'}
                  strokeWidth={edge.weight > 0.8 ? 2.5 : 1.5}
                  strokeDasharray={edge.label.includes('SHARED') ? '4 3' : undefined}
                  markerEnd="url(#arrowLight)"
                  className="opacity-80 group-hover:opacity-100 transition-opacity"
                />
                <rect
                  x={midX - 45}
                  y={midY - 10}
                  width="90"
                  height="18"
                  rx="4"
                  fill="#FFFFFF"
                  stroke="#CBD5E1"
                  strokeWidth="1"
                  className="opacity-95 shadow-xs"
                />
                <text
                  x={midX}
                  y={midY + 2}
                  textAnchor="middle"
                  className="text-[9px] font-mono font-medium fill-[#475569] select-none pointer-events-none"
                >
                  {edge.label}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {layoutNodes.map((node) => {
            const colors = getNodeColor(node);
            const isSelected = selectedNodeId === node.id;
            const isTarget = node.role.includes('Primary') || node.role.includes('Target');

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={() => onSelectNode?.(node)}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer transition-transform hover:scale-110"
              >
                {/* Outer halo */}
                <circle
                  r={isTarget ? 28 : 22}
                  fill="none"
                  stroke={colors.border}
                  strokeWidth={isSelected ? 4 : isTarget ? 2.5 : 1.5}
                  strokeDasharray={isTarget ? undefined : '3 2'}
                  className={isTarget ? 'animate-spin-slow' : ''}
                />

                {/* Node Body */}
                <circle
                  r={isTarget ? 24 : 18}
                  className={`${colors.bg} ${colors.stroke}`}
                  strokeWidth="2"
                />

                {/* Icon inside Node */}
                <g transform="translate(-8, -8)" className="pointer-events-none">
                  {node.type === 'device' ? (
                    <Smartphone className={`w-4 h-4 ${colors.iconColor}`} />
                  ) : node.type === 'ip' ? (
                    <Globe className={`w-4 h-4 ${colors.iconColor}`} />
                  ) : node.type === 'merchant' ? (
                    <Store className={`w-4 h-4 ${colors.iconColor}`} />
                  ) : (
                    <User className={`w-4 h-4 ${colors.iconColor}`} />
                  )}
                </g>

                {/* Label */}
                <text
                  y={isTarget ? 38 : 32}
                  textAnchor="middle"
                  className="text-[10.5px] font-mono font-bold fill-[#172033] select-none pointer-events-none"
                >
                  {node.label.length > 20 ? node.label.slice(0, 18) + '…' : node.label}
                </text>

                {/* Risk Score Pill */}
                <rect
                  x="-18"
                  y={isTarget ? -36 : -30}
                  width="36"
                  height="14"
                  rx="7"
                  fill="#FFFFFF"
                  stroke={colors.border}
                  strokeWidth="1"
                />
                <text
                  y={isTarget ? -26 : -20}
                  textAnchor="middle"
                  className="text-[9px] font-mono font-bold fill-[#172033]"
                >
                  {(node.risk_score * 100).toFixed(0)}%
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Hover Info Tooltip */}
      {hoveredNode && (
        <div className="absolute bottom-3 left-3 z-20 bg-white p-3 rounded-xl border border-[#D9DEE7] shadow-lg text-xs space-y-1 max-w-xs pointer-events-none animate-in fade-in">
          <div className="flex items-center justify-between gap-3 font-bold text-[#172033]">
            <span>{hoveredNode.id}</span>
            <span className="font-mono text-[#C53030]">Score: {(hoveredNode.risk_score * 100).toFixed(1)}%</span>
          </div>
          <div className="text-[11px] text-[#667085]">
            <span className="text-[#98A2B3]">Role:</span> {hoveredNode.role} | <span className="text-[#98A2B3]">Tier:</span> {hoveredNode.tier}
          </div>
        </div>
      )}

      {/* Legend Footer */}
      <div className="absolute bottom-3 right-3 z-10 flex items-center gap-3 bg-white/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#D9DEE7] text-[10px] font-mono text-[#667085] shadow-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#C53030]" /> Primary Suspect
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#B7791F]" /> Device Farm
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-purple-600" /> Proxy IP
        </div>
      </div>
    </div>
  );
};
