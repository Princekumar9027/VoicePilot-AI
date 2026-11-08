export type OrbState = "idle" | "listening" | "thinking" | "speaking" | "error";

export default function Orb({ state, size = 220 }: { state: OrbState; size?: number }) {
  return (
    <div className={`orb orb-${state}`} style={{ width: size, height: size }} role="img" aria-label={`Assistant is ${state}`}>
      <span className="orb-ring" />
      <span className="orb-ring orb-ring-two" />
      <span className="orb-core" />
    </div>
  );
}
