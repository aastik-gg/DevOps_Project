import { useState } from 'react';
import Modal from './Modal.jsx';
import { CONDITION_LABELS } from '../lib/format.js';

const CATEGORIES = ['Electronics', 'Tools', 'Cameras', 'Computing', 'Audio', 'Measurement'];

export default function ItemDialog({ item, onSave, onClose }) {
  const editing = Boolean(item);
  const [form, setForm] = useState({
    name: item?.name ?? '',
    category: item?.category ?? '',
    asset_tag: item?.asset_tag ?? '',
    location: item?.location ?? 'Main lab',
    condition: item?.condition ?? 'GOOD',
    notes: item?.notes ?? '',
  });
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    const payload = { ...form, category: form.category.trim() || 'General', name: form.name.trim() };
    if (editing) delete payload.asset_tag; // asset tags are immutable once issued
    const ok = await onSave(payload);
    if (!ok) setSaving(false);
  }

  return (
    <Modal title={editing ? `Edit ${item.name}` : 'Add equipment'} subtitle={editing ? item.asset_tag : 'Register a new item on the desk'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label className="field">
          <span>Name</span>
          <input required maxLength={120} value={form.name} onChange={set('name')} placeholder="Rigol DS1054Z oscilloscope" />
        </label>
        <div className="field-row">
          <label className="field">
            <span>Category</span>
            <input list="gl-categories" maxLength={60} value={form.category} onChange={set('category')} placeholder="Electronics" />
            <datalist id="gl-categories">
              {CATEGORIES.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </label>
          <label className="field">
            <span>Asset tag</span>
            <input
              required={!editing}
              disabled={editing}
              maxLength={40}
              pattern="[A-Za-z0-9\-]+"
              title="Letters, numbers and dashes"
              className="mono"
              value={form.asset_tag}
              onChange={set('asset_tag')}
              placeholder="LAB-0042"
            />
          </label>
        </div>
        <div className="field-row">
          <label className="field">
            <span>Location</span>
            <input maxLength={120} value={form.location} onChange={set('location')} placeholder="Shelf B2" />
          </label>
          <label className="field">
            <span>Condition</span>
            <select value={form.condition} onChange={set('condition')}>
              {Object.entries(CONDITION_LABELS).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="field">
          <span>Notes</span>
          <textarea rows={3} value={form.notes} onChange={set('notes')} placeholder="Accessories, quirks, calibration date…" />
        </label>
        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : editing ? 'Save changes' : 'Add to inventory'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
