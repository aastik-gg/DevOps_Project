import { useState } from 'react';
import Modal from './Modal.jsx';

export default function ConfirmDialog({ title, message, confirmLabel = 'Confirm', danger = false, onConfirm, onClose }) {
  const [working, setWorking] = useState(false);

  async function confirm() {
    setWorking(true);
    const ok = await onConfirm();
    if (!ok) setWorking(false);
  }

  return (
    <Modal title={title} onClose={onClose} width={400}>
      <p className="confirm-msg">{message}</p>
      <footer className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className={`btn btn-primary ${danger ? 'btn-danger-solid' : ''}`} disabled={working} onClick={confirm}>
          {working ? 'Working…' : confirmLabel}
        </button>
      </footer>
    </Modal>
  );
}
