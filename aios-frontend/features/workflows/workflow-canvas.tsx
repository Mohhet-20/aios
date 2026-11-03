"use client";

import { useMemo, useState, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
  applyNodeChanges,
  applyEdgeChanges,
  type NodeChange,
  type EdgeChange,
  addEdge,
  type Connection,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { WorkflowNode } from "@/components/graph/workflow-node";
import type { WorkflowDefinition } from "@/types";

const nodeTypes = { workflowNode: WorkflowNode };

/**
 * Visual workflow canvas built on React Flow. Nodes represent Agent/Tool/
 * Condition/Human/Start/End steps per the Workflow Engine's step contract
 * (Phase 1, Step Workflow Engine); edges represent control flow, optionally
 * labeled with a branch condition (e.g. "yes"/"no").
 */
export function WorkflowCanvas({ workflow }: { workflow: WorkflowDefinition }) {
  const initialNodes: Node[] = useMemo(
    () =>
      workflow.nodes.map((n) => ({
        id: n.id,
        type: "workflowNode",
        position: n.position,
        data: { label: n.label, type: n.type },
      })),
    [workflow]
  );
  const initialEdges: Edge[] = useMemo(
    () =>
      workflow.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: { stroke: "hsl(var(--border))" },
        labelStyle: { fontSize: 10, fill: "hsl(var(--muted-foreground))" },
      })),
    [workflow]
  );

  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

  const onNodesChange = useCallback((changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)), []);
  const onEdgesChange = useCallback((changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)), []);
  const onConnect = useCallback((connection: Connection) => setEdges((eds) => addEdge(connection, eds)), []);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      nodeTypes={nodeTypes}
      fitView
      proOptions={{ hideAttribution: true }}
    >
      <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="hsl(var(--border))" />
      <Controls className="!shadow-md [&_button]:!border-border [&_button]:!bg-card" />
      <MiniMap
        pannable
        zoomable
        maskColor="hsl(var(--background) / 0.6)"
        style={{ background: "hsl(var(--card))" }}
        nodeColor="hsl(var(--primary))"
      />
    </ReactFlow>
  );
}
