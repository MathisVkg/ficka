"use client";
import * as Dialog from "@radix-ui/react-dialog";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
export function Modal({
  title,
  description,
  children,
  onClose,
  busy = false,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content
          className="modal-content"
          onInteractOutside={(event) => {
            if (busy) event.preventDefault();
          }}
          onEscapeKeyDown={(event) => {
            if (busy) event.preventDefault();
          }}
        >
          <header className="modal-header">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description>{description}</Dialog.Description>
            </div>
            <button
              className="icon-button"
              aria-label="Close dialog"
              disabled={busy}
              onClick={onClose}
            >
              <X size={20} />
            </button>
          </header>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function ConfirmDialog({
  title,
  description,
  onCancel,
  onConfirm,
  busy = false,
  error,
  confirmLabel = "Confirm",
}: {
  title: string;
  description: string;
  onCancel: () => void;
  onConfirm: () => void;
  busy?: boolean;
  error?: string;
  confirmLabel?: string;
}) {
  return (
    <AlertDialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !busy) onCancel();
      }}
    >
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="modal-overlay alert-overlay" />
        <AlertDialog.Content className="confirm-content">
          <AlertDialog.Title>{title}</AlertDialog.Title>
          <AlertDialog.Description>{description}</AlertDialog.Description>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <div className="confirm-actions">
            <AlertDialog.Cancel asChild>
              <Button variant="outline" disabled={busy}>
                Keep working
              </Button>
            </AlertDialog.Cancel>
            <Button onClick={onConfirm} disabled={busy}>
              {busy ? "Working…" : confirmLabel}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
