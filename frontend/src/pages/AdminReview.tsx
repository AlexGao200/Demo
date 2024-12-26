import React, { useEffect, useState } from 'react';
import axiosInstance from '../axiosInstance';
import PendingDocumentReview from '../components/admin_review/PendingDocument';
import PublicSubfield from '../components/admin_review/CreatePublicSubfield';  // Keep this component
import CreateAreaForSubfield from '../components/admin_review/PublicSubfieldArea';  // Keep this component
import { Organization } from '../types';
import { Subfield } from '../types';

interface Document {
  _id: string;
  title: string;
  file_url: string;
  file_name?: string;
  organization_name?: string;
  subfields?: string[];
  areas?: string[];
}


const AdminReviewPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [subfields, setSubfields] = useState<Subfield[]>([]);
  const [message, setMessage] = useState<string>('');

  // Fetch pending documents and metadata (organizations and subfields) on mount
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const response = await axiosInstance.get('/get_pending_documents');
        setDocuments(response.data);  // Set the documents
      } catch (err) {
        console.error('Error fetching pending documents:', err);
      }
    };

    const fetchMetadata = async () => {
      try {
        const response = await axiosInstance.get('/get_public_metadata');
        setOrganizations(response.data.organizations);  // Set the organizations
        setSubfields(response.data.subfields);  // Set the subfields
      } catch (err) {
        console.error('Error fetching metadata:', err);
      }
    };

    fetchDocuments();  // Fetch documents on mount
    fetchMetadata();  // Fetch organizations and subfields on mount
  }, []);

  // Handle approve action
  const handleApprove = async (docId: string, docData: any) => {
    console.log("Submitting approval for document:", docId);
    console.log("Approval payload:", docData); // Log the payload

    try {
      const response = await axiosInstance.post('/approve_document', {
        document_id: docId,
        title: docData.title || '',
        organization_name: docData.organization || '',
        subfield: docData.subfields || [],
        area: docData.areas || [],
      });
      console.log("Backend response:", response.data); // Log the response

      setMessage(response.data.message || `Document has been approved and moved to the public index.`);
      setDocuments(documents.filter(doc => doc._id !== docId));
    } catch (err) {
      console.error('Error approving document:', err);
      setMessage('An error occurred while approving the document.');
    }
  };


  // Handle reject action
  const handleReject = async (documentId: string) => {
    try {
      const response = await axiosInstance.post('/reject_document', { document_id: documentId });
      setMessage(response.data.message || `Document has been rejected and deleted.`);
      setDocuments(documents.filter(doc => doc._id !== documentId));  // Remove the rejected document from the list
    } catch (err) {
      console.error('Error rejecting document:', err instanceof Error ? err.message : String(err));
      setMessage('An error occurred while rejecting the document.');
    }
  };

  return (
    <div>
      <h2>Admin Review Page</h2>
      {message && <p>{message}</p>}

      {/* PublicSubfield and CreateAreaForSubfield components */}
      <PublicSubfield />
      <CreateAreaForSubfield />

      {/* Render each pending document for review */}
      <ul>
        {documents.map((doc) => (
          <PendingDocumentReview
            key={doc._id}
            document={doc}
            organizations={organizations}
            subfields={subfields}
            handleApprove={handleApprove}  // Pass the approve handler
            handleReject={handleReject}  // Pass the reject handler
          />
        ))}
      </ul>
    </div>
  );
};

export default AdminReviewPage;
