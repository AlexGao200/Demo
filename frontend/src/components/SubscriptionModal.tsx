import React from 'react';
import { Link } from 'react-router-dom';
import Modal from './Modal';  // Assuming you have a generic Modal component for reuse

interface SubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SubscriptionModal: React.FC<SubscriptionModalProps> = ({ isOpen, onClose }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="subscription-modal-content">
        <h2>Subscription Required</h2>
        <p>Please subscribe or contact your organization for membership.</p>
        <div className="modal-buttons">
          <Link to="/subscription" className="modal-button">Subscribe</Link>
          <Link to="/trial" className="modal-button">Try for Free</Link>
          <Link to="/contact" className="modal-button">Contact Organization</Link>
        </div>
      </div>
    </Modal>
  );
};

export default SubscriptionModal;
