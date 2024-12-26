import React, { useEffect, useState } from 'react';
import DashboardGridItem from './DashboardGridItem';
import SortDropdown from './SortDropdown';
import { Document } from '../types/DocumentTypes';
import '../styles/DocumentGrid.css';

interface DocumentGridProps {
  documents: Document[];
  groups: { groupName: string; documents: Document[] }[];
  currentPage: number;
  totalPages: number;
  onNextPage: () => void;
  onPreviousPage: () => void;
  onDocumentClick: (doc: Document) => void;
  onDeleteDocument: (doc: Document) => void;
  onDownloadDocument: (event: React.MouseEvent<HTMLButtonElement>, doc: Document) => void;
  sortField: string;
  sortOrder: 'asc' | 'desc';
  setSortField: (field: string) => void;
  setSortOrder: (order: 'asc' | 'desc') => void;
  loading: boolean;
  isDarkMode?: boolean;
}

const DocumentGrid: React.FC<DocumentGridProps> = ({
  documents,
  groups = [],
  currentPage,
  totalPages,
  onNextPage,
  onPreviousPage,
  onDocumentClick,
  onDeleteDocument,
  onDownloadDocument,
  sortField,
  sortOrder,
  setSortField,
  setSortOrder,
  loading,
  isDarkMode = false,
}) => {
  useEffect(() => {
    console.log('DocumentGrid received props:', {
      documents,
      groups,
      currentPage,
      totalPages,
      sortField,
      sortOrder,
    });
  }, [documents, groups, currentPage, totalPages, sortField, sortOrder]);

  if (loading) {
    return <div className="loading-message">Loading documents...</div>;
  }

  // Render ungrouped documents (for 'title' sorting)
  const renderUngroupedDocuments = () => {
    if (documents.length === 0) {
      return <div>No documents found.</div>;
    }

    const rows: JSX.Element[] = [];
    let docsPerRow = 3;

    if (window.innerWidth <= 540) {
      docsPerRow = 1;
    } else if (window.innerWidth <= 1300) {
      docsPerRow = 2;
    }

    const fullRows = Math.floor(documents.length / docsPerRow);
    const remainingDocs = documents.length % docsPerRow;

    for (let i = 0; i < fullRows * docsPerRow; i += docsPerRow) {
      const rowDocs = documents.slice(i, i + docsPerRow);
      const row = (
        <div key={`row-${i}`} className="ungrouped-document-row">
          {rowDocs.map((doc, index) => (
            <div key={`doc-${doc.id}-${index}`} className="ungrouped-document-cell">
              <DashboardGridItem
                doc={doc}
                onDocumentClick={onDocumentClick}
                onDelete={() => onDeleteDocument(doc)}
                onDownload={(e) => onDownloadDocument(e, doc)}
                isDarkMode={isDarkMode}
              />
            </div>
          ))}
        </div>
      );
      rows.push(row);
    }

    if (remainingDocs > 0) {
      const lastRowDocs = documents.slice(fullRows * docsPerRow);
      const lastRow = (
        <div key="row-last" className="ungrouped-document-row">
          {lastRowDocs.map((doc, index) => (
            <div key={`doc-${doc.id}-${index}`} className="ungrouped-document-cell">
              <DashboardGridItem
                doc={doc}
                onDocumentClick={onDocumentClick}
                onDelete={() => onDeleteDocument(doc)}
                onDownload={(e) => onDownloadDocument(e, doc)}
                isDarkMode={isDarkMode}
              />
            </div>
          ))}
        </div>
      );
      rows.push(lastRow);
    }

    return <div className="ungrouped-grid">{rows}</div>;
  };

  const [, setForceUpdate] = useState({});

  useEffect(() => {
    const handleResize = () => {
      setForceUpdate({});
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Render grouped documents (for other sorts like 'filter_dimensions.name')
  const renderGroupedDocuments = () => {
    if (groups.length === 0) {
      return <div>No grouped documents found.</div>;
    }

    return (
      <div className="grouped-documents-container">
        {groups.map((group, index) => (
          <div key={`group-${group.groupName}-${index}`} className="grouped-document-section">
            <h3 className="grouped-document-title">{group.groupName}</h3>
            <div className="grouped-document-scroll-container">
              <div className="grouped-document-row">
                {group.documents.map((doc, docIndex) => (
                  <div key={`doc-${doc.id}-${docIndex}`} className="grouped-document-item">
                    <DashboardGridItem
                      doc={doc}
                      onDocumentClick={onDocumentClick}
                      onDelete={() => onDeleteDocument(doc)}
                      onDownload={(e) => onDownloadDocument(e, doc)}
                      isDarkMode={isDarkMode}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="document-grid-container">
      <div className="sort-dropdown-container">
        <SortDropdown
          sortField={sortField}
          sortOrder={sortOrder}
          onSortChange={(field, order) => {
            setSortField(field);
            setSortOrder(order);
          }}
        />
      </div>

      {sortField === 'title' ? renderUngroupedDocuments() : renderGroupedDocuments()}

      <div className="pagination">
        <button
          onClick={onPreviousPage}
          disabled={currentPage === 1}
          className="pageButton"
        >
          Previous
        </button>
        <span>{`Page ${currentPage} of ${totalPages}`}</span>
        <button
          onClick={onNextPage}
          disabled={currentPage === totalPages}
          className="pageButton"
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default DocumentGrid;
