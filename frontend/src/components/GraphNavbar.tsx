import type { GraphNodeMeta, NodeStatus } from "../types";

interface Props { nodes: GraphNodeMeta[]; status: Record<string, NodeStatus> }

export default function GraphNavbar({ nodes, status }: Props) {
  const stages = [...new Set(nodes.map((n) => n.stage))].sort((a, b) => a - b);
  return (
    <nav className="graphbar" aria-label="Nodi LangGraph in esecuzione">
      <span className="graphbar-title">LangGraph</span>
      <ol className="stages">
        {stages.map((stage) => (
          <li key={stage} className="stage">
            {nodes.filter((n) => n.stage === stage).map((n) => {
              const st = status[n.id] ?? { state: "idle" };
              return (
                <div key={n.id} className={`node node-${st.state}`}
                  title={`${n.description}${st.summary ? ` — ${st.summary}` : ""}`}>
                  <span className="node-dot" aria-hidden />
                  <span className="node-label">{n.label}</span>
                  {st.state === "done" && st.ms !== undefined ? <span className="node-ms">{st.ms} ms</span> : null}
                  {st.summary && st.state !== "idle" ? <span className="node-sum">{st.summary}</span> : null}
                </div>
              );
            })}
          </li>
        ))}
      </ol>
    </nav>
  );
}
