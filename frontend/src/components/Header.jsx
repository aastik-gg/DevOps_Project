export default function Header({ onAdd }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="9" />
            <circle cx="16" cy="16" r="8" />
            <circle cx="16" cy="16" r="2.5" />
          </svg>
          <div>
            <span className="brand-name">GearLoop</span>
            <span className="brand-tag">Lab equipment desk · Campus Makerspace</span>
          </div>
        </div>
        <button type="button" className="btn btn-primary" onClick={onAdd}>
          <span aria-hidden="true">+</span> Add equipment
        </button>
      </div>
    </header>
  );
}
