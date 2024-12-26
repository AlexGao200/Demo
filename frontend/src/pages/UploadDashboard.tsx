import React, { useState, useCallback, useContext, useEffect } from 'react';
import '../styles/UploadDashboard.css';
import { UserContext } from '../context/UserContext';
import { UserContextType, ThemeContextType } from '../types';
import { ThemeContext } from '../context/ThemeContext';
import useDocumentDeletion from '../hooks/useDocumentDeletion';
import SearchModal from '../components/SearchModal';
import MiniPDFViewer from '../components/MiniPDFViewer';
import AppHeader from '../components/AppHeader';
import Modal from '../components/Modal';
import PDFModal from '../components/PDFModal';
import logoImage from '../assets/images/logo3.png';
import { Document } from '../types/DocumentTypes';
import { useFetchDocuments } from '../hooks/useFetchDocuments';
import DocumentGrid from '../components/DocumentGrid';
import UploadFilter from '../components/filters_new/UploadFilter';
import QueryFilter from '../components/filters_new/QueryFilter';
import { FilterProps } from '../types/FilterTypes';
import { UnifiedFilterProvider, useUnifiedFilter, setUploadFilters, setQueryFilters } from '../context/UnifiedFilterContext';

const UploadDashboardContent: React.FC = () => {
  const { user, loading: userLoading } = useContext(UserContext) as UserContextType;
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const { dispatch: filterDispatch } = useUnifiedFilter();

  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [isCategoryOpen, setIsCategoryOpen] = useState<boolean>(false);

  const [showSuccessPopup, setShowSuccessPopup] = useState<boolean>(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);

  const [isPDFModalOpen, setIsPDFModalOpen] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [modalMessage, setModalMessage] = useState<string>('');

  const {
    documents,
    groups,
    loading,
    page: currentPage,
    totalPages,
    fetchDocuments,
    loadNextPage,
    loadPreviousPage,
    setSortField,
    setSortOrder,
    sortField,
    sortOrder,
  } = useFetchDocuments();

  const { handleDeleteDocument } = useDocumentDeletion(fetchDocuments);

  const checkSubscriptionStatus = useCallback((): boolean => {
    if (user?.subscription_status === 'inactive' && !user?.is_admin) {
      setModalMessage('Please renew your subscription to access this feature.');
      setIsModalOpen(true);
      return false;
    }
    return true;
  }, [user?.subscription_status, user?.is_admin]);

  const handleUploadComplete = (data: FilterProps) => {
    setIsUploadOpen(false);
    if (data.uploadResult?.success) {
      setShowSuccessPopup(true);
      setUploadFilters(filterDispatch, data);
      setTimeout(() => {
        fetchDocuments();
      }, 1000);
    }
  };

  const handleUploadAbort = () => {
    setIsUploadOpen(false);
  };

  const handleUploadClick = () => {
    setIsUploadOpen(true);
  };

  const handleSearchClick = (): void => {
    if (!checkSubscriptionStatus()) return;
    setIsSearchOpen(true);
  };

  const handleCategoryClick = (): void => {
    if (!checkSubscriptionStatus()) return;
    setIsCategoryOpen(true);
  };

  const handleFiltersApplied = (newFilters: FilterProps) => {
    setQueryFilters(filterDispatch, newFilters);
    setIsCategoryOpen(false);
    fetchDocuments();
  };

  const handleCategoryAbort = () => {
    setIsCategoryOpen(false);
  };

  const handleDocumentClick = (doc: Document) => {
    if (!checkSubscriptionStatus()) return;
    setSelectedDocument(doc);
    setIsPDFModalOpen(true);
  };

  const handleDownloadDocument = (event: React.MouseEvent<HTMLButtonElement>, doc: Document): void => {
    event.preventDefault();
    if (!checkSubscriptionStatus()) return;
    const link = document.createElement('a');
    link.href = doc.s3_url;
    link.download = doc.title;
    link.click();
  };

  const closeSuccessPopup = (): void => {
    setShowSuccessPopup(false);
  };

  const closePDFModal = (): void => {
    setIsPDFModalOpen(false);
    setSelectedDocument(null);
  };

  const closeModal = (): void => {
    setIsModalOpen(false);
    setModalMessage('');
  };

  useEffect(() => {
    if (selectedDocument?.s3_url) {
      console.log("Document selected with URL:", selectedDocument.s3_url);
    }
  }, [selectedDocument]);

  if (userLoading || loading) {
    return <div className="loadingIndicator">Loading...</div>;
  }

  return (
    <div className={`dashboard-container ${theme === 'dark' ? 'dark-mode' : ''}`}>
      <AppHeader />
      <div className="top-buttons">
        <button onClick={handleUploadClick}>Upload</button>
        <button onClick={handleSearchClick}>Search</button>
        <button onClick={handleCategoryClick}>Category</button>
      </div>

      {isUploadOpen && (
        <UploadFilter onComplete={handleUploadComplete} onAbort={handleUploadAbort} />
      )}

      {isSearchOpen && (
        <SearchModal
          onClose={() => setIsSearchOpen(false)}
          onSearch={() => {
            fetchDocuments();
          }}
        />
      )}

      {isCategoryOpen && (
        <QueryFilter
          onComplete={handleFiltersApplied}
          onAbort={handleCategoryAbort}
        />
      )}

      <div className="mainContent">
        <img src={logoImage} alt="Logo" className="logoImage" />
        {user && (
          <h2>{`${user.first_name} ${user.last_name}'s Library`}</h2>
        )}

        <DocumentGrid
          documents={documents}
          groups={groups}
          currentPage={currentPage}
          totalPages={totalPages}
          onNextPage={loadNextPage}
          onPreviousPage={loadPreviousPage}
          onDocumentClick={handleDocumentClick}
          onDeleteDocument={handleDeleteDocument}
          onDownloadDocument={handleDownloadDocument}
          sortField={sortField}
          sortOrder={sortOrder}
          setSortField={setSortField}
          setSortOrder={setSortOrder}
          loading={loading}
          isDarkMode={theme === 'dark'}
        />
      </div>

      {showSuccessPopup && (
        <Modal isOpen={true} onClose={closeSuccessPopup} message="Upload successful!" />
      )}

      {selectedDocument && isPDFModalOpen && (
        <PDFModal isOpen={isPDFModalOpen} onClose={closePDFModal}>
          <MiniPDFViewer documentLink={selectedDocument.s3_url} initialPage={1} />
        </PDFModal>
      )}

      {isModalOpen && <Modal isOpen={isModalOpen} onClose={closeModal} message={modalMessage} />}
    </div>
  );
};

const UploadDashboard: React.FC = () => {
  return (
    <UnifiedFilterProvider>
      <UploadDashboardContent />
    </UnifiedFilterProvider>
  );
};

export default UploadDashboard;
