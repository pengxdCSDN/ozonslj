import { CaretDown, Check } from "@phosphor-icons/react";
import { useState } from "react";

export type SelectMenuOption<T extends string> = { value: T; label: string };

type SelectMenuProps<T extends string> = {
  label: string;
  value: T;
  options: readonly SelectMenuOption<T>[];
  onChange: (value: T) => void;
};

/** 项目统一业务下拉：避免原生菜单接管主题，同时保留 listbox 语义和键盘关闭。 */
export function SelectMenu<T extends string>({ label, value, options, onChange }: SelectMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.value === value);

  return (
    <div
      className="select-menu"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <span className="select-menu-label">{label}</span>
      <button
        type="button"
        className="select-menu-trigger"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
      >
        <span>{selected?.label ?? value}</span>
        <CaretDown className="select-menu-caret" size={16} aria-hidden />
      </button>
      {open ? (
        <div className="select-menu-popover" role="listbox" aria-label={label}>
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                className={isSelected ? "selected" : undefined}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
              >
                <span>{option.label}</span>
                {isSelected ? <Check size={15} weight="bold" aria-hidden /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
