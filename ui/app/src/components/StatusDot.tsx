export function StatusDot({ color, label }: { color: 'green' | 'amber' | 'red' | 'purple'; label: string }) {
  const colorMap = {
    green: '#15803D',
    amber: '#B45309',
    red: '#B91C1C',
    purple: '#7C3AED',
  }

  return (
    <div className="flex items-center gap-2">
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '2px',
          backgroundColor: colorMap[color],
          flexShrink: 0,
        }}
      />
      <span className="font-sans text-sm font-medium" style={{ color: colorMap[color] }}>
        {label}
      </span>
    </div>
  )
}
