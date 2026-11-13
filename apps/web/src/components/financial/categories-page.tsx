"use client";
import { useEffect, useState } from "react";
import { Plus, Pencil, Archive, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Modal } from "@/components/ui/modal";
import { api, Category, EntryType, listCategories } from "@/lib/api/financial";
export function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]),
    [version, setVersion] = useState(0);
  const [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [editing, setEditing] = useState<{
    category?: Category;
    type: EntryType;
  } | null>(null);
  const [archive, setArchive] = useState<Category | null>(null),
    [busy, setBusy] = useState(false),
    [archiveError, setArchiveError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    listCategories(undefined, controller.signal).then(
      (cats) => {
        setCategories(cats);
        setLoading(false);
        setError("");
      },
      (error) => {
        if (!controller.signal.aborted) {
          setError(error.message);
          setLoading(false);
        }
      },
    );
    return () => controller.abort();
  }, [version]);
  function refresh(message = "") {
    setNotice(message);
    setLoading(true);
    setVersion((v) => v + 1);
  }
  async function toggleArchive() {
    if (!archive || busy) return;
    setBusy(true);
    try {
      await api<Category>("categories/" + archive.id, {
        method: "PATCH",
        body: JSON.stringify({ active: !archive.active }),
      });
      setArchive(null);
      refresh("Category updated. Historical entries are preserved.");
    } catch (error) {
      setArchiveError(error instanceof Error ? error.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="eyebrow">YOUR WORKSPACE</div>
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Keep your income and expense categories useful and organized.</p>
        </div>
      </header>
      <div className="section-heading">
        <div>
          <h2>Financial categories</h2>
          <p>
            Archive a category to stop new assignments without changing
            historical entries.
          </p>
        </div>
      </div>
      {notice && (
        <p role="status" className="save-notice">
          {notice}
        </p>
      )}
      {error ? (
        <div role="alert" className="table-message">
          <p>{error}</p>
          <Button variant="outline" onClick={() => refresh()}>
            Retry
          </Button>
        </div>
      ) : loading ? (
        <p role="status">Loading categories…</p>
      ) : (
        <div className="category-groups">
          {(["income", "expense"] as const).map((type) => (
            <section key={type}>
              <div className="section-heading">
                <h2>
                  {type === "income"
                    ? "Income categories"
                    : "Expense categories"}
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditing({ type })}
                >
                  <Plus size={14} />
                  Add {type} category
                </Button>
              </div>
              {categories
                .filter((c) => c.type === type)
                .map((category) => (
                  <div className="category-row" key={category.id}>
                    <span className="category-label">
                      {category.color && (
                        <i style={{ backgroundColor: category.color }} />
                      )}
                      <strong>{category.name}</strong>
                    </span>
                    <span className="quiet-tag">
                      {category.active ? "Active" : "Archived"}
                    </span>
                    <button
                      className="icon-button"
                      aria-label={"Rename " + category.name}
                      onClick={() => setEditing({ category, type })}
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      className="icon-button"
                      aria-label={
                        (category.active ? "Archive " : "Restore ") +
                        category.name
                      }
                      onClick={() => {
                        setArchiveError("");
                        setArchive(category);
                      }}
                    >
                      {category.active ? (
                        <Archive size={16} />
                      ) : (
                        <RotateCcw size={16} />
                      )}
                    </button>
                  </div>
                ))}
            </section>
          ))}
        </div>
      )}
      <p className="financial-footnote">
        Belgium and EUR are entry defaults. Company preferences, deductibility
        settings and Sentinel sign-in remain future features.
      </p>
      {editing && (
        <CategoryForm
          key={editing.category?.id ?? editing.type}
          {...editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh("Category saved.");
          }}
        />
      )}
      {archive && (
        <ConfirmDialog
          title={
            (archive.active ? "Archive " : "Restore ") + archive.name + "?"
          }
          description={
            archive.active
              ? "Historical entries keep their category. This category will no longer be available for new assignments."
              : "This category will become available for new entries again."
          }
          confirmLabel={
            archive.active ? "Archive category" : "Restore category"
          }
          error={archiveError}
          busy={busy}
          onCancel={() => setArchive(null)}
          onConfirm={() => void toggleArchive()}
        />
      )}
    </>
  );
}
function CategoryForm({
  category,
  type,
  onClose,
  onSaved,
}: {
  category?: Category;
  type: EntryType;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(category?.name ?? ""),
    [color, setColor] = useState(category?.color ?? "");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [discard, setDiscard] = useState(false);
  const dirty =
    name !== (category?.name ?? "") || color !== (category?.color ?? "");
  function close() {
    if (busy) return;
    if (dirty) setDiscard(true);
    else onClose();
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!name.trim()) {
      setError("Enter a category name.");
      return;
    }
    if (color && !/^#[0-9a-fA-F]{6}$/.test(color)) {
      setError("Use a hex color such as #7250c9, or leave it empty.");
      return;
    }
    setBusy(true);
    try {
      await api<Category>("categories" + (category ? "/" + category.id : ""), {
        method: category ? "PATCH" : "POST",
        body: JSON.stringify({
          name: name.trim(),
          color: color || null,
          ...(!category ? { type } : {}),
        }),
      });
      onSaved();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Modal
        title={category ? "Rename category" : "New " + type + " category"}
        description="Names are unique within income or expenses. Historical entry references are retained."
        onClose={close}
        busy={busy}
      >
        <form onSubmit={save} noValidate className="modal-form">
          <div className="modal-body form-grid">
            {error && (
              <p role="alert" className="form-error full-width">
                {error}
              </p>
            )}
            <label className="form-field full-width">
              Category name *
              <input
                value={name}
                maxLength={100}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label className="form-field full-width">
              Color (optional)
              <input
                placeholder="#7250c9"
                value={color}
                maxLength={7}
                onChange={(e) => setColor(e.target.value)}
              />
            </label>
          </div>
          <footer className="modal-footer">
            <Button
              variant="outline"
              type="button"
              onClick={close}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save category"}
            </Button>
          </footer>
        </form>
      </Modal>
      {discard && (
        <ConfirmDialog
          title="Discard category changes?"
          description="The changes have not been saved."
          confirmLabel="Discard changes"
          onCancel={() => setDiscard(false)}
          onConfirm={onClose}
        />
      )}
    </>
  );
}
