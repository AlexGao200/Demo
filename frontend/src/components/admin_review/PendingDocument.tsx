import React, { useState, useEffect } from 'react';
import SingleSelectDropdown from './SingleSelectDropdown';
import MultiSelectDropdown from './MultiSelectDropdown';
import Modal from './Modal';
import axiosInstance from '../../axiosInstance';

interface DocumentProps {
  document: any;
  organizations: { id: string; name: string }[];
  subfields: { id: string; name: string }[];
  handleApprove: (docId: string, docData: any) => void;
  handleReject: (docId: string) => void;
}

const SubfieldModalContent: React.FC<{
  subfields: { id: string; name: string }[];
  selectedSubfields: string[];
  setSelectedSubfields: (subfields: string[]) => void;
  onClose: () => void;
}> = ({ subfields, selectedSubfields, setSelectedSubfields, onClose }) => (
  <>
    <h2>Select Subfields</h2>
    <MultiSelectDropdown
      options={subfields}
      selectedOptions={selectedSubfields}
      setSelectedOptions={setSelectedSubfields}
      label="Subfields"
    />
    <button onClick={onClose}>Done</button>
  </>
);

const AreaModalContent: React.FC<{
  areas: string[];
  selectedAreas: string[];
  setSelectedAreas: (areas: string[]) => void;
  onClose: () => void;
}> = ({ areas, selectedAreas, setSelectedAreas, onClose }) => (
  <>
    <h2>Select Areas</h2>
    <MultiSelectDropdown
      options={areas.map(area => ({ id: area, name: area }))}
      selectedOptions={selectedAreas}
      setSelectedOptions={setSelectedAreas}
      label="Areas"
    />
    <button onClick={onClose}>Done</button>
  </>
);

const PendingDocumentReview: React.FC<DocumentProps> = ({
  document,
  organizations,
  subfields,
  handleApprove,
  handleReject,
}) => {
  const [selectedOrganizationId, setSelectedOrganizationId] = useState<string>(
    document.organization_id || ''
  );
  const [selectedSubfields, setSelectedSubfields] = useState<string[]>(document.subfields || []);
  const [availableAreas, setAvailableAreas] = useState<string[]>([]);
  const [selectedAreas, setSelectedAreas] = useState<string[]>(document.areas || []);
  const [isSubfieldModalOpen, setIsSubfieldModalOpen] = useState(false);
  const [isAreaModalOpen, setIsAreaModalOpen] = useState(false);
  const [isLoadingAreas, setIsLoadingAreas] = useState(false);
  const [areaFetchError, setAreaFetchError] = useState<string | null>(null);
  const [documentTitle, setDocumentTitle] = useState<string>(document.title || '');

  // Fetch areas when subfields are selected
  useEffect(() => {
    const fetchAreasForSubfields = async () => {
      if (selectedSubfields.length > 0) {
        setIsLoadingAreas(true);
        setAreaFetchError(null);
        try {
          const response = await axiosInstance.post('/get_areas_by_subfield', {
            subfield_ids: selectedSubfields,
          });

          const areas: string[] = Object.values(response.data.subfield_areas).flat();
          setAvailableAreas(areas);
        } catch (err) {
          console.error('Error fetching areas for subfields:', err);
          setAreaFetchError('Failed to fetch areas. Please try again.');
        } finally {
          setIsLoadingAreas(false);
        }
      } else {
        setAvailableAreas([]);
      }
    };

    fetchAreasForSubfields();
  }, [selectedSubfields]);

  // Get the organization name based on the selected organization ID
  const selectedOrganization = organizations.find(org => org.id === selectedOrganizationId);
  const organizationName = selectedOrganization ? selectedOrganization.name : null;

  const openSubfieldModal = () => setIsSubfieldModalOpen(true);
  const closeSubfieldModal = () => setIsSubfieldModalOpen(false);
  const openAreaModal = () => setIsAreaModalOpen(true);
  const closeAreaModal = () => setIsAreaModalOpen(false);

  return (
    <li className="pending-document">
      <h3>Document ID: {document._id}</h3>

      {/* Title Input */}
      <div className="document-title">
        <strong>Title:</strong>
        <input
          type="text"
          value={documentTitle}
          onChange={(e) => setDocumentTitle(e.target.value)}
          placeholder="Enter document title"
        />
      </div>

      {/* Organization Selection */}
      <SingleSelectDropdown
        options={organizations}
        selectedOption={selectedOrganizationId}
        setSelectedOption={setSelectedOrganizationId}
        label="Select Organization"
      />

      {/* Subfield Selection */}
      <div className="selection-container">
        <button onClick={openSubfieldModal}>Select Subfields</button>
        <span>{selectedSubfields.length} subfields selected</span>
      </div>

      {/* Area Selection */}
      {isLoadingAreas && <p>Loading areas...</p>}
      {areaFetchError && <p className="error">{areaFetchError}</p>}
      {availableAreas.length > 0 && !isLoadingAreas && !areaFetchError && (
        <div className="selection-container">
          <button onClick={openAreaModal}>Select Areas</button>
          <span>{selectedAreas.length} areas selected</span>
        </div>
      )}

      {/* Document Link */}
      <div className="document-link">
        <a href={document.file_url} target="_blank" rel="noopener noreferrer">
          {document.file_name || document.file_url}
        </a>
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        <button
          className="approve"
          onClick={() => handleApprove(document._id, {
            title: documentTitle,
            organization: organizationName,  // Pass organization name here
            subfields: selectedSubfields.length > 0 ? selectedSubfields : null,
            areas: selectedAreas.length > 0 ? selectedAreas : null,
          })}
        >
          Approve
        </button>
        <button className="reject" onClick={() => handleReject(document._id)}>Reject</button>
      </div>

      {/* Subfield Modal */}
      <Modal isOpen={isSubfieldModalOpen} onClose={closeSubfieldModal}>
        <SubfieldModalContent
          subfields={subfields}
          selectedSubfields={selectedSubfields}
          setSelectedSubfields={setSelectedSubfields}
          onClose={closeSubfieldModal}
        />
      </Modal>

      {/* Area Modal */}
      <Modal isOpen={isAreaModalOpen} onClose={closeAreaModal}>
        <AreaModalContent
          areas={availableAreas}
          selectedAreas={selectedAreas}
          setSelectedAreas={setSelectedAreas}
          onClose={closeAreaModal}
        />
      </Modal>

      {/* CSS Styling */}
      <style jsx>{`
        .pending-document {
          border: 1px solid #ccc;
          padding: 1rem;
          margin-bottom: 1rem;
          border-radius: 4px;
        }
        .document-title {
          margin-bottom: 1rem;
        }
        .document-title input {
          margin-left: 0.5rem;
        }
        .selection-container {
          display: flex;
          align-items: center;
          margin-bottom: 1rem;
        }
        .selection-container button {
          margin-right: 1rem;
        }
        .document-link {
          margin-bottom: 1rem;
        }
        .action-buttons {
          display: flex;
          gap: 1rem;
        }
        .action-buttons button {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        .action-buttons .approve {
          background-color: #4CAF50;
          color: white;
        }
        .action-buttons .reject {
          background-color: #f44336;
          color: white;
        }
        .error {
          color: red;
        }
      `}</style>
    </li>
  );
};

export default PendingDocumentReview;
