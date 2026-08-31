"use client";

import { useId, useMemo, useState, type KeyboardEvent } from "react";

type ProjectOptionPickerProps = {
  label: string;
  hint?: string;
  selected: string[];
  options: string[];
  onChange: (values: string[]) => void;
  onCreateOption?: (label: string) => Promise<string | void>;
  canCreate?: boolean;
  multiple?: boolean;
  disabled?: boolean;
  placeholder?: string;
};

export function ProjectOptionPicker({
  label,
  hint,
  selected,
  options,
  onChange,
  onCreateOption,
  canCreate = false,
  multiple = false,
  disabled = false,
  placeholder = "Search or choose an option",
}: ProjectOptionPickerProps) {
  const listboxId = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedKeys = useMemo(() => new Set(selected.map((value) => value.toLocaleLowerCase())), [selected]);
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const filteredOptions = options
    .filter((option) => option.toLocaleLowerCase().includes(normalizedQuery))
    .filter((option) => multiple || !selectedKeys.has(option.toLocaleLowerCase()));
  const exactMatch = options.some((option) => option.toLocaleLowerCase() === normalizedQuery);
  const showCreate = canCreate && Boolean(normalizedQuery) && !exactMatch;

  function choose(value: string) {
    if (multiple) {
      const alreadySelected = selectedKeys.has(value.toLocaleLowerCase());
      onChange(
        alreadySelected
          ? selected.filter((item) => item.toLocaleLowerCase() !== value.toLocaleLowerCase())
          : [...selected, value],
      );
      setQuery("");
      setOpen(true);
      return;
    }
    onChange([value]);
    setQuery("");
    setOpen(false);
  }

  async function addOption() {
    const value = query.trim().replace(/\s+/g, " ");
    if (!value || !onCreateOption) return;
    setCreating(true);
    setError(null);
    try {
      const createdLabel = (await onCreateOption(value)) || value;
      choose(createdLabel);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to add option.");
    } finally {
      setCreating(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setOpen(false);
      setQuery("");
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      if (showCreate) {
        void addOption();
      } else if (filteredOptions[0]) {
        choose(filteredOptions[0]);
      }
    }
    if (event.key === "Backspace" && !query && multiple && selected.length > 0) {
      onChange(selected.slice(0, -1));
    }
  }

  return (
    <div className="form-field project-option-picker">
      <span>{label}{hint ? <small>{hint}</small> : null}</span>
      <div
        className={`project-option-picker-control${disabled ? " disabled" : ""}`}
        onBlur={() => window.setTimeout(() => setOpen(false), 140)}
        onClick={() => { if (!disabled) setOpen(true); }}
      >
        {selected.map((value) => (
          <span className="project-option-chip" key={value}>
            {value}
            {!disabled ? (
              <button
                aria-label={`Remove ${value}`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(value)}
                type="button"
              >×</button>
            ) : null}
          </span>
        ))}
        <input
          aria-controls={listboxId}
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-label={label}
          disabled={disabled}
          onChange={(event) => { setQuery(event.target.value); setOpen(true); setError(null); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={selected.length ? "Add another…" : placeholder}
          value={query}
        />
      </div>
      {open && !disabled ? (
        <div className="project-option-picker-menu" id={listboxId} role="listbox">
          {filteredOptions.map((option) => {
            const isSelected = selectedKeys.has(option.toLocaleLowerCase());
            return (
              <button
                aria-selected={isSelected}
                className={`project-option-picker-option${isSelected ? " selected" : ""}`}
                key={option}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(option)}
                role="option"
                type="button"
              >
                <span>{option}</span>
                {isSelected ? <span>✓</span> : null}
              </button>
            );
          })}
          {showCreate ? (
            <button
              className="project-option-picker-create"
              disabled={creating}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => void addOption()}
              type="button"
            >
              {creating ? "Adding…" : `＋ Add “${query.trim()}” to workspace`}
            </button>
          ) : null}
          {!filteredOptions.length && !showCreate ? (
            <div className="project-option-picker-empty">No matching workspace options.</div>
          ) : null}
        </div>
      ) : null}
      {error ? <small className="project-option-picker-error" role="alert">{error}</small> : null}
    </div>
  );
}

