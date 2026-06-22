export function AvatarRing({ active }: { active: boolean }) {
  return (
    <svg className={active ? "audio-ring-svg active" : "audio-ring-svg"} width="210" height="210" viewBox="0 0 210 210">
      {Array.from({ length: 130 }, (_, index) => {
        const angle = (360 / 130) * index;
        const wave = active ? Math.sin(index * 0.42) * 4 + Math.sin(index * 0.17) * 2 : 0;
        const height = Math.max(1.78, 2.2 + wave);
        return (
          <rect
            key={index}
            fill={active ? "#6B5CFF" : "#CACACA"}
            width="2"
            rx="1"
            ry="1"
            height={height}
            transform={`rotate(${angle}, 105, 105) translate(105, 190)`}
          />
        );
      })}
    </svg>
  );
}

