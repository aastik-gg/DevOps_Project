import { useState } from 'react';
import Modal from './Modal.jsx';
import { formatDate } from '../lib/format.js';

export default function CheckoutDialog({ item, onSave, onClose }) {
  const [borrower, setBorrower] = useState('');
  const [purpose, setPurpose] = useState('');
  const [days, setDays] = useState(7);
  const [saving, setSaving] = useState(false);
  const due = new Date(Date.now() + Number(days || 0) * 86400000);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    const ok = await onSave({ item_id: item.id, borrower: borrower.trim(), purpose: purpose.trim(), days: Number(days) });
    if (!ok) setSaving(false);
  }

  return (
    <Modal title="Check out" subtitle={`${item.name} · ${item.asset_tag}`} onClose={onClose} width={420}>
      <form className="form" onSubmit={submit}>
        <label className="field">
          <span>Borrower</span>
          <input required maxLength={120} value={borrower} onChange={(e) => setBorrower(e.target.value)} placeholder="Name or roll number" />
        </label>
        <label className="field">
          <span>Purpose</span>
          <input maxLength={200} value={purpose} onChange={(e) => setPurpose(e.target.value)} placeholder="Robotics club demo" />
        </label>
        <label className="field">
          <span>Loan length</span>
          <div className="days">
            <input type="range" min={1} max={30} value={days} onChange={(e) => setDays(e.target.value)} aria-label="Days" />
            <input type="number" min={1} max={30} required value={days} onChange={(e) => setDays(e.target.value)} className="days-num" />
            <span className="muted small">days</span>
          </div>
          <span className="muted small">Due back {formatDate(due)}</span>
        </label>
        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Checking out…' : 'Confirm checkout'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
