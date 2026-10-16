import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api.js';
import Header from './components/Header.jsx';
import SummaryStrip from './components/SummaryStrip.jsx';
import Toolbar from './components/Toolbar.jsx';
import ItemCard from './components/ItemCard.jsx';
import ActivityPanel from './components/ActivityPanel.jsx';
import ItemDialog from './components/ItemDialog.jsx';
import CheckoutDialog from './components/CheckoutDialog.jsx';
import ConfirmDialog from './components/ConfirmDialog.jsx';
import Toasts from './components/Toasts.jsx';

let toastSeq = 0;

export default function App() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loans, setLoans] = useState([]);
  const [loansError, setLoansError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [dialog, setDialog] = useState(null); // {type: 'add'|'edit'|'checkout'|'delete'|'return', item}
  const [toasts, setToasts] = useState([]);
  const queryRef = useRef(query);
  queryRef.current = query;

  const toast = useCallback((message, kind = 'info') => {
    const id = ++toastSeq;
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 6000 : 3500);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [itemList, statData] = await Promise.all([api.items({ q: queryRef.current.trim() }), api.stats()]);
      setItems(itemList);
      setStats(statData);
      setLoadError(null);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
    try {
      setLoans(await api.loans({ limit: 12 }));
      setLoansError(false);
    } catch {
      setLoansError(true);
    }
  }, []);

  // Debounced search; also does the initial load.
  useEffect(() => {
    const t = setTimeout(refresh, query ? 250 : 0);
    return () => clearTimeout(t);
  }, [query, refresh]);

  const counts = useMemo(() => {
    const c = { ALL: items.length };
    items.forEach((i) => {
      c[i.status] = (c[i.status] ?? 0) + 1;
    });
    return c;
  }, [items]);

  const visible = status ? items.filter((i) => i.status === status) : items;

  // Runs an API mutation, reports the outcome, refreshes data. Returns true on success
  // so dialogs know whether to stay open.
  async function mutate(fn, successMessage, itemId) {
    setBusyId(itemId ?? null);
    try {
      await fn();
      toast(successMessage, 'success');
      setDialog(null);
      await refresh();
      return true;
    } catch (err) {
      toast(err.message, 'error');
      return false;
    } finally {
      setBusyId(null);
    }
  }

  const close = useCallback(() => setDialog(null), []);

  return (
    <>
      <Header onAdd={() => setDialog({ type: 'add' })} />
      <main className="page">
        <SummaryStrip stats={stats} />
        <div className="layout">
          <section className="inventory" aria-label="Equipment">
            <Toolbar status={status} onStatus={setStatus} query={query} onQuery={setQuery} counts={loading || loadError ? null : counts} />

            {loading && (
              <div className="grid" aria-busy="true">
                {Array.from({ length: 6 }, (_, i) => (
                  <div key={i} className="card skeleton" />
                ))}
              </div>
            )}

            {!loading && loadError && (
              <div className="state state-error">
                <h3>Can’t reach the equipment desk</h3>
                <p className="muted">{loadError}. Check that the backend and database are running.</p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    setLoading(true);
                    refresh();
                  }}
                >
                  Retry
                </button>
              </div>
            )}

            {!loading && !loadError && visible.length === 0 && (
              <div className="state">
                {items.length === 0 && !query ? (
                  <>
                    <h3>The shelves are empty</h3>
                    <p className="muted">Add your first piece of equipment to start lending it out.</p>
                    <button type="button" className="btn btn-primary" onClick={() => setDialog({ type: 'add' })}>
                      Add equipment
                    </button>
                  </>
                ) : (
                  <>
                    <h3>Nothing matches</h3>
                    <p className="muted">Try another status filter or search term.</p>
                  </>
                )}
              </div>
            )}

            {!loading && !loadError && visible.length > 0 && (
              <div className="grid">
                {visible.map((item) => (
                  <ItemCard
                    key={item.id}
                    item={item}
                    busy={busyId === item.id}
                    onCheckOut={(it) => setDialog({ type: 'checkout', item: it })}
                    onReturn={(it) => setDialog({ type: 'return', item: it })}
                    onEdit={(it) => setDialog({ type: 'edit', item: it })}
                    onDelete={(it) => setDialog({ type: 'delete', item: it })}
                  />
                ))}
              </div>
            )}
          </section>
          <ActivityPanel loans={loans} error={loansError} />
        </div>
      </main>

      {dialog?.type === 'add' && (
        <ItemDialog onClose={close} onSave={(data) => mutate(() => api.createItem(data), `${data.name} added`)} />
      )}
      {dialog?.type === 'edit' && (
        <ItemDialog
          item={dialog.item}
          onClose={close}
          onSave={(data) => mutate(() => api.updateItem(dialog.item.id, data), 'Changes saved', dialog.item.id)}
        />
      )}
      {dialog?.type === 'checkout' && (
        <CheckoutDialog
          item={dialog.item}
          onClose={close}
          onSave={(loan) => mutate(() => api.checkOut(loan), `${dialog.item.name} checked out to ${loan.borrower}`, dialog.item.id)}
        />
      )}
      {dialog?.type === 'return' && (
        <ConfirmDialog
          title="Mark as returned?"
          message={`${dialog.item.name} will go back on the shelf and ${dialog.item.active_loan.borrower}'s loan will be closed.`}
          confirmLabel="Mark returned"
          onClose={close}
          onConfirm={() => mutate(() => api.returnLoan(dialog.item.active_loan.id), `${dialog.item.name} returned`, dialog.item.id)}
        />
      )}
      {dialog?.type === 'delete' && (
        <ConfirmDialog
          title="Delete this item?"
          message={`${dialog.item.name} (${dialog.item.asset_tag}) and its loan history will be removed permanently.`}
          confirmLabel="Delete"
          danger
          onClose={close}
          onConfirm={() => mutate(() => api.deleteItem(dialog.item.id), `${dialog.item.name} deleted`, dialog.item.id)}
        />
      )}
      <Toasts toasts={toasts} onDismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />
    </>
  );
}
