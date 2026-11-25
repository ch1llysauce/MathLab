import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { Compartment, EditorState } from "@codemirror/state";
import { EditorView, keymap, placeholder as cmPlaceholder } from "@codemirror/view";

export interface CodeMirrorEditorHandle {
  insertText: (text: string, cursorBack?: number) => void;
  backspace: () => void;
  clear: () => void;
}

interface CodeMirrorCellEditorProps {
  value: string;
  onChange: (nextValue: string) => void;
  onRunCell?: () => void;
  placeholder?: string;
}

const workbenchTheme = EditorView.theme({
  "&": {
    backgroundColor: "var(--bg-subtle)",
    color: "var(--text-primary)",
    fontSize: "13.5px",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    borderRadius: "4px",
    border: "1px solid var(--border-hairline)",
  },
  "&.cm-focused": {
    outline: "none",
    borderColor: "var(--border-strong)",
    backgroundColor: "var(--bg-surface)",
  },
  ".cm-content": {
    padding: "8px 10px",
    minHeight: "36px",
  },
  ".cm-line": {
    padding: "0",
  },
  ".cm-cursor": {
    borderLeftColor: "var(--text-primary)",
  },
  ".cm-selectionBackground, ::selection": {
    backgroundColor: "var(--selection-bg) !important",
  },
  ".cm-placeholder": {
    color: "var(--text-muted)",
  },
});

export const CodeMirrorCellEditor = forwardRef<
  CodeMirrorEditorHandle,
  CodeMirrorCellEditorProps
>(function CodeMirrorCellEditor(
  {
    value,
    onChange,
    onRunCell,
    placeholder = "Enter mathematical expression...",
  },
  ref
) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);
  const placeholderConfRef = useRef(new Compartment());
  const onChangeRef = useRef(onChange);
  const onRunRef = useRef(onRunCell);

  onChangeRef.current = onChange;
  onRunRef.current = onRunCell;

  useImperativeHandle(ref, () => ({
    insertText(text: string, cursorBack = 0) {
      const view = viewRef.current;
      if (!view) return;
      const { from, to } = view.state.selection.main;
      const nextAnchor = Math.max(0, from + text.length - cursorBack);
      view.dispatch({
        changes: { from, to, insert: text },
        selection: { anchor: nextAnchor },
      });
      view.focus();
    },
    backspace() {
      const view = viewRef.current;
      if (!view) return;
      const { from, to } = view.state.selection.main;
      if (from === 0 && to === 0) {
        view.focus();
        return;
      }
      const delFrom = from !== to ? from : Math.max(0, from - 1);
      view.dispatch({
        changes: { from: delFrom, to, insert: "" },
        selection: { anchor: delFrom },
      });
      view.focus();
    },
    clear() {
      const view = viewRef.current;
      if (!view) return;
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: "" },
        selection: { anchor: 0 },
      });
      view.focus();
    },
  }));

  useEffect(() => {
    if (!hostRef.current) return;

    const runShortcut = keymap.of([
      {
        key: "Shift-Enter",
        run: () => {
          onRunRef.current?.();
          return true;
        },
      },
    ]);

    const state = EditorState.create({
      doc: value,
      extensions: [
        runShortcut,
        history(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        placeholderConfRef.current.of(cmPlaceholder(placeholder)),
        workbenchTheme,
        EditorView.lineWrapping,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChangeRef.current(update.state.doc.toString());
          }
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: hostRef.current,
    });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: placeholderConfRef.current.reconfigure(cmPlaceholder(placeholder)),
    });
  }, [placeholder]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== value) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      });
    }
  }, [value]);

  return <div ref={hostRef} className="w-full" />;
});
