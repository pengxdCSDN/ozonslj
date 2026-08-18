import { useEffect, useState } from "react";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  itemLabel: string;
  disabled?: boolean;
  onPageChange: (page: number) => void;
}

/**
 * 统一的列表分页控件：案例确认和评测运行历史共享同一套跳页行为，
 * 避免各页面自行实现时出现页码边界、回车提交和移动端布局不一致。
 */
export function Pagination({
  page,
  totalPages,
  total,
  itemLabel,
  disabled = false,
  onPageChange,
}: PaginationProps) {
  const [jumpPage, setJumpPage] = useState("");
  const safeTotalPages = Math.max(1, totalPages);

  useEffect(() => {
    setJumpPage("");
  }, [page, safeTotalPages]);

  const goToPage = () => {
    const requestedPage = Number(jumpPage);
    if (!Number.isInteger(requestedPage)) return;
    onPageChange(Math.min(safeTotalPages, Math.max(1, requestedPage)));
  };

  return (
    <nav className="sync-actions rag-pagination" aria-label={`${itemLabel}分页`}>
      <span>共 {total} 个{itemLabel} · 第 {page} / {safeTotalPages} 页</span>
      <div className="rag-page-controls">
        <button
          type="button"
          className="secondary-button"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={disabled || page <= 1}
        >
          上一页
        </button>
        <button
          type="button"
          className="secondary-button"
          onClick={() => onPageChange(Math.min(safeTotalPages, page + 1))}
          disabled={disabled || page >= safeTotalPages}
        >
          下一页
        </button>
        <label className="rag-page-jump">
          <span>跳至</span>
          <input
            type="number"
            min="1"
            max={safeTotalPages}
            value={jumpPage}
            onChange={(event) => setJumpPage(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") goToPage(); }}
            placeholder={String(page)}
            aria-label={`输入${itemLabel}页码`}
          />
          <span>页</span>
          <button
            type="button"
            className="secondary-button"
            onClick={goToPage}
            disabled={disabled || !jumpPage}
          >
            确定
          </button>
        </label>
      </div>
    </nav>
  );
}
