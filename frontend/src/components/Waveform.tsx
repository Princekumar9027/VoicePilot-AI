export default function Waveform({ active }: { active: boolean }) {
  return (
    <div className={`wave ${active ? "wave-active" : ""}`} aria-hidden="true">
      {Array.from({ length: 24 }).map((_, index) => (
        <span key={index} style={{ animationDelay: `${(index % 8) * 0.09}s` }} />
      ))}
    </div>
  );
}
