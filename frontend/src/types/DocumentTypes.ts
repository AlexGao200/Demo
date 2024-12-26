import { ReactNode } from 'react';

/** Represents a document in the system */
export interface Document {
  id: string;
  s3_url: string;
  file_visibility: string;
  title: string;
  organization?: string;
  thumbnail_urls: string[];
  index_name: string;
  filter_dimensions?: { [key: string]: string[] };
}

/** Options for filtering documents */
export interface FilterOptions {
  organizations: string[]; // TODO: REMOVE
  subfields: string[]; // TODO: REMOVE
  areas: string[]; // TODO: REMOVE
  indices: string[]; // To filter by index names
  showPublicDocs: boolean;
  showPrivateDocs: boolean;
}

export interface FilterProps {
  selectedFilterDimNames: string[];
  selectedFilterDimValues: string[];
  selectedIndexNames: string[];
  onFilterComplete: (indices: string[]) => void;
  visibility: 'public' | 'private';
  onClose: () => void;
  isOpen: boolean;
}

/** Props for the UploadOptions component */
export interface UploadOptionsProps {
  onUploadComplete: (success?: boolean) => void;
  onSelectUpload: (uploadType: string) => void;
}

/** Props for upload components (Personal, Organizational, Public) */
export interface UploadProps {
  onUploadComplete: (success?: boolean) => void;
}

/** Props for the SearchModal component */
export interface SearchModalProps {
  onClose: () => void;
  onSearch: (searchTerm: string) => void;
}

/** Props for the DashboardGridItem component */
export interface DashboardGridItemProps {
  doc: Document;
  onDocumentClick: (doc: Document) => void;
  onDelete: () => void;
  onDownload: (e: React.MouseEvent<HTMLButtonElement>) => void;
}

/** Props for the MiniPDFViewer component */
export interface MiniPDFViewerProps {
  documentLink: string;
  initialPage: number;
}

/** Props for the Modal component */
export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string; // Optional message prop
  children: ReactNode; // Allow modal to have children elements
}

/** Type for the document deletion hook */
export type DocumentDeletionHook = (callback: () => void) => (doc: Document) => void;

/** Utility type for making all properties of an interface optional */
export type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

/** Utility type for components that can have children */
export interface WithChildren {
  children?: ReactNode;
}
