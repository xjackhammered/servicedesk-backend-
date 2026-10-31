export default function Pagination({ page, totalPages, onPage }) {
  if (totalPages <= 1) return null;
  return (
    <div className="pagination">
      <button className="btn" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Previous</button>
      <span>Page {page} of {totalPages}</span>
      <button className="btn" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>Next →</button>
    </div>
  );
}
